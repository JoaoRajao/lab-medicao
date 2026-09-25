from __future__ import annotations

import argparse
from pathlib import Path

from labs.lab02_ia_vs_manual.scripts.analysis_stats import (
    load_trials_from_paths,
    metric_table,
    outlier_lines,
    wilcoxon_line,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = [
    LAB_DIR / "data" / "raw" / "trials_pedro.jsonl",
    LAB_DIR / "data" / "raw" / "trials_joao.jsonl",
    LAB_DIR / "data" / "raw" / "trials_salomao.jsonl",
]
DEFAULT_OUTPUT = ROOT_DIR / "docs" / "lab02" / "rq1_rq2_analise.md"

METRICS = [
    ("time_to_green_seconds", "Tempo ate verde (s)"),
    ("acceptance_success_rate", "Taxa de sucesso"),
    ("tests_failed", "Falhas nos testes"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera analise RQ1/RQ2 do Lab02.")
    parser.add_argument("--input", type=Path, nargs="+", default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def build_markdown(input_paths: list[Path]) -> str:
    records = load_trials_from_paths(input_paths)
    participants = ", ".join(sorted({record["participant"] for record in records}))
    lines = [
        "# Lab02 - Analise RQ1/RQ2",
        "",
        f"Base analisada: {len(records)} trials consolidados ({participants}). Os demais trials ainda nao entram nesta versao.",
        "Os testes de Wilcoxon usam pares por participante: para cada participante, compara-se a media dos trials `ai_assisted` contra a media dos trials `manual`. O delta reportado e `ai_assisted - manual`.",
        "",
        "## RQ1 - Tempo ate verde",
        "",
        metric_table(records, "time_to_green_seconds", "Tempo ate verde (s)"),
        "",
        "### Outliers de tempo",
        "",
        *outlier_lines(records, "time_to_green_seconds", "Tempo ate verde (s)"),
        "",
        "## RQ2 - Sucesso e falhas",
        "",
        metric_table(records, "acceptance_success_rate", "Taxa de sucesso"),
        "",
        metric_table(records, "tests_failed", "Falhas nos testes"),
        "",
        "### Outliers de sucesso/falhas",
        "",
        *outlier_lines(records, "acceptance_success_rate", "Taxa de sucesso"),
        *outlier_lines(records, "tests_failed", "Falhas nos testes"),
        "",
        "## Wilcoxon",
        "",
        "| Metrica | Pares por participante | Mediana do delta | Estatistica W | p-valor | Observacao |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for metric, label in METRICS:
        lines.append(wilcoxon_line(records, metric, label))

    lines.extend(
        [
            "",
            "Com alfa=0.05, nenhuma hipotese nula foi rejeitada: tempo, sucesso e falhas tiveram p-valor acima do limiar ou diferencas pareadas todas iguais a zero.",
            "",
            "## Discussao",
            "",
            "- Tempo: o tratamento `ai_assisted` apresenta mediana menor que `manual`. A diferenca aparece nos dois participantes consolidados, com os tempos manuais de P2 atualizados a partir do cronometro externo informado.",
            "- Sucesso: todos os trials terminaram verdes, entao a taxa de sucesso e 1.0 para ambos os tratamentos.",
            "- Falhas: todos os registros finais tem `tests_failed = 0`; por isso, Wilcoxon para sucesso/falhas e nao informativo e retorna diferencas zero.",
            "- Interpretacao: com n pequeno e katas curtos, os resultados devem ser lidos como evidencia exploratoria. A mediana/IQR e mais apropriada que media simples porque reduz impacto de tempos extremos.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_paths = [path if path.is_absolute() else ROOT_DIR / path for path in args.input]
    output_path = args.output if args.output.is_absolute() else ROOT_DIR / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(input_paths), encoding="utf-8")
    print(f"OK: analise RQ1/RQ2 gravada em {output_path}")


if __name__ == "__main__":
    main()
