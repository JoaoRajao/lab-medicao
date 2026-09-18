from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = LAB_DIR / "data" / "raw" / "trials.jsonl"
STATE_DIR = LAB_DIR / "data" / "raw" / ".trial_state"
TIMEBOX_SECONDS = 35 * 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cronometra um trial Lab02 em tres etapas: start, check e stop."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--participant", required=True, help="Identificador do participante, ex.: P1.")
    common.add_argument("--kata", required=True, help="Nome do kata em labs/lab02_ia_vs_manual/katas.")
    common.add_argument(
        "--treatment",
        required=True,
        choices=["manual", "ai_assisted"],
        help="Tratamento usado no trial.",
    )

    start_parser = subparsers.add_parser("start", parents=[common], help="Inicia o cronometro do trial.")
    start_parser.add_argument(
        "--timebox-seconds",
        type=int,
        default=TIMEBOX_SECONDS,
        help="Limite do trial em segundos.",
    )
    start_parser.add_argument(
        "--assistant",
        default=None,
        help="Nome do assistente de IA usado (obrigatorio faz sentido so para ai_assisted).",
    )
    start_parser.add_argument("--force", action="store_true", help="Sobrescreve um timer ja ativo.")

    subparsers.add_parser("check", parents=[common], help="Roda os testes sem parar o cronometro.")

    stop_parser = subparsers.add_parser("stop", parents=[common], help="Encerra o cronometro e grava o registro.")
    stop_parser.add_argument(
        "--solution-path",
        type=Path,
        help="Arquivo de solucao a medir. Padrao: labs/lab02_ia_vs_manual/katas/<kata>/solution.py.",
    )
    stop_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Arquivo JSONL de saida.",
    )

    return parser.parse_args()


def trial_id_for(participant: str, kata: str, treatment: str) -> str:
    return f"{participant}-{kata}-{treatment}"


def state_path_for(trial_id: str) -> Path:
    return STATE_DIR / f"{trial_id}.json"


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


def run_pytest(kata: str) -> tuple[bool, int, int, str]:
    kata_path = LAB_DIR / "katas" / kata
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(kata_path), "-q"],
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    passed, failed = count_pytest_results(completed.stdout)
    return completed.returncode == 0, passed, failed, completed.stdout[-4000:]


def load_state(trial_id: str) -> dict[str, Any]:
    path = state_path_for(trial_id)
    if not path.exists():
        raise SystemExit(
            f"Nenhum timer ativo para {trial_id}. Rode 'start' antes de 'check'/'stop'."
        )
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def cmd_start(args: argparse.Namespace) -> None:
    trial_id = trial_id_for(args.participant, args.kata, args.treatment)
    path = state_path_for(trial_id)
    if path.exists() and not args.force:
        raise SystemExit(
            f"Timer para {trial_id} ja esta ativo (desde {json.loads(path.read_text())['started_at']}). "
            "Use --force para reiniciar."
        )

    assistant = args.assistant
    if assistant is None and args.treatment == "ai_assisted":
        assistant = "ChatGPT"

    state = {
        "trial_id": trial_id,
        "participant": args.participant,
        "kata": args.kata,
        "treatment": args.treatment,
        "assistant": assistant,
        "timebox_seconds": args.timebox_seconds,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Timer iniciado para {trial_id} em {state['started_at']} (timebox={args.timebox_seconds}s).")


def cmd_check(args: argparse.Namespace) -> None:
    trial_id = trial_id_for(args.participant, args.kata, args.treatment)
    state = load_state(trial_id)
    started_at = datetime.fromisoformat(state["started_at"])
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    remaining = state["timebox_seconds"] - elapsed

    success, tests_passed, tests_failed, pytest_tail = run_pytest(args.kata)
    print(f"[{trial_id}] tests_passed={tests_passed} tests_failed={tests_failed} success={success}")
    print(f"[{trial_id}] elapsed={int(elapsed)}s remaining={int(remaining)}s")
    if remaining <= 0:
        print(f"[{trial_id}] AVISO: timebox esgotado. Rode 'stop' para registrar como censurado.")
    if not success:
        print(pytest_tail[-1000:])


def cmd_stop(args: argparse.Namespace) -> None:
    trial_id = trial_id_for(args.participant, args.kata, args.treatment)
    state = load_state(trial_id)
    started_at = datetime.fromisoformat(state["started_at"])
    timebox_seconds = state["timebox_seconds"]

    solution_path = args.solution_path or LAB_DIR / "katas" / args.kata / "solution.py"

    success, tests_passed, tests_failed, pytest_tail = run_pytest(args.kata)
    finished_at = datetime.now(timezone.utc)
    elapsed_seconds = min(int((finished_at - started_at).total_seconds()), timebox_seconds)
    censored = not success and elapsed_seconds >= timebox_seconds

    record = {
        "trial_id": trial_id,
        "participant": args.participant,
        "kata": args.kata,
        "treatment": args.treatment,
        "assistant": state.get("assistant"),
        "timebox_seconds": timebox_seconds,
        "time_to_green_seconds": elapsed_seconds if success else timebox_seconds,
        "censored": censored,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "acceptance_success_rate": tests_passed / max(tests_passed + tests_failed, 1),
        "solution_path": solution_path.relative_to(ROOT_DIR).as_posix(),
        "started_at": state["started_at"],
        "finished_at": finished_at.isoformat(),
        "pytest_output_tail": pytest_tail,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
        file.write("\n")

    state_path_for(trial_id).unlink(missing_ok=True)
    print(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True))


def main() -> None:
    args = parse_args()
    if args.command == "start":
        cmd_start(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "stop":
        cmd_stop(args)


if __name__ == "__main__":
    main()
