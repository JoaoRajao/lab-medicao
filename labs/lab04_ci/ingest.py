"""Coleta congelada e ingestão dos workflow runs usados no Lab04S01 (#96)."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from shared.github_rest import GitHubRestClient
from shared.warehouse import create_and_load_table, export_table

ROOT = Path(__file__).resolve().parents[2]
LAB_DIR = Path(__file__).resolve().parent
CSV_PATH = LAB_DIR / "data" / "raw" / "ci_runs.csv"
PARQUET_PATH = LAB_DIR / "data" / "parquet" / "ci_runs.parquet"
REPOSITORY = "astral-sh/ruff"
WORKFLOW_ID = 32130301  # .github/workflows/ci.yaml (CI)
BRANCH = "main"
CUTOFF = datetime(2026, 11, 2, 18, 14, 10, tzinfo=timezone.utc)
SAMPLE_SIZE = 30
VALID_CONCLUSIONS = {"success", "failure"}
CSV_COLUMNS = (
    "repository", "workflow_id", "run_id", "run_attempt", "head_sha",
    "event", "head_branch", "created_at", "conclusion", "html_url",
)
TABLE_COLUMNS = [
    ("repository", "varchar"), ("workflow_id", "bigint"), ("run_id", "bigint"),
    ("run_attempt", "integer"), ("head_sha", "varchar"), ("event", "varchar"),
    ("head_branch", "varchar"), ("created_at", "timestamptz"),
    ("conclusion", "varchar"), ("html_url", "varchar"),
]


def parse_utc(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError(f"Data sem fuso horário: {value}")
    return timestamp.astimezone(timezone.utc)


def eligible(run: dict[str, Any]) -> bool:
    try:
        return (
            run["workflow_id"] == WORKFLOW_ID
            and run["event"] == "push"
            and run["head_branch"] == BRANCH
            and run["status"] == "completed"
            and run["conclusion"] in VALID_CONCLUSIONS
            and parse_utc(run["created_at"]) <= CUTOFF
        )
    except (KeyError, TypeError, ValueError):
        return False


def select_runs(runs: list[dict[str, Any]], size: int = SAMPLE_SIZE) -> list[dict[str, str]]:
    """Seleciona os últimos commits elegíveis antes do corte, sem escolher pelo resultado."""
    ordered = sorted(
        (run for run in runs if eligible(run)),
        key=lambda run: (parse_utc(run["created_at"]), int(run["id"])),
        reverse=True,
    )
    selected: list[dict[str, str]] = []
    seen_sha: set[str] = set()
    for run in ordered:
        sha = run.get("head_sha")
        if not isinstance(sha, str) or not sha or sha in seen_sha:
            continue
        seen_sha.add(sha)
        selected.append({
            "repository": REPOSITORY,
            "workflow_id": str(WORKFLOW_ID),
            "run_id": str(run["id"]),
            "run_attempt": str(run["run_attempt"]),
            "head_sha": sha,
            "event": run["event"],
            "head_branch": run["head_branch"],
            "created_at": parse_utc(run["created_at"]).isoformat().replace("+00:00", "Z"),
            "conclusion": run["conclusion"],
            "html_url": run["html_url"],
        })
        if len(selected) == size:
            break
    if len(selected) != size:
        raise ValueError(f"Apenas {len(selected)} de {size} commits elegíveis antes do corte")
    return selected


def fetch_runs(token: str) -> list[dict[str, str]]:
    client = GitHubRestClient(token=token)
    path = f"repos/{REPOSITORY}/actions/workflows/{WORKFLOW_ID}/runs"
    collected: list[dict[str, Any]] = []
    # A API limita a 1.000 resultados para buscas filtradas. A amostra fixa
    # precisa estar nesse alcance; caso contrário, falhamos explicitamente.
    for page in range(1, 11):
        response = client.get(
            path,
            {"event": "push", "branch": BRANCH, "per_page": 100, "page": page},
            use_cache=False,
        )
        page_runs = response.data["workflow_runs"]
        collected.extend(page_runs)
        if not page_runs:
            break
        try:
            return select_runs(collected)
        except ValueError as error:
            if not str(error).startswith("Apenas "):
                raise
    return select_runs(collected)


def write_csv(rows: list[dict[str, str]], path: Path = CSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_csv(path: Path = CSV_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError("Cabeçalho do CSV Lab04 inválido")
        rows = list(reader)
    if len(rows) != SAMPLE_SIZE:
        raise ValueError(f"A amostra deve ter {SAMPLE_SIZE} execuções; recebeu {len(rows)}")
    if len({row["run_id"] for row in rows}) != SAMPLE_SIZE:
        raise ValueError("IDs de execução repetidos")
    if len({row["head_sha"] for row in rows}) != SAMPLE_SIZE:
        raise ValueError("Commits repetidos")
    for row in rows:
        if (
            row["repository"] != REPOSITORY
            or int(row["workflow_id"]) != WORKFLOW_ID
            or row["event"] != "push"
            or row["head_branch"] != BRANCH
            or row["conclusion"] not in VALID_CONCLUSIONS
            or parse_utc(row["created_at"]) > CUTOFF
        ):
            raise ValueError(f"Execução fora do protocolo: {row['run_id']}")
        if int(row["run_id"]) <= 0 or int(row["run_attempt"]) <= 0:
            raise ValueError(f"ID ou tentativa inválida: {row['run_id']}")
        if not row["head_sha"] or not row["html_url"].startswith(f"https://github.com/{REPOSITORY}/actions/runs/"):
            raise ValueError(f"Proveniência inválida: {row['run_id']}")
        row["workflow_id"] = int(row["workflow_id"])
        row["run_id"] = int(row["run_id"])
        row["run_attempt"] = int(row["run_attempt"])
        row["created_at"] = parse_utc(row["created_at"])
    return rows


def build_dbt() -> None:
    profile = {
        "lab_medicao": {
            "target": "dev",
            "outputs": {"dev": {"type": "duckdb", "path": str(ROOT / "data" / "warehouse.duckdb")}},
        },
    }
    with tempfile.TemporaryDirectory(prefix="lab04-dbt-") as directory:
        Path(directory, "profiles.yml").write_text(yaml.safe_dump(profile), encoding="utf-8")
        subprocess.run(
            ["dbt", "build", "--project-dir", str(ROOT), "--profiles-dir", directory,
             "--select", "+gold_lab04_ci_failure_rate"],
            cwd=ROOT,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstrói CSV → DuckDB → Parquet → dbt do Lab04S01")
    parser.add_argument("--refresh", action="store_true", help="Recoleta a amostra fixa pela API do GitHub")
    args = parser.parse_args()
    if args.refresh:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            parser.error("--refresh requer GITHUB_TOKEN")
        write_csv(fetch_runs(token))

    rows = read_csv()
    create_and_load_table("lab04_ci_runs", TABLE_COLUMNS, rows)
    temporary = PARQUET_PATH.with_name(f".{PARQUET_PATH.name}.tmp")
    try:
        export_table("lab04_ci_runs", parquet_path=temporary)
        temporary.replace(PARQUET_PATH)
    finally:
        temporary.unlink(missing_ok=True)
    build_dbt()
    failures = sum(row["conclusion"] == "failure" for row in rows)
    print(f"Lab04S01: {len(rows)} execuções, {failures} falhas; Parquet e dbt atualizados")


if __name__ == "__main__":
    main()
