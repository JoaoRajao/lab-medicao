from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.checkpoint import append_checkpoint, load_checkpoint
from shared.dates import days_between, parse_datetime
from shared.github_client import GitHubGraphQLClient, load_env_file
from shared.pagination import paginate
from shared.warehouse import create_and_load_table, export_table, read_table

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"
PARQUET_PATH = DATA_DIR / "parquet" / "repositories.parquet"
CSV_PATH = DATA_DIR / "csv" / "repositories.csv"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
DEFAULT_CHECKPOINT_PATH = CHECKPOINT_DIR / "repositories.jsonl"
POPULAR_LANGUAGES_PATH = ROOT_DIR / "config" / "popular_languages.json"
ENV_PATH = REPO_ROOT / ".env"
GITHUB_SEARCH_RESULT_LIMIT = 1000

TABLE_NAME = "lab01_repos_populares"
DATETIME_COLUMNS = ["created_at", "updated_at", "pushed_at", "collected_at"]

TABLE_COLUMNS: list[tuple[str, str]] = [
    ("repo_id", "bigint"),
    ("full_name", "varchar"),
    ("owner", "varchar"),
    ("name", "varchar"),
    ("html_url", "varchar"),
    ("description", "varchar"),
    ("primary_language", "varchar"),
    ("is_popular_language", "boolean"),
    ("popular_language_source", "varchar"),
    ("popular_language_source_url", "varchar"),
    ("stars_count", "integer"),
    ("forks_count", "integer"),
    ("watchers_count", "integer"),
    ("open_issues_count", "integer"),
    ("closed_issues_count", "integer"),
    ("total_issues_count", "integer"),
    ("closed_issues_ratio", "double"),
    ("accepted_pull_requests", "integer"),
    ("releases_count", "integer"),
    ("created_at", "timestamptz"),
    ("updated_at", "timestamptz"),
    ("pushed_at", "timestamptz"),
    ("age_days", "integer"),
    ("days_since_last_update", "integer"),
    ("archived", "boolean"),
    ("disabled", "boolean"),
    ("is_fork", "boolean"),
    ("default_branch", "varchar"),
    ("license_key", "varchar"),
    ("license_name", "varchar"),
    ("collected_at", "timestamptz"),
]
RECORD_COLUMNS = [name for name, _ in TABLE_COLUMNS]


REPOSITORY_SEARCH_QUERY = """
query SearchPopularRepositories($query: String!, $first: Int!, $after: String) {
  search(query: $query, type: REPOSITORY, first: $first, after: $after) {
    repositoryCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on Repository {
        id
        databaseId
        nameWithOwner
      }
    }
  }
  rateLimit {
    remaining
    resetAt
  }
}
"""


REPOSITORY_DETAIL_QUERY = """
query RepositoryDetails($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    databaseId
    nameWithOwner
    name
    url
    description
    stargazerCount
    forkCount
    createdAt
    updatedAt
    pushedAt
    isArchived
    isDisabled
    isFork
    primaryLanguage {
      name
    }
    owner {
      login
    }
    watchers {
      totalCount
    }
    issues(states: OPEN) {
      totalCount
    }
    closedIssues: issues(states: CLOSED) {
      totalCount
    }
    pullRequests(states: MERGED) {
      totalCount
    }
    releases {
      totalCount
    }
    defaultBranchRef {
      name
    }
    licenseInfo {
      key
      name
    }
  }
  rateLimit {
    remaining
    resetAt
  }
}
"""


@dataclass(frozen=True)
class PopularLanguageReference:
    source_name: str
    source_url: str
    languages: set[str]


def load_popular_languages() -> PopularLanguageReference:
    with POPULAR_LANGUAGES_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return PopularLanguageReference(
        source_name=raw["source_name"],
        source_url=raw["source_url"],
        languages=set(raw["languages"]),
    )


def repository_details(client: GitHubGraphQLClient, full_name: str) -> dict[str, Any]:
    owner, name = full_name.split("/", 1)
    data = client.execute(REPOSITORY_DETAIL_QUERY, {"owner": owner, "name": name})
    repository = data.get("repository")
    if repository is None:
        raise RuntimeError(f"Repositorio nao encontrado via GraphQL: {full_name}")
    return repository


