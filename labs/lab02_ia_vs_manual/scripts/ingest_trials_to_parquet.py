from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    import duckdb
except ImportError:  # pragma: no cover - fallback for local CLI-only environments
    duckdb = None


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT_DIR / "labs" / "lab02_ia_vs_manual" / "data" / "raw" / "trials_sample.jsonl"
DEFAULT_OUTPUT = ROOT_DIR / "labs" / "lab02_ia_vs_manual" / "data" / "parquet" / "trials.parquet"


BOOLEAN_FIELDS = {"censored"}
INTEGER_FIELDS = {
    "timebox_seconds",
    "time_to_green_seconds",
    "tests_passed",
    "tests_failed",
    "loc",
    "lloc",
    "sloc",
    "cyclomatic_complexity_max",
}
FLOAT_FIELDS = {
    "acceptance_success_rate",
    "cyclomatic_complexity_avg",
    "maintainability_index",
    "duplication_pct",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Converte resultados de trials Lab02 para Parquet.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def coerce_record(record: dict[str, Any]) -> dict[str, Any]:
    coerced = dict(record)
    for field in BOOLEAN_FIELDS:
        if field in coerced and isinstance(coerced[field], str):
            coerced[field] = coerced[field].strip().lower() in {"true", "1", "yes", "sim"}
    for field in INTEGER_FIELDS:
        if coerced.get(field) not in {None, ""}:
            coerced[field] = int(float(coerced[field]))
    for field in FLOAT_FIELDS:
        if coerced.get(field) not in {None, ""}:
            coerced[field] = float(coerced[field])
    return coerced


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as file:
            return [coerce_record(json.loads(line)) for line in file if line.strip()]
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as file:
            return [coerce_record(row) for row in csv.DictReader(file)]
    raise ValueError("Entrada precisa ser .jsonl ou .csv")


def main() -> None:
    args = parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT_DIR / args.input
    output_path = args.output if args.output.is_absolute() else ROOT_DIR / args.output
    records = load_records(input_path)
    if not records:
        raise ValueError(f"Nenhum registro encontrado em {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if duckdb is None:
        duckdb_cli = shutil.which("duckdb")
        if duckdb_cli is None:
            raise RuntimeError(
                "Instale duckdb com `pip install -r requirements.txt` "
                "ou deixe o comando `duckdb` disponivel no PATH."
            )
        input_sql = str(input_path).replace("'", "''")
        output_sql = str(output_path).replace("'", "''")
        reader = "read_json_auto" if input_path.suffix.lower() == ".jsonl" else "read_csv_auto"
        subprocess.run(
            [
                duckdb_cli,
                "-c",
                f"copy (select * from {reader}('{input_sql}')) to '{output_sql}' (format parquet, compression zstd);",
            ],
            check=True,
        )
        print(f"OK: {len(records)} trials gravados em {output_path}")
        return

    with duckdb.connect(":memory:") as conn:
        conn.execute(
            """
            create table trials (
                trial_id varchar,
                participant varchar,
                kata varchar,
                treatment varchar,
                assistant varchar,
                timebox_seconds integer,
                time_to_green_seconds integer,
                censored boolean,
                tests_passed integer,
                tests_failed integer,
                acceptance_success_rate double,
                cyclomatic_complexity_avg double,
                cyclomatic_complexity_max integer,
                maintainability_index double,
                loc integer,
                lloc integer,
                sloc integer,
                duplication_pct double,
                solution_path varchar,
                started_at varchar,
                finished_at varchar
            )
            """
        )
        columns = [
            "trial_id",
            "participant",
            "kata",
            "treatment",
            "assistant",
            "timebox_seconds",
            "time_to_green_seconds",
            "censored",
            "tests_passed",
            "tests_failed",
            "acceptance_success_rate",
            "cyclomatic_complexity_avg",
            "cyclomatic_complexity_max",
            "maintainability_index",
            "loc",
            "lloc",
            "sloc",
            "duplication_pct",
            "solution_path",
            "started_at",
            "finished_at",
        ]
        placeholders = ", ".join(["?"] * len(columns))
        conn.executemany(
            f"insert into trials values ({placeholders})",
            [[record.get(column) for column in columns] for record in records],
        )
        conn.execute(
            "copy trials to ? (format parquet, compression zstd)",
            [str(output_path)],
        )

    print(f"OK: {len(records)} trials gravados em {output_path}")


if __name__ == "__main__":
    main()
