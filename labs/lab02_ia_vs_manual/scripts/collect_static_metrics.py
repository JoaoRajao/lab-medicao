from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = LAB_DIR / "data" / "raw" / "static_metrics.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coleta metricas estaticas para um trial Lab02.")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--kata", required=True)
    parser.add_argument("--treatment", required=True, choices=["manual", "ai_assisted"])
    parser.add_argument("--solution-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def run_json_command(command: list[str]) -> Any:
    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(completed.stdout or "{}")


def collect_radon_metrics(solution_path: Path) -> dict[str, Any]:
    cc_raw = run_json_command([sys.executable, "-m", "radon", "cc", "-j", str(solution_path)])
    raw_raw = run_json_command([sys.executable, "-m", "radon", "raw", "-j", str(solution_path)])
    mi_raw = run_json_command([sys.executable, "-m", "radon", "mi", "-j", str(solution_path)])

    path_key = str(solution_path)
    complexities = [block["complexity"] for block in cc_raw.get(path_key, [])]
    raw_metrics = raw_raw.get(path_key, {})
    maintainability = mi_raw.get(path_key, {}).get("mi")

    return {
        "cyclomatic_complexity_avg": round(mean(complexities), 4) if complexities else 0.0,
        "cyclomatic_complexity_max": max(complexities) if complexities else 0,
        "maintainability_index": round(float(maintainability), 4) if maintainability is not None else None,
        "loc": int(raw_metrics.get("loc", 0)),
        "lloc": int(raw_metrics.get("lloc", 0)),
        "sloc": int(raw_metrics.get("sloc", 0)),
    }


def collect_duplication_pct(solution_path: Path) -> float | None:
    npx_path = shutil.which("npx")
    if npx_path is None:
        return None

    output_dir = LAB_DIR / "data" / "static_metrics"
    output_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            npx_path,
            "--yes",
            "jscpd",
            "--reporters",
            "json",
            "--output",
            str(output_dir),
            str(solution_path),
        ],
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        return None

    report_path = output_dir / "jscpd-report.json"
    if not report_path.exists():
        return None
    with report_path.open("r", encoding="utf-8") as file:
        report = json.load(file)
    return report.get("statistics", {}).get("total", {}).get("percentage")


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        file.write("\n")


def main() -> None:
    args = parse_args()
    solution_path = args.solution_path if args.solution_path.is_absolute() else ROOT_DIR / args.solution_path
    metrics = collect_radon_metrics(solution_path)
    metrics["duplication_pct"] = collect_duplication_pct(solution_path)

    record = {
        "trial_id": args.trial_id,
        "participant": args.participant,
        "kata": args.kata,
        "treatment": args.treatment,
        "solution_path": solution_path.relative_to(ROOT_DIR).as_posix(),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        **metrics,
    }
    append_record(args.output, record)
    print(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
