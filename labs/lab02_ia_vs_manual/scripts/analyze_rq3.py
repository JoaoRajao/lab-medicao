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
]
DEFAULT_OUTPUT = ROOT_DIR / "docs" / "lab02" / "rq3_analise.md"

METRICS = [
    ("cyclomatic_complexity_avg", "Complexidade ciclomática media"),
    ("maintainability_index", "Maintainability Index"),
    ("loc", "LOC"),
    ("duplication_pct", "Duplicacao (%)"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera analise RQ3 do Lab02.")
    parser.add_argument("--input", type=Path, nargs="+", default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def build_markdown(input_paths: list[Path]) -> str:
    records = load_trials_from_paths(input_paths)
    participants = ", ".join(sorted({record["participant"] for record in records}))
    lines = [
        "# Lab02 - Analise RQ3",
        "",
        f"Base analisada: {len(records)} trials consolidados ({participants}). Os demais trials ainda nao entram nesta versao.",
        "Os testes de Wilcoxon usam pares por participante: para cada participante, compara-se a media dos trials `ai_assisted` contra a media dos trials `manual`. O delta reportado e `ai_assisted - manual`.",
        "",
        "## Medianas e IQR",
        "",
    ]

    for metric, label in METRICS:
        lines.extend([metric_table(records, metric, label), ""])

    lines.extend(
        [
            "## Outliers",
            "",
        ]
    )
    for metric, label in METRICS:
        lines.extend(outlier_lines(records, metric, label))

    lines.extend(
        [
            "",
            "## Wilcoxon",
            "",
            "| Metrica | Pares por participante | Mediana do delta | Estatistica W | p-valor | Observacao |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for metric, label in METRICS:
        lines.append(wilcoxon_line(records, metric, label))

    lines.extend(
        [
            "",
            "Com alfa=0.05, nenhuma hipotese nula foi rejeitada para as metricas estruturais.",
            "",
            "## Discussao",
            "",
            "- Complexidade: as medianas por tratamento ficam proximas, com variacao maior dependente do kata do que do tratamento.",
            "- Maintainability Index: o `ai_assisted` fica ligeiramente abaixo na mediana, mas a diferenca e pequena para sustentar conclusao forte com esta amostra.",
            "- LOC: o tratamento `ai_assisted` apresenta mediana maior, embora a diferenca pareada por participante seja pequena na amostra.",
            "- Duplicacao: todos os registros tiveram duplicacao 0%, entao Wilcoxon e nao informativo nessa metrica.",
            "- Interpretacao: RQ3 nao mostra evidencia robusta de degradacao estrutural causada por IA; o sinal mais claro e que solucoes variam mais pelo kata e estilo individual do que pelo tratamento.",
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
    print(f"OK: analise RQ3 gravada em {output_path}")


if __name__ == "__main__":
    main()
