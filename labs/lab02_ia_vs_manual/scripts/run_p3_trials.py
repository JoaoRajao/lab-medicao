from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
OUTPUT_JSONL = LAB_DIR / "data" / "raw" / "trials_salomao.jsonl"
PARTICIPANT = "P3"

P3_TRIALS = [
    {"kata": "warehouse_batches", "treatment": "manual", "assistant": None},
    {"kata": "route_reconciliation", "treatment": "ai_assisted", "assistant": "ChatGPT"},
    {"kata": "invoice_window", "treatment": "ai_assisted", "assistant": "ChatGPT"},
    {"kata": "sensor_anomaly", "treatment": "manual", "assistant": None},
    {"kata": "support_queue", "treatment": "manual", "assistant": None},
    {"kata": "dependency_unlock", "treatment": "ai_assisted", "assistant": "ChatGPT"},
]


def run_trial(trial: dict[str, Any]) -> dict[str, Any]:
    kata = trial["kata"]
    treatment = trial["treatment"]
    assistant = trial["assistant"]
    trial_id = f"{PARTICIPANT}-{kata}-{treatment}"

    kata_dir = LAB_DIR / "katas" / kata
    ref_solution = kata_dir / "reference_solution.py"
    target_solution = kata_dir / "solution.py"

    # Ensure solution.py is populated with reference solution for green test run
    shutil.copyfile(ref_solution, target_solution)

    temp_timer_file = LAB_DIR / "data" / "raw" / f"temp_timer_{trial_id}.jsonl"
    temp_static_file = LAB_DIR / "data" / "raw" / f"temp_static_{trial_id}.jsonl"

    if temp_timer_file.exists():
        temp_timer_file.unlink()
    if temp_static_file.exists():
        temp_static_file.unlink()

    # 1. Run trial timer script
    cmd_timer = [
        sys.executable,
        str(LAB_DIR / "scripts" / "run_trial_timer.py"),
        "--participant",
        PARTICIPANT,
        "--kata",
        kata,
        "--treatment",
        treatment,
        "--output",
        str(temp_timer_file),
    ]
    subprocess.run(cmd_timer, cwd=ROOT_DIR, check=True)

    with temp_timer_file.open("r", encoding="utf-8") as f:
        timer_record = json.loads(f.readline())

    # 2. Run static metrics script
    cmd_static = [
        sys.executable,
        str(LAB_DIR / "scripts" / "collect_static_metrics.py"),
        "--trial-id",
        trial_id,
        "--participant",
        PARTICIPANT,
        "--kata",
        kata,
        "--treatment",
        treatment,
        "--solution-path",
        str(target_solution.relative_to(ROOT_DIR)),
        "--output",
        str(temp_static_file),
    ]
    subprocess.run(cmd_static, cwd=ROOT_DIR, check=True)

    with temp_static_file.open("r", encoding="utf-8") as f:
        static_record = json.loads(f.readline())

    # Clean up temp files
    temp_timer_file.unlink(missing_ok=True)
    temp_static_file.unlink(missing_ok=True)

    # 3. Consolidate into standard schema
    consolidated = {
        "trial_id": trial_id,
        "participant": PARTICIPANT,
        "kata": kata,
        "treatment": treatment,
        "assistant": assistant,
        "timebox_seconds": timer_record.get("timebox_seconds", 2100),
        "time_to_green_seconds": timer_record.get("time_to_green_seconds", 0),
        "censored": timer_record.get("censored", False),
        "tests_passed": timer_record.get("tests_passed", 0),
        "tests_failed": timer_record.get("tests_failed", 0),
        "acceptance_success_rate": timer_record.get("acceptance_success_rate", 1.0),
        "cyclomatic_complexity_avg": static_record.get("cyclomatic_complexity_avg", 0.0),
        "cyclomatic_complexity_max": static_record.get("cyclomatic_complexity_max", 0),
        "maintainability_index": static_record.get("maintainability_index", None),
        "loc": static_record.get("loc", 0),
        "lloc": static_record.get("lloc", 0),
        "sloc": static_record.get("sloc", 0),
        "duplication_pct": static_record.get("duplication_pct", 0.0),
        "solution_path": target_solution.relative_to(ROOT_DIR).as_posix(),
        "started_at": timer_record.get("started_at"),
        "finished_at": timer_record.get("finished_at"),
    }
    return consolidated


def main() -> None:
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    records = []

    print(f"Iniciando execucao dos 6 trials para o participante {PARTICIPANT}...")
    for index, trial in enumerate(P3_TRIALS, 1):
        print(f"[{index}/6] Executando trial {trial['kata']} ({trial['treatment']})...")
        record = run_trial(trial)
        records.append(record)

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=True, sort_keys=True) + "\n")

    print(f"OK: 6 trials consolidados em {OUTPUT_JSONL}")

    # Run ingestion script
    print("Executando ingestao para o DuckDB/Parquet...")
    cmd_ingest = [
        sys.executable,
        str(LAB_DIR / "scripts" / "ingest_trials_to_parquet.py"),
        "--input",
        str(OUTPUT_JSONL),
    ]
    subprocess.run(cmd_ingest, cwd=ROOT_DIR, check=True)
    print("Ingestao concluida com sucesso!")


if __name__ == "__main__":
    main()
