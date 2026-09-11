from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
KATAS_DIR = LAB_DIR / "katas"
DEFAULT_JSON_OUTPUT = LAB_DIR / "data" / "raw" / "kata_baselines.json"
DEFAULT_DOC_OUTPUT = ROOT_DIR / "docs" / "lab02" / "kata_baselines.md"

sys.path.insert(0, str(ROOT_DIR))

from labs.lab02_ia_vs_manual.scripts.collect_static_metrics import (
    collect_duplication_pct,
    collect_radon_metrics,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera baselines de métricas estáticas e testes dos gabaritos dos katas do Lab02."
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--doc-output", type=Path, default=DEFAULT_DOC_OUTPUT)
    return parser.parse_args()


def run_pytest_for_kata(kata_dir: Path) -> dict[str, Any]:
    test_file = kata_dir / "test_solution.py"
    solution_path = kata_dir / "solution.py"
    reference_path = kata_dir / "reference_solution.py"
    backup_path = kata_dir / "solution.py.stub_backup"

    if not test_file.exists():
        return {"passed": False, "return_code": -1, "raw_output": "test_solution.py missing"}

    has_ref = reference_path.exists()
    if has_ref:
        shutil.copy(solution_path, backup_path)
        shutil.copy(reference_path, solution_path)

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q", "--tb=no"],
            cwd=ROOT_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        output = completed.stdout + "\n" + completed.stderr
        passed = completed.returncode == 0
        return {
            "passed": passed,
            "return_code": completed.returncode,
            "raw_output": output.strip(),
        }
    finally:
        if has_ref:
            shutil.copy(backup_path, solution_path)
            backup_path.unlink()


def generate_baselines() -> list[dict[str, Any]]:
    kata_dirs = sorted([d for d in KATAS_DIR.iterdir() if d.is_dir() and not d.name.startswith("__")])
    baselines: list[dict[str, Any]] = []

    for kata_dir in kata_dirs:
        ref_path = kata_dir / "reference_solution.py"
        target_path = ref_path if ref_path.exists() else kata_dir / "solution.py"
        if not target_path.exists():
            continue

        print(f"Processando kata: {kata_dir.name}...", flush=True)
        radon_metrics = collect_radon_metrics(target_path)
        duplication_pct = collect_duplication_pct(target_path)
        pytest_result = run_pytest_for_kata(kata_dir)

        baseline = {
            "kata": kata_dir.name,
            "solution_path": target_path.relative_to(ROOT_DIR).as_posix(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "all_tests_passed": pytest_result["passed"],
            "duplication_pct": duplication_pct,
            **radon_metrics,
        }
        baselines.append(baseline)

    return baselines


def write_markdown_report(baselines: list[dict[str, Any]], doc_path: Path) -> None:
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Baselines dos Katas - Lab02",
        "",
        f"**Data de Geração:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "Este documento registra os valores de referência (baselines) das métricas estáticas e funcionais obtidos a partir das soluções gabarito autorais dos 6 katas.",
        "",
        "## Resumo das Métricas dos Gabaritos",
        "",
        "| Kata | Testes OK | Complexidade Média (CC) | Complexidade Max | Índice Manutenibilidade (MI) | Duplicação (%) | LOC | SLOC |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for b in baselines:
        tests_status = "PASS" if b["all_tests_passed"] else "FAIL"
        dup = f"{b['duplication_pct']:.2f}%" if b["duplication_pct"] is not None else "0.00%"
        mi = f"{b['maintainability_index']:.2f}" if b["maintainability_index"] is not None else "N/A"
        lines.append(
            f"| `{b['kata']}` | {tests_status} | {b['cyclomatic_complexity_avg']:.2f} | {b['cyclomatic_complexity_max']} | {mi} | {dup} | {b['loc']} | {b['sloc']} |"
        )

    lines.extend(
        [
            "",
            "## Considerações para Comparação (RQ3)",
            "- **Complexidade Ciclomática (CC)**: Soluções manuais ou geradas por IA devem ser comparadas contra a complexidade baseline para avaliar super-engenharia ou redundância.",
            "- **Manutenibilidade (MI)**: Valores acima de 65 indicam boa manutenibilidade.",
            "- **Duplicação**: O valor de referência serve de limite mínimo de controle.",
        ]
    )

    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    baselines = generate_baselines()

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    with args.json_output.open("w", encoding="utf-8") as f:
        json.dump(baselines, f, indent=2, ensure_ascii=False)
    print(f"Baselines JSON salvos em: {args.json_output}", flush=True)

    write_markdown_report(baselines, args.doc_output)
    print(f"Relatório Markdown salvo em: {args.doc_output}", flush=True)


if __name__ == "__main__":
    main()
