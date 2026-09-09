from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT_DIR / "lab02" / "data" / "raw" / "trials.jsonl"
TIMEBOX_SECONDS = 35 * 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa um trial Lab02 e registra tempo/testes.")
    parser.add_argument("--participant", required=True, help="Identificador do participante, ex.: P1.")
    parser.add_argument("--kata", required=True, help="Nome do kata em lab02/katas.")
    parser.add_argument(
        "--treatment",
        required=True,
        choices=["manual", "ai_assisted"],
        help="Tratamento usado no trial.",
    )
    parser.add_argument(
        "--solution-path",
        type=Path,
        help="Arquivo de solucao a medir. Padrao: lab02/katas/<kata>/solution.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Arquivo JSONL de saida.",
    )
    parser.add_argument(
        "--timebox-seconds",
        type=int,
        default=TIMEBOX_SECONDS,
        help="Limite do trial em segundos.",
    )
    return parser.parse_args()


def count_pytest_results(output: str) -> tuple[int, int]:
    passed = 0
    failed = 0
    for token in output.replace(",", " ").split():
        if token.endswith("passed") and token[:-6].isdigit():
            passed += int(token[:-6])
        if token.endswith("failed") and token[:-6].isdigit():
            failed += int(token[:-6])
    return passed, failed


def run_pytest(kata: str, timebox_seconds: int) -> tuple[bool, int, int, str]:
    kata_path = ROOT_DIR / "lab02" / "katas" / kata
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(kata_path), "-q"],
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timebox_seconds,
        check=False,
    )
    elapsed = int(round(time.monotonic() - started))
    passed, failed = count_pytest_results(completed.stdout)
    return completed.returncode == 0, passed, failed, completed.stdout[-4000:]


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        file.write("\n")


def main() -> None:
    args = parse_args()
    solution_path = args.solution_path or ROOT_DIR / "lab02" / "katas" / args.kata / "solution.py"

    started_at = datetime.now(timezone.utc)
    try:
        success, tests_passed, tests_failed, pytest_tail = run_pytest(
            args.kata,
            args.timebox_seconds,
        )
        elapsed_seconds = min(int((datetime.now(timezone.utc) - started_at).total_seconds()), args.timebox_seconds)
        censored = not success and elapsed_seconds >= args.timebox_seconds
    except subprocess.TimeoutExpired as error:
        success = False
        tests_passed = 0
        tests_failed = 0
        pytest_tail = str(error)
        elapsed_seconds = args.timebox_seconds
        censored = True

    record = {
        "trial_id": f"{args.participant}-{args.kata}-{args.treatment}",
        "participant": args.participant,
        "kata": args.kata,
        "treatment": args.treatment,
        "assistant": "ChatGPT" if args.treatment == "ai_assisted" else None,
        "timebox_seconds": args.timebox_seconds,
        "time_to_green_seconds": elapsed_seconds if success else args.timebox_seconds,
        "censored": censored,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "acceptance_success_rate": tests_passed / max(tests_passed + tests_failed, 1),
        "solution_path": str(solution_path.relative_to(ROOT_DIR)),
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "pytest_output_tail": pytest_tail,
    }
    append_record(args.output, record)
    print(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