def build_repository_record(
    repo: dict[str, Any],
    language_reference: PopularLanguageReference,
    collected_at: datetime,
) -> dict[str, Any]:
    full_name = repo["nameWithOwner"]
    owner = repo["owner"]["login"]
    primary_language = repo["primaryLanguage"]["name"] if repo.get("primaryLanguage") else None
    open_issues_count = int(repo["issues"]["totalCount"])
    closed_issues_count = int(repo["closedIssues"]["totalCount"])
    total_issues_count = open_issues_count + closed_issues_count
    closed_issues_ratio = (
        closed_issues_count / total_issues_count if total_issues_count > 0 else None
    )

    created_at = parse_datetime(repo.get("createdAt"))
    pushed_at = parse_datetime(repo.get("pushedAt"))
    updated_at = parse_datetime(repo.get("updatedAt"))
    license_info = repo.get("licenseInfo") or {}

    return {
        "repo_id": repo["databaseId"],
        "full_name": full_name,
        "owner": owner,
        "name": repo["name"],
        "html_url": repo.get("url"),
        "description": repo.get("description"),
        "primary_language": primary_language,
        "is_popular_language": primary_language in language_reference.languages
        if primary_language
        else False,
        "popular_language_source": language_reference.source_name,
        "popular_language_source_url": language_reference.source_url,
        "stars_count": repo.get("stargazerCount"),
        "forks_count": repo.get("forkCount"),
        "watchers_count": repo["watchers"]["totalCount"],
        "open_issues_count": open_issues_count,
        "closed_issues_count": closed_issues_count,
        "total_issues_count": total_issues_count,
        "closed_issues_ratio": closed_issues_ratio,
        "accepted_pull_requests": repo["pullRequests"]["totalCount"],
        "releases_count": repo["releases"]["totalCount"],
        "created_at": created_at,
        "updated_at": updated_at,
        "pushed_at": pushed_at,
        "age_days": days_between(created_at, collected_at),
        "days_since_last_update": days_between(pushed_at or updated_at, collected_at),
        "archived": repo.get("isArchived"),
        "disabled": repo.get("isDisabled"),
        "is_fork": repo.get("isFork"),
        "default_branch": (repo.get("defaultBranchRef") or {}).get("name"),
        "license_key": license_info.get("key"),
        "license_name": license_info.get("name"),
        "collected_at": collected_at,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Coleta repositorios populares via GraphQL do GitHub e grava warehouse + Parquet + CSV."
    )
    parser.add_argument(
        "--query",
        default="stars:>1000 archived:false fork:false sort:stars-desc",
        help="Query da busca do GitHub usada dentro da query GraphQL.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Numero maximo de repositorios para coletar.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Pausa em segundos entre repositorios ao gravar checkpoint.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=25,
        help="Numero de repositorios por pagina da query GraphQL.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_CHECKPOINT_PATH,
        help="Arquivo JSONL usado para salvar progresso e permitir retomar a coleta.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignora checkpoint anterior e refaz a coleta do zero.",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Pula a coleta na API e apenas reexporta Parquet/CSV a partir do warehouse existente.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace, token: str | None) -> None:
    if args.limit < 1:
        raise ValueError("--limit precisa ser maior que zero.")
    if args.limit > GITHUB_SEARCH_RESULT_LIMIT:
        raise ValueError(
            "A busca do GitHub retorna no maximo os primeiros "
            f"{GITHUB_SEARCH_RESULT_LIMIT} resultados. Use --limit 1000."
        )
    if not 1 <= args.page_size <= 100:
        raise ValueError("--page-size precisa estar entre 1 e 100.")
    if not token:
        raise RuntimeError(f"Configure GITHUB_TOKEN em {ENV_PATH}.")


def main() -> None:
    load_env_file(ENV_PATH)
    args = parse_args()

    if args.export_only:
        records = read_table(TABLE_NAME, RECORD_COLUMNS)
    else:
        token = os.getenv("GITHUB_TOKEN")
        validate_args(args, token)

        client = GitHubGraphQLClient(token=token or "")
        language_reference = load_popular_languages()
        collected_at = datetime.now(timezone.utc)

        repositories = paginate(
            client,
            REPOSITORY_SEARCH_QUERY,
            {"query": args.query},
            path="search",
            page_size=args.page_size,
            limit=args.limit,
        )
        checkpoint_path = args.checkpoint if args.checkpoint.is_absolute() else ROOT_DIR / args.checkpoint
        if args.no_resume and checkpoint_path.exists():
            checkpoint_path.unlink()

        repository_names = {repo["nameWithOwner"] for repo in repositories}
        records = [] if args.no_resume else load_checkpoint(checkpoint_path, DATETIME_COLUMNS)
        records = [record for record in records if record["full_name"] in repository_names]
        collected_repository_names = {record["full_name"] for record in records}

        for index, repo in enumerate(repositories, start=1):
            full_name = repo["nameWithOwner"]
            if full_name in collected_repository_names:
                print(f"[{index}/{len(repositories)}] pulando {repo['nameWithOwner']} (checkpoint)", flush=True)
                continue
            print(f"[{index}/{len(repositories)}] coletando detalhes {full_name}", flush=True)
            detailed_repo = repository_details(client, full_name)
            record = build_repository_record(detailed_repo, language_reference, collected_at)
            records.append(record)
            append_checkpoint(checkpoint_path, record)
            if args.sleep > 0:
                time.sleep(args.sleep)

        create_and_load_table(TABLE_NAME, TABLE_COLUMNS, records)
        print(f"OK: {len(records)} repositorios gravados na tabela {TABLE_NAME}")

    export_table(TABLE_NAME, parquet_path=PARQUET_PATH, csv_path=CSV_PATH)
    print(f"OK: parquet gravado em {PARQUET_PATH}")
    print(f"OK: csv gravado em {CSV_PATH}")


if __name__ == "__main__":
    main()
