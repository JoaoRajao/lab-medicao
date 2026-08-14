from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import duckdb

try:
    import certifi
except ImportError:  # pragma: no cover - optional TLS certificate helper
    certifi = None


GRAPHQL_URL = "https://api.github.com/graphql"
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
PARQUET_DIR = DATA_DIR / "parquet"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
DUCKDB_PATH = DATA_DIR / "github.duckdb"
POPULAR_LANGUAGES_PATH = ROOT_DIR / "config" / "popular_languages.json"
DEFAULT_CHECKPOINT_PATH = CHECKPOINT_DIR / "repositories.jsonl"
GITHUB_SEARCH_RESULT_LIMIT = 1000


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


class GitHubGraphQLClient:
    def __init__(self, token: str, timeout: int = 30) -> None:
        self.token = token
        self.timeout = timeout
        self.ssl_context = (
            ssl.create_default_context(cafile=certifi.where())
            if certifi is not None
            else ssl.create_default_context()
        )

    def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = Request(
            GRAPHQL_URL,
            data=payload,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "lab-medicao-github-graphql-ingest",
            },
            method="POST",
        )

        while True:
            try:
                with urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                    raw = response.read().decode("utf-8")
            except HTTPError as error:
                raw = error.read().decode("utf-8", errors="replace")
                if 500 <= error.code < 600:
                    print(f"GitHub retornou HTTP {error.code}. Tentando novamente em 30s.")
                    time.sleep(30)
                    continue
                if error.code in {403, 429}:
                    wait_seconds = self._rate_limit_wait_seconds(error.headers, raw)
                    print(f"GitHub rate limit atingido. Aguardando {wait_seconds}s.")
                    time.sleep(wait_seconds)
                    continue
                raise RuntimeError(f"Erro HTTP {error.code} na API GraphQL: {raw}") from error
            except (TimeoutError, URLError) as error:
                print(f"Erro de rede na API GraphQL: {error}. Tentando novamente em 30s.")
                time.sleep(30)
                continue

            data = json.loads(raw)
            errors = data.get("errors", [])
            if errors and self._has_rate_limit_error(errors):
                reset_at = data.get("data", {}).get("rateLimit", {}).get("resetAt")
                wait_seconds = self._wait_seconds_from_reset_at(reset_at) if reset_at else 60
                print(f"GitHub rate limit atingido. Aguardando {wait_seconds}s.")
                time.sleep(wait_seconds)
                continue
            if errors:
                raise RuntimeError(f"Erro na query GraphQL: {errors}")
            return data["data"]

    def search_repositories(self, query: str, limit: int, page_size: int) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        after = None

        while len(repositories) < limit:
            first = min(page_size, limit - len(repositories))
            data = self.execute(
                REPOSITORY_SEARCH_QUERY,
                {"query": query, "first": first, "after": after},
            )
            search = data["search"]
            nodes = [node for node in search["nodes"] if node is not None]
            repositories.extend(nodes)

            page_info = search["pageInfo"]
            if not page_info["hasNextPage"] or not nodes:
                break
            after = page_info["endCursor"]

        return repositories[:limit]

    def repository_details(self, full_name: str) -> dict[str, Any]:
        owner, name = full_name.split("/", 1)
        data = self.execute(REPOSITORY_DETAIL_QUERY, {"owner": owner, "name": name})
        repository = data.get("repository")
        if repository is None:
            raise RuntimeError(f"Repositorio nao encontrado via GraphQL: {full_name}")
        return repository

    @staticmethod
    def _has_rate_limit_error(errors: list[dict[str, Any]]) -> bool:
        return any("rate limit" in error.get("message", "").lower() for error in errors)

    @staticmethod
    def _rate_limit_wait_seconds(headers: Any, body: str) -> int:
        reset_header = headers.get("X-RateLimit-Reset")
        if reset_header:
            return max(int(reset_header) - int(time.time()) + 2, 1)

        try:
            data = json.loads(body)
            reset_at = data.get("data", {}).get("rateLimit", {}).get("resetAt")
        except json.JSONDecodeError:
            reset_at = None
        return GitHubGraphQLClient._wait_seconds_from_reset_at(reset_at) if reset_at else 60

    @staticmethod
    def _wait_seconds_from_reset_at(reset_at: str | None) -> int:
        if not reset_at:
            return 60
        reset_datetime = parse_datetime(reset_at)
        if reset_datetime is None:
            return 60
        return max(int((reset_datetime - datetime.now(timezone.utc)).total_seconds()) + 2, 1)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_between(start: datetime | None, end: datetime) -> int | None:
    if start is None:
        return None
    return max((end - start).days, 0)


