from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import requests
from dotenv import load_dotenv


BASE_URL = "https://api.github.com"
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
PARQUET_DIR = DATA_DIR / "parquet"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
DUCKDB_PATH = DATA_DIR / "github.duckdb"
POPULAR_LANGUAGES_PATH = ROOT_DIR / "config" / "popular_languages.json"
DEFAULT_CHECKPOINT_PATH = CHECKPOINT_DIR / "repositories.jsonl"
GITHUB_SEARCH_RESULT_LIMIT = 1000


@dataclass(frozen=True)
class PopularLanguageReference:
    source_name: str
    source_url: str
    languages: set[str]


class GitHubClient:
    def __init__(self, token: str | None, timeout: int = 30, search_sleep: float = 2.2) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "dataplataform-ti6-github-ingest",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout
        self.search_sleep = search_sleep

    def get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        while True:
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                wait_seconds = max(reset_at - int(time.time()) + 2, 1)
                print(f"GitHub rate limit atingido. Aguardando {wait_seconds}s para continuar.")
                time.sleep(wait_seconds)
                continue

            if response.status_code in {403, 429} and "rate limit" in response.text.lower():
                print("GitHub pediu reducao de ritmo. Aguardando 60s para continuar.")
                time.sleep(60)
                continue

            response.raise_for_status()
            return response

    def search_repositories(self, query: str, limit: int) -> list[dict[str, Any]]:
        repos: list[dict[str, Any]] = []
        per_page = min(100, limit)

        for page in range(1, (limit + per_page - 1) // per_page + 1):
            response = self.get(
                "/search/repositories",
                {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )
            items = response.json().get("items", [])
            repos.extend(items)
            if len(items) < per_page or len(repos) >= limit:
                break

        return repos[:limit]

    def search_count(self, query: str) -> int:
        response = self.get("/search/issues", {"q": query, "per_page": 1})
        if self.search_sleep > 0:
            time.sleep(self.search_sleep)
        return int(response.json().get("total_count", 0))

    def paginated_endpoint_count(self, path: str) -> int:
        response = self.get(path, {"per_page": 1})
        link = response.headers.get("Link", "")
        last_page = self._extract_last_page(link)
        if last_page is not None:
            return last_page
        return len(response.json())

    @staticmethod
    def _extract_last_page(link_header: str) -> int | None:
        for part in link_header.split(","):
            if 'rel="last"' not in part:
                continue
            marker = "page="
            start = part.find(marker)
            if start == -1:
                continue
            start += len(marker)
            end = start
            while end < len(part) and part[end].isdigit():
                end += 1
            return int(part[start:end])
        return None


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
    client: GitHubClient,
    repo: dict[str, Any],
    language_reference: PopularLanguageReference,
    collected_at: datetime,
) -> dict[str, Any]:
    full_name = repo["full_name"]
    owner, name = full_name.split("/", 1)
    primary_language = repo.get("language")

    accepted_pull_requests = client.search_count(f"repo:{full_name} type:pr is:merged")
    open_issues_count = client.search_count(f"repo:{full_name} type:issue state:open")
    closed_issues_count = client.search_count(f"repo:{full_name} type:issue state:closed")
    total_issues_count = open_issues_count + closed_issues_count
    releases_count = client.paginated_endpoint_count(f"/repos/{owner}/{name}/releases")

    created_at = parse_datetime(repo.get("created_at"))
    pushed_at = parse_datetime(repo.get("pushed_at"))
    updated_at = parse_datetime(repo.get("updated_at"))
    closed_issues_ratio = (
        closed_issues_count / total_issues_count if total_issues_count > 0 else None
    )

    return {
        "repo_id": repo["id"],
        "full_name": full_name,
        "owner": owner,
        "name": name,
        "html_url": repo.get("html_url"),
        "description": repo.get("description"),
        "primary_language": primary_language,
        "is_popular_language": primary_language in language_reference.languages
        if primary_language
        else False,
        "popular_language_source": language_reference.source_name,
        "popular_language_source_url": language_reference.source_url,
        "stars_count": repo.get("stargazers_count"),
        "forks_count": repo.get("forks_count"),
        "watchers_count": repo.get("watchers_count"),
        "open_issues_count": open_issues_count,
        "closed_issues_count": closed_issues_count,
        "total_issues_count": total_issues_count,
        "closed_issues_ratio": closed_issues_ratio,
        "accepted_pull_requests": accepted_pull_requests,
        "releases_count": releases_count,
        "created_at": created_at,
        "updated_at": updated_at,
        "pushed_at": pushed_at,
        "age_days": days_between(created_at, collected_at),
        "days_since_last_update": days_between(pushed_at or updated_at, collected_at),
        "archived": repo.get("archived"),
        "disabled": repo.get("disabled"),
        "is_fork": repo.get("fork"),
        "default_branch": repo.get("default_branch"),
        "license_key": (repo.get("license") or {}).get("key"),
        "license_name": (repo.get("license") or {}).get("name"),
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
        description="Coleta repositorios populares do GitHub e grava DuckDB + Parquet."
    )
    parser.add_argument(
        "--query",
        default="stars:>1000 archived:false fork:false",
        help="Query da GitHub Search API para selecionar repositorios.",
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
        help="Pausa em segundos entre repositorios para reduzir pressao na API.",
    )
    parser.add_argument(
        "--search-sleep",
        type=float,
        default=2.2,
        help="Pausa em segundos entre chamadas da GitHub Search API.",
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
            "A GitHub Search API retorna no maximo os primeiros "
            f"{GITHUB_SEARCH_RESULT_LIMIT} resultados por busca. Use --limit 1000."
        )
    if args.limit > 10 and not token:
        raise RuntimeError(
            "Para coletar mais de 10 repositorios, configure GITHUB_TOKEN em "
            f"{ROOT_DIR / '.env'}. A coleta de 1.000 repositorios faz milhares de "
            "chamadas na API."
        )


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    args = parse_args()
    token = os.getenv("GITHUB_TOKEN")
    validate_args(args, token)
    client = GitHubClient(token=token, search_sleep=args.search_sleep)
    language_reference = load_popular_languages()
    collected_at = datetime.now(timezone.utc)

    repositories = client.search_repositories(args.query, args.limit)
    checkpoint_path = args.checkpoint if args.checkpoint.is_absolute() else ROOT_DIR / args.checkpoint
    if args.no_resume and checkpoint_path.exists():
        checkpoint_path.unlink()

    repository_ids = {repo["id"] for repo in repositories}
    records = [] if args.no_resume else load_checkpoint(checkpoint_path)
    records = [record for record in records if record["repo_id"] in repository_ids]
    collected_repo_ids = {record["repo_id"] for record in records}

    for index, repo in enumerate(repositories, start=1):
        if repo["id"] in collected_repo_ids:
            print(f"[{index}/{len(repositories)}] pulando {repo['full_name']} (checkpoint)")
            continue
        print(f"[{index}/{len(repositories)}] coletando {repo['full_name']}")
        record = build_repository_record(client, repo, language_reference, collected_at)
        records.append(record)
        append_checkpoint(checkpoint_path, record)
        if args.sleep > 0:
            time.sleep(args.sleep)

    write_duckdb_and_parquet(records)
    print(f"OK: {len(records)} repositorios gravados em {DUCKDB_PATH}")
    print(f"OK: parquet gravado em {PARQUET_DIR / 'repositories.parquet'}")


if __name__ == "__main__":
    main()
