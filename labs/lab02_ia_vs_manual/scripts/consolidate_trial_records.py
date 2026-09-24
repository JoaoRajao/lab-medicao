from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LAB_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = LAB_DIR / "data" / "raw"

PARTICIPANT_ORDERS: dict[str, list[tuple[str, str]]] = {
    "P1": [
        ("warehouse_batches", "manual"),
        ("route_reconciliation", "ai_assisted"),
        ("invoice_window", "manual"),
        ("sensor_anomaly", "ai_assisted"),
        ("support_queue", "manual"),
        ("dependency_unlock", "ai_assisted"),
    ],
    "P2": [
        ("warehouse_batches", "ai_assisted"),
        ("route_reconciliation", "manual"),
        ("invoice_window", "ai_assisted"),
        ("sensor_anomaly", "manual"),
        ("support_queue", "ai_assisted"),
        ("dependency_unlock", "manual"),
    ],
    "P3": [
        ("warehouse_batches", "manual"),
        ("route_reconciliation", "ai_assisted"),
        ("invoice_window", "ai_assisted"),
        ("sensor_anomaly", "manual"),
        ("support_queue", "manual"),
        ("dependency_unlock", "ai_assisted"),
    ],
}
P2_ORDER = PARTICIPANT_ORDERS["P2"]

PARTICIPANT_NAME_ALIASES: dict[str, str] = {
    "P1": "pedro",
    "P2": "joao",
    "P3": "salomao",
}

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
    parser = argparse.ArgumentParser(description="Consolida os seis trials reais de um participante.")
    parser.add_argument(
        "--participant",
        choices=["P1", "P2", "P3"],
        default="P2",
        help="Identificador do participante (P1, P2, P3). Padrao: P2.",
    )
    parser.add_argument("--timing", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    alias = PARTICIPANT_NAME_ALIASES.get(args.participant, args.participant.lower())
    if args.timing is None:
        args.timing = RAW_DIR / f"trials_{alias}_timing.jsonl"
    if args.metrics is None:
        args.metrics = RAW_DIR / f"trials_{alias}_metrics.jsonl"
    if args.output is None:
        args.output = RAW_DIR / f"trials_{alias}.jsonl"

    return args


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
    timing: dict[str, dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
    participant: str = "P2",
) -> list[dict[str, Any]]:
    order = PARTICIPANT_ORDERS.get(participant)
    if not order:
        raise ValueError(f"Participante desconhecido: {participant}")

    expected = [f"{participant}-{kata}-{treatment}" for kata, treatment in order]
    if set(timing) != set(expected) or set(metrics) != set(expected):
        raise ValueError(
            f"Sao exigidos os seis IDs {participant} em ambos os arquivos; "
            f"tempo ausentes={sorted(set(expected) - set(timing))}, "
            f"metricas ausentes={sorted(set(expected) - set(metrics))}, "
            f"IDs inesperados={sorted((set(timing) | set(metrics)) - set(expected))}"
        )

    result = []
    previous_start = ""
    for trial_id, (kata, treatment) in zip(expected, order, strict=True):
        time_record = timing[trial_id]
        metric_record = metrics[trial_id]
        for record in (time_record, metric_record):
            if (record.get("participant"), record.get("kata"), record.get("treatment")) != (
                participant, kata, treatment
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
    records = consolidate(
        load_by_trial_id(args.timing),
        load_by_trial_id(args.metrics),
        participant=args.participant,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_name(f".{args.output.name}.tmp")
    try:
        with temporary_output.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
        temporary_output.replace(args.output)
    finally:
        temporary_output.unlink(missing_ok=True)
    print(f"OK: {len(records)} trials {args.participant} consolidados em {args.output}")


if __name__ == "__main__":
    main()
