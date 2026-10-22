"""Compara versoes da heuristica de release corretiva contra a amostra-ouro (secao 6 do enunciado).

O enunciado pede que cada versao testada e o F1 obtido sejam documentados. Este script recalcula todas a
partir de `releases.csv` (patch do SemVer e commits de correcao entre releases) e do consenso, sem API:

    python -m labs.lab03_dora.avaliar_heuristicas
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Sequence

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from labs.lab03_dora.amostra_ouro import GOLD_DIR, read_labels
from labs.lab03_dora.metricas.cfr_b import FIX_SHARE, SEMVER, VERSION

LAB_DIR = Path(__file__).resolve().parent
RELEASES = LAB_DIR / "data" / "releases.csv"
OUTPUT = GOLD_DIR / "heuristicas_f1.csv"
EVALUATORS = ("pedro", "joao", "salomao")


def patch_increment(tag: str, previous: str) -> bool:
    current, before = SEMVER.fullmatch(tag or ""), SEMVER.fullmatch(previous or "")
    if not (current and before):
        return False
    return current.groups()[:2] == before.groups()[:2] and int(current.group(3)) > int(before.group(3))


def signals(releases: pd.DataFrame) -> pd.DataFrame:
    frame = releases.copy()
    frame["patch"] = [patch_increment(t, p if isinstance(p, str) else "") for t, p in zip(frame.tag_name, frame.previous_tag)]
    total = frame.commits_compared.astype(int)
    frame["fix_share"] = (frame.fix_commits.astype(int) / total.where(total > 0)).fillna(0.0)
    frame["any_fix"] = frame.fix_commits.astype(int) > 0
    return frame


# Versoes na ordem em que foram testadas; a final e a implementada em metricas/cfr_b.py.
VERSIONS: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "semver-patch-v1": lambda f: f.patch,
    "patch-ou-qualquer-commit-fix": lambda f: f.patch | f.any_fix,
    "patch-ou-50pct-commits-fix": lambda f: f.patch | (f.fix_share >= 0.5),
    VERSION: lambda f: f.patch | (f.fix_share >= FIX_SHARE),
    "referencia-tudo-corretiva": lambda f: pd.Series(True, index=f.index),
}


def score(truth: pd.Series, predicted: pd.Series) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(truth, predicted, average="binary", zero_division=0)
    return {"precisao": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "positivos_previstos": int(predicted.sum()), "positivos_referencia": int(truth.sum())}


def evaluate(releases: pd.DataFrame, references: dict[str, pd.Series]) -> pd.DataFrame:
    frame = signals(releases.drop_duplicates(["repository", "tag_name"])).set_index(["repository", "tag_name"])
    rows = []
    for reference, truth in references.items():
        keys = truth.index
        missing = keys.difference(frame.index)
        if len(missing):
            raise ValueError(f"{len(missing)} release(s) da amostra-ouro ausentes em releases.csv, ex.: {list(missing[:2])}")
        subset = frame.loc[keys]
        for version, rule in VERSIONS.items():
            rows.append({"referencia": reference, "versao": version, **score(truth, rule(subset).astype(bool))})
    return pd.DataFrame(rows)


def references(gold_dir: Path) -> dict[str, pd.Series]:
    consensus = pd.read_csv(gold_dir / "consenso_releases.csv", dtype=str)
    found = {"consenso": consensus.set_index(["repositorio", "tag"]).corretiva.eq("sim").rename_axis(["repository", "tag_name"])}
    for name in EVALUATORS:
        _, labels = read_labels(gold_dir / f"rotulagem_{name}.xlsx")
        found[f"avaliador_{name}"] = labels.set_index(["repositorio", "tag"]).corretiva.eq("sim").rename_axis(
            ["repository", "tag_name"])
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F1 de cada versao da heuristica de release corretiva.")
    parser.add_argument("--releases", type=Path, default=RELEASES)
    parser.add_argument("--amostra-ouro", type=Path, default=GOLD_DIR)
    parser.add_argument("--saida", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    releases = pd.read_csv(args.releases, dtype={"tag_name": str, "previous_tag": str})
    result = evaluate(releases, references(args.amostra_ouro))
    result.to_csv(args.saida, index=False)
    print(result.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
