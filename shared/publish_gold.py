"""Publica tabelas gold em Parquet para consumo pelo dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from shared.warehouse import DEFAULT_WAREHOUSE_PATH, REPO_ROOT

GOLD_TABLES = {
    "lab01": [f"gold_lab01_rq{number:02d}_{suffix}" for number, suffix in (
        (1, "age"), (2, "pull_requests"), (3, "releases"), (4, "updates"),
        (5, "popular_languages"), (6, "closed_issues"),
        (7, "popular_language_comparison"),
    )],
    "lab02": [
        "gold_lab02_rq01_time",
        "gold_lab02_rq02_defects",
        "gold_lab02_rq03_static_metrics",
    ],
}
DEFAULT_OUTPUT = REPO_ROOT / "data" / "published"


def publish(lab: str, warehouse: Path = DEFAULT_WAREHOUSE_PATH, output: Path = DEFAULT_OUTPUT) -> list[Path]:
    """Exporta apenas um lab completo; cada arquivo substitui seu antecessor ao terminar."""
    if lab not in GOLD_TABLES:
        raise ValueError(f"Lab desconhecido: {lab}")
    if not warehouse.is_file():
        raise FileNotFoundError(f"Warehouse nao encontrado: {warehouse}")

    destination = output / lab
    destination.mkdir(parents=True, exist_ok=True)
    published: list[Path] = []
    with duckdb.connect(str(warehouse), read_only=True) as conn:
        existing = {row[0] for row in conn.execute(
            "select table_name from information_schema.tables where table_schema = 'main'"
        ).fetchall()}
        missing = set(GOLD_TABLES[lab]) - existing
        if missing:
            raise RuntimeError(f"Tabelas gold ausentes para {lab}: {', '.join(sorted(missing))}. Rode dbt run antes.")
        for table in GOLD_TABLES[lab]:
            target = destination / f"{table}.parquet"
            temporary = destination / f".{table}.parquet.tmp"
            try:
                conn.execute(f"copy (select * from {table}) to ? (format parquet, compression zstd)", [str(temporary)])
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            published.append(target)
    return published


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica os modelos gold em Parquet para o Streamlit")
    parser.add_argument("--lab", choices=sorted(GOLD_TABLES), required=True)
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    paths = publish(args.lab, args.warehouse, args.output)
    print(f"OK: {len(paths)} tabelas de {args.lab} publicadas em {args.output / args.lab}")


if __name__ == "__main__":
    main()
