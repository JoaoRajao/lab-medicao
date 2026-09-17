from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = LAB_DIR / "data" / "raw" / "trials.jsonl"
TIMEBOX_SECONDS = 35 * 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa um trial Lab02 e registra tempo/testes.")
    parser.add_argument("--participant", required=True, help="Identificador do participante, ex.: P1.")
    parser.add_argument("--kata", required=True, help="Nome do kata em labs/lab02_ia_vs_manual/katas.")
    parser.add_argument(
        "--treatment",
        required=True,
        choices=["manual", "ai_assisted"],
        help="Tratamento usado no trial.",
    )
    parser.add_argument(
        "--solution-path",
        type=Path,
        help="Arquivo de solucao a medir. Padrao: labs/lab02_ia_vs_manual/katas/<kata>/solution.py.",
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
    parser.add_argument(
        "--check-interval-seconds",
        type=float,
        default=5.0,
        help="Intervalo entre verificacoes pytest enquanto o trial esta ativo.",
    )
    return parser.parse_args()


def count_pytest_results(output: str) -> tuple[int, int]:
    # Pytest's short summary uses space-separated tokens, e.g. "1 failed, 2 passed
    # in 0.06s" -- the count and its label are always two separate tokens.
    passed = 0
    failed = 0
    tokens = output.replace(",", " ").split()
    for index, token in enumerate(tokens[:-1]):
        if not token.isdigit():
            continue
        label = tokens[index + 1]
        if label == "passed":
            passed += int(token)
        elif label == "failed":
            failed += int(token)
    return passed, failed


def run_pytest(kata: str, timeout_seconds: int) -> tuple[bool, int, int, str]:
    kata_path = LAB_DIR / "katas" / kata
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(kata_path), "-q"],
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
        check=False,
    )
    passed, failed = count_pytest_results(completed.stdout)
    return completed.returncode == 0, passed, failed, completed.stdout[-4000:]


def measure_trial(kata: str, timebox_seconds: int, check_interval_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    tests_passed = 0
    tests_failed = 0
    pytest_tail = ""

    while True:
        remaining = timebox_seconds - (time.monotonic() - started)
        if remaining <= 0:
            break

        try:
            success, tests_passed, tests_failed, pytest_tail = run_pytest(
                kata, max(1, math.ceil(remaining))
            )
        except subprocess.TimeoutExpired as error:
            success = False
            pytest_tail = str(error)

        elapsed = time.monotonic() - started
        if success and elapsed <= timebox_seconds:
            return {
                "time_to_green_seconds": math.ceil(elapsed),
                "censored": False,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "pytest_output_tail": pytest_tail,
            }
        if elapsed >= timebox_seconds:
            break
        time.sleep(min(check_interval_seconds, timebox_seconds - elapsed))

    return {
        "time_to_green_seconds": timebox_seconds,
        "censored": True,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "pytest_output_tail": pytest_tail,
    }


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        file.write("\n")


def main() -> None:
    args = parse_args()
    solution_path = args.solution_path or LAB_DIR / "katas" / args.kata / "solution.py"
    if not solution_path.is_absolute():
        solution_path = ROOT_DIR / solution_path
    if args.timebox_seconds <= 0 or args.check_interval_seconds <= 0:
        raise ValueError("O time-box e o intervalo de verificacao precisam ser positivos")
    if not solution_path.is_file():
        raise FileNotFoundError(f"Solucao nao encontrada: {solution_path}")

    trial_id = f"{args.participant}-{args.kata}-{args.treatment}"
    if args.output.exists():
        with args.output.open("r", encoding="utf-8") as file:
            if any(json.loads(line).get("trial_id") == trial_id for line in file if line.strip()):
                raise ValueError(f"Trial ja registrado em {args.output}: {trial_id}")

    started_at = datetime.now(timezone.utc)
    print(f"Trial {trial_id} iniciado. Programe em outro terminal; verificacoes ate {args.timebox_seconds}s.", flush=True)
    result = measure_trial(args.kata, args.timebox_seconds, args.check_interval_seconds)

    record = {
        "trial_id": trial_id,
        "participant": args.participant,
        "kata": args.kata,
        "treatment": args.treatment,
        "assistant": "ChatGPT" if args.treatment == "ai_assisted" else None,
        "timebox_seconds": args.timebox_seconds,
        "time_to_green_seconds": result["time_to_green_seconds"],
        "censored": result["censored"],
        "tests_passed": result["tests_passed"],
        "tests_failed": result["tests_failed"],
        "acceptance_success_rate": result["tests_passed"] / max(result["tests_passed"] + result["tests_failed"], 1),
        "solution_path": solution_path.relative_to(ROOT_DIR).as_posix(),
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "pytest_output_tail": result["pytest_output_tail"],
    }
    append_record(args.output, record)
    print(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
