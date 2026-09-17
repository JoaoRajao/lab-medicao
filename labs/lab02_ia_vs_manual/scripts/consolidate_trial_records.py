from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LAB_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = LAB_DIR / "data" / "raw"
P2_ORDER = [
    ("warehouse_batches", "ai_assisted"),
    ("route_reconciliation", "manual"),
    ("invoice_window", "ai_assisted"),
    ("sensor_anomaly", "manual"),
    ("support_queue", "ai_assisted"),
    ("dependency_unlock", "manual"),
]
STATIC_FIELDS = {
    "cyclomatic_complexity_avg",
    "cyclomatic_complexity_max",
    "maintainability_index",
    "loc",
    "lloc",
    "sloc",
    "duplication_pct",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolida os seis trials reais do participante P2.")
    parser.add_argument("--timing", type=Path, default=RAW_DIR / "trials_joao_timing.jsonl")
    parser.add_argument("--metrics", type=Path, default=RAW_DIR / "trials_joao_metrics.jsonl")
    parser.add_argument("--output", type=Path, default=RAW_DIR / "trials_joao.jsonl")
    return parser.parse_args()


def load_by_trial_id(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            trial_id = record.get("trial_id")
            if not isinstance(trial_id, str) or not trial_id:
                raise ValueError(f"{path}:{line_number}: trial_id ausente")
            if trial_id in records:
                raise ValueError(f"{path}:{line_number}: trial_id duplicado: {trial_id}")
            records[trial_id] = record
    return records


def consolidate(
    timing: dict[str, dict[str, Any]], metrics: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    expected = [f"P2-{kata}-{treatment}" for kata, treatment in P2_ORDER]
    if set(timing) != set(expected) or set(metrics) != set(expected):
        raise ValueError(
            "Sao exigidos os seis IDs P2 em ambos os arquivos; "
            f"tempo ausentes={sorted(set(expected) - set(timing))}, "
            f"metricas ausentes={sorted(set(expected) - set(metrics))}, "
            f"IDs inesperados={sorted((set(timing) | set(metrics)) - set(expected))}"
        )

    result = []
    previous_start = ""
    for trial_id, (kata, treatment) in zip(expected, P2_ORDER, strict=True):
        time_record = timing[trial_id]
        metric_record = metrics[trial_id]
        for record in (time_record, metric_record):
            if (record.get("participant"), record.get("kata"), record.get("treatment")) != (
                "P2", kata, treatment
            ):
                raise ValueError(f"Metadados inconsistentes em {trial_id}")
        if time_record.get("solution_path") != metric_record.get("solution_path"):
            raise ValueError(f"solution_path inconsistente em {trial_id}")
        start = time_record.get("started_at")
        if not isinstance(start, str) or start <= previous_start:
            raise ValueError(f"Ordem ou started_at invalido em {trial_id}")
        previous_start = start
        missing = STATIC_FIELDS - metric_record.keys()
        if missing:
            raise ValueError(f"Metricas ausentes em {trial_id}: {sorted(missing)}")
        result.append({**time_record, **{field: metric_record[field] for field in STATIC_FIELDS}})
    return result


def main() -> None:
    args = parse_args()
    records = consolidate(load_by_trial_id(args.timing), load_by_trial_id(args.metrics))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_name(f".{args.output.name}.tmp")
    try:
        with temporary_output.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
        temporary_output.replace(args.output)
    finally:
        temporary_output.unlink(missing_ok=True)
    print(f"OK: {len(records)} trials P2 consolidados em {args.output}")


if __name__ == "__main__":
    main()
