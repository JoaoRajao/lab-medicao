from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from shared.warehouse import create_and_load_table, export_table

ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = LAB_DIR / "data" / "raw" / "trials_sample.jsonl"
DEFAULT_OUTPUT = LAB_DIR / "data" / "parquet" / "trials.parquet"

TABLE_NAME = "lab02_trials"
TABLE_COLUMNS: list[tuple[str, str]] = [
    ("trial_id", "varchar"),
    ("participant", "varchar"),
    ("kata", "varchar"),
    ("treatment", "varchar"),
    ("assistant", "varchar"),
    ("timebox_seconds", "integer"),
    ("time_to_green_seconds", "integer"),
    ("censored", "boolean"),
    ("tests_passed", "integer"),
    ("tests_failed", "integer"),
    ("acceptance_success_rate", "double"),
    ("cyclomatic_complexity_avg", "double"),
    ("cyclomatic_complexity_max", "integer"),
    ("maintainability_index", "double"),
    ("loc", "integer"),
    ("lloc", "integer"),
    ("sloc", "integer"),
    ("duplication_pct", "double"),
    ("solution_path", "varchar"),
    ("started_at", "timestamptz"),
    ("finished_at", "timestamptz"),
]
RECORD_COLUMNS = [name for name, _ in TABLE_COLUMNS]

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
    parser = argparse.ArgumentParser(
        description="Converte resultados de trials Lab02 (JSONL/CSV) para a tabela lab02_trials no warehouse + Parquet."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def coerce_record(record: dict[str, Any]) -> dict[str, Any]:
    coerced = {column: record.get(column) for column in RECORD_COLUMNS}
    for field in BOOLEAN_FIELDS:
        if isinstance(coerced[field], str):
            coerced[field] = coerced[field].strip().lower() in {"true", "1", "yes", "sim"}
    for field in INTEGER_FIELDS:
        if coerced[field] not in (None, ""):
            coerced[field] = int(float(coerced[field]))
    for field in FLOAT_FIELDS:
        if coerced[field] not in (None, ""):
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

    create_and_load_table(TABLE_NAME, TABLE_COLUMNS, records)
    temporary_output = output_path.with_name(f".{output_path.name}.tmp")
    try:
        export_table(TABLE_NAME, parquet_path=temporary_output)
        temporary_output.replace(output_path)
    finally:
        temporary_output.unlink(missing_ok=True)
    print(f"OK: {len(records)} trials gravados na tabela {TABLE_NAME} e em {output_path}")


if __name__ == "__main__":
    main()