def load_popular_languages() -> PopularLanguageReference:
    with POPULAR_LANGUAGES_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return PopularLanguageReference(
        source_name=raw["source_name"],
        source_url=raw["source_url"],
        languages=set(raw["languages"]),
    )


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Tipo nao serializavel em JSON: {type(value)!r}")


def parse_checkpoint_record(record: dict[str, Any]) -> dict[str, Any]:
    for column in ["created_at", "updated_at", "pushed_at", "collected_at"]:
        record[column] = parse_datetime(record.get(column))
    return record


def load_checkpoint(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            records.append(parse_checkpoint_record(json.loads(line)))
    return records


def append_checkpoint(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=json_default, ensure_ascii=True))
        file.write("\n")


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


def write_duckdb_and_parquet(records: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "repo_id",
        "full_name",
        "owner",
        "name",
        "html_url",
        "description",
        "primary_language",
        "is_popular_language",
        "popular_language_source",
        "popular_language_source_url",
        "stars_count",
        "forks_count",
        "watchers_count",
        "open_issues_count",
        "closed_issues_count",
        "total_issues_count",
        "closed_issues_ratio",
        "accepted_pull_requests",
        "releases_count",
        "created_at",
        "updated_at",
        "pushed_at",
        "age_days",
        "days_since_last_update",
        "archived",
        "disabled",
        "is_fork",
        "default_branch",
        "license_key",
        "license_name",
        "collected_at",
    ]

    with duckdb.connect(str(DUCKDB_PATH)) as conn:
        conn.execute("drop table if exists github_repositories")
        conn.execute(
            """
            create table github_repositories (
                repo_id bigint,
                full_name varchar,
                owner varchar,
                name varchar,
                html_url varchar,
                description varchar,
                primary_language varchar,
                is_popular_language boolean,
                popular_language_source varchar,
                popular_language_source_url varchar,
                stars_count integer,
                forks_count integer,
                watchers_count integer,
                open_issues_count integer,
                closed_issues_count integer,
                total_issues_count integer,
                closed_issues_ratio double,
                accepted_pull_requests integer,
                releases_count integer,
                created_at timestamptz,
                updated_at timestamptz,
                pushed_at timestamptz,
                age_days integer,
                days_since_last_update integer,
                archived boolean,
                disabled boolean,
                is_fork boolean,
                default_branch varchar,
                license_key varchar,
                license_name varchar,
                collected_at timestamptz
            )
            """
        )
        placeholders = ", ".join(["?"] * len(columns))
        conn.executemany(
            f"insert into github_repositories values ({placeholders})",
            [[record.get(column) for column in columns] for record in records],
        )
        parquet_path = str(PARQUET_DIR / "repositories.parquet").replace("'", "''")
        conn.execute(
            f"""
            copy github_repositories
            to '{parquet_path}'
            (format parquet, compression zstd)
            """
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Coleta repositorios populares via GraphQL do GitHub e grava DuckDB + Parquet."
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
        raise RuntimeError(f"Configure GITHUB_TOKEN em {ROOT_DIR / '.env'}.")


def main() -> None:
    load_env_file(ROOT_DIR / ".env")
    args = parse_args()
    token = os.getenv("GITHUB_TOKEN")
    validate_args(args, token)

    client = GitHubGraphQLClient(token=token or "")
    language_reference = load_popular_languages()
    collected_at = datetime.now(timezone.utc)

    repositories = client.search_repositories(args.query, args.limit, args.page_size)
    checkpoint_path = args.checkpoint if args.checkpoint.is_absolute() else ROOT_DIR / args.checkpoint
    if args.no_resume and checkpoint_path.exists():
        checkpoint_path.unlink()

    repository_names = {repo["nameWithOwner"] for repo in repositories}
    records = [] if args.no_resume else load_checkpoint(checkpoint_path)
    records = [record for record in records if record["full_name"] in repository_names]
    collected_repository_names = {record["full_name"] for record in records}

    for index, repo in enumerate(repositories, start=1):
        full_name = repo["nameWithOwner"]
        if full_name in collected_repository_names:
            print(f"[{index}/{len(repositories)}] pulando {repo['nameWithOwner']} (checkpoint)", flush=True)
            continue
        print(f"[{index}/{len(repositories)}] coletando detalhes {full_name}", flush=True)
        detailed_repo = client.repository_details(full_name)
        record = build_repository_record(detailed_repo, language_reference, collected_at)
        records.append(record)
        append_checkpoint(checkpoint_path, record)
        if args.sleep > 0:
            time.sleep(args.sleep)

    write_duckdb_and_parquet(records)
    print(f"OK: {len(records)} repositorios gravados em {DUCKDB_PATH}")
    print(f"OK: parquet gravado em {PARQUET_DIR / 'repositories.parquet'}")


if __name__ == "__main__":
    main()
