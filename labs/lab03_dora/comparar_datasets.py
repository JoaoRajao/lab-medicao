"""Compara um dataset replicado com o original (secao 9 do enunciado, replicacao cruzada).

Para cada metrica: diferenca relativa por repositorio, `|replicado - original| / |original|`, resumida por
mediana e pela fracao de repositorios dentro de 10%; e a % de repositorios com a mesma classe DORA.

    python -m labs.lab03_dora.comparar_datasets --original A.csv --replicado B.csv [--saida pasta]

As colunas sao configuraveis para comparar com datasets de outros grupos:
`--metricas frequencia=deployment_frequency_per_week ...` usa `frequencia` no original e
`deployment_frequency_per_week` no replicado.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

DEFAULT_METRICS = (
    "deployment_frequency_per_week", "lead_time_a_hours", "lead_time_b_hours",
    "cfr_a", "cfr_b", "recovery_median_hours",
)
TOLERANCE = 0.10


def _pairs(specs: Sequence[str]) -> list[tuple[str, str]]:
    """`a=b` compara a coluna `a` do original com `b` do replicado; `a` sozinho usa o mesmo nome."""
    return [tuple(spec.split("=", 1)) if "=" in spec else (spec, spec) for spec in specs]


def relative_difference(original: pd.Series, replicated: pd.Series) -> pd.Series:
    """0 quando os dois sao 0; infinito quando so o original e 0."""
    diff = (replicated - original).abs()
    base = original.abs()
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = diff / base
    return relative.where(base != 0, np.where(diff == 0, 0.0, np.inf))


def compare(original: pd.DataFrame, replicated: pd.DataFrame, metrics: Sequence[tuple[str, str]],
            key: tuple[str, str] = ("repository", "repository"),
            category: tuple[str, str] | None = ("dora_category", "dora_category")) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    left = original.set_index(key[0])
    right = replicated.set_index(key[1])
    common = left.index.intersection(right.index)
    detail = pd.DataFrame(index=common.rename("repository"))
    rows = []
    for source, target in metrics:
        a = pd.to_numeric(left.loc[common, source], errors="coerce")
        b = pd.to_numeric(right.loc[common, target], errors="coerce")
        both = a.notna() & b.notna()
        relative = relative_difference(a[both], b[both])
        detail[f"{source}_original"], detail[f"{source}_replicado"] = a, b
        detail[f"{source}_dif_relativa"] = relative.reindex(common)
        finite = relative[np.isfinite(relative)]
        rows.append({
            "metrica": source, "pares": int(both.sum()),
            "so_no_original": int((a.notna() & b.isna()).sum()), "so_no_replicado": int((a.isna() & b.notna()).sum()),
            "mediana_dif_relativa": round(float(finite.median()), 4) if len(finite) else None,
            "dentro_de_10pct": round(float((relative <= TOLERANCE).mean()), 4) if len(relative) else None,
        })
    summary = {
        "repositorios_original": len(left), "repositorios_replicado": len(right), "em_comum": len(common),
        "so_no_original": sorted(left.index.difference(right.index)),
        "so_no_replicado": sorted(right.index.difference(left.index)),
    }
    if category is not None:
        same = left.loc[common, category[0]].astype(str) == right.loc[common, category[1]].astype(str)
        detail["mesma_classe_dora"] = same
        summary["mesma_classe_dora_pct"] = round(100 * float(same.mean()), 2) if len(common) else None
    return pd.DataFrame(rows), detail.reset_index(), summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compara dataset replicado com o original.")
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--replicado", type=Path, required=True)
    parser.add_argument("--metricas", nargs="+", default=list(DEFAULT_METRICS),
                        help="colunas a comparar; `orig=rep` quando os nomes diferem")
    parser.add_argument("--chave", default="repository", help="coluna do repositorio; `orig=rep` se diferirem")
    parser.add_argument("--classe", default="dora_category", help="classe DORA; `orig=rep` ou `nenhuma`")
    parser.add_argument("--saida", type=Path, help="pasta para os CSVs (padrao: pasta do replicado)")
    args = parser.parse_args(argv)
    try:
        original, replicated = pd.read_csv(args.original), pd.read_csv(args.replicado)
        key = _pairs([args.chave])[0]
        category = None if args.classe == "nenhuma" else _pairs([args.classe])[0]
        summary_rows, detail, summary = compare(original, replicated, _pairs(args.metricas), key, category)
    except (FileNotFoundError, KeyError) as error:
        print(f"Nao foi possivel comparar: {error}")
        return 1
    output = args.saida or args.replicado.parent
    output.mkdir(parents=True, exist_ok=True)
    summary_rows.to_csv(output / "comparacao_metricas.csv", index=False)
    detail.to_csv(output / "comparacao_por_repositorio.csv", index=False)
    print(f"Repositorios: {summary['em_comum']} em comum ({summary['repositorios_original']} no original, "
          f"{summary['repositorios_replicado']} no replicado).")
    if summary.get("mesma_classe_dora_pct") is not None:
        print(f"Mesma classe DORA: {summary['mesma_classe_dora_pct']}%")
    print(summary_rows.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
