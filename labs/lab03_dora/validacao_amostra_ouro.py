"""Concordancia entre avaliadores, consenso e avaliacao da heuristica (#71)."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Sequence

import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from labs.lab03_dora.amostra_ouro import read_labels
from labs.lab03_dora.records import write_csv

DIMENSIONS = {
    "repositorios": ("tipo_projeto", "entregas_reais"),
    "releases": ("corretiva",),
}
KEYS = {"repositorios": ("repositorio",), "releases": ("repositorio", "tag")}
LANDIS_KOCH = (
    (0.20, "leve"),
    (0.40, "razoavel"),
    (0.60, "moderada"),
    (0.80, "substancial"),
    (1.0, "quase perfeita"),
)


def interpretation(value: float) -> str:
    if value < 0:
        return "abaixo do acaso"
    for limit, name in LANDIS_KOCH:
        if value <= limit:
            return name
    return "fora da escala"


def _indexed(frame: pd.DataFrame, keys: tuple[str, ...], evaluator: str) -> pd.DataFrame:
    if frame.duplicated(list(keys)).any():
        raise ValueError(f"{evaluator}: chaves duplicadas em {keys}")
    return frame.set_index(list(keys)).sort_index()


def align(frames: dict[str, tuple[pd.DataFrame, pd.DataFrame]], scope: str) -> dict[str, pd.DataFrame]:
    if len(frames) != 3:
        raise ValueError("Sao necessarios exatamente tres avaliadores.")
    indexed = {
        evaluator: _indexed(pair[0 if scope == "repositorios" else 1], KEYS[scope], evaluator)
        for evaluator, pair in frames.items()
    }
    base = next(iter(indexed.values())).index
    for evaluator, frame in indexed.items():
        if not frame.index.equals(base):
            raise ValueError(f"{evaluator}: chaves diferentes na aba {scope}.")
        for dimension in DIMENSIONS[scope]:
            if frame[dimension].isna().any():
                raise ValueError(f"{evaluator}: rotulos incompletos em {dimension}.")
    return indexed


def agreement(labels: pd.DataFrame) -> dict:
    counts, categories = aggregate_raters(labels.to_numpy())
    value = float(fleiss_kappa(counts))
    if pd.isna(value):
        raise ValueError("Kappa indefinido: todas as observacoes receberam a mesma categoria.")
    return {
        "n": len(labels), "categories": "|".join(map(str, categories)),
        "kappa": value, "interpretation": interpretation(value),
    }


def consensus(
    aligned: dict[str, pd.DataFrame], scope: str, resolutions: dict[tuple[str, str, str, str], tuple[str, str]],
) -> tuple[list[dict], list[dict]]:
    names = list(aligned)
    index = aligned[names[0]].index
    final, pending = [], []
    for key in index:
        key_tuple = key if isinstance(key, tuple) else (key,)
        repo, tag = key_tuple[0], key_tuple[1] if len(key_tuple) > 1 else ""
        row = {"repositorio": repo, "tag": tag}
        for dimension in DIMENSIONS[scope]:
            votes = [aligned[name].loc[key, dimension] for name in names]
            counts = Counter(votes)
            top_label, top_count = counts.most_common(1)[0]
            resolution_key = (scope, repo, tag, dimension)
            if top_count >= 2:
                selected, reason = top_label, "maioria"
            elif resolution_key in resolutions:
                selected, reason = resolutions[resolution_key]
                if selected not in votes or not reason:
                    raise ValueError(f"Desempate invalido para {resolution_key}.")
            else:
                selected, reason = "", "pendente"
                pending.append({"escopo": scope, "repositorio": repo, "tag": tag,
                                "dimensao": dimension, "votos": "|".join(votes)})
            row[dimension] = selected
            row[f"{dimension}_criterio"] = reason
        final.append(row)
    return final, pending


def load_resolutions(path: Path) -> dict[tuple[str, str, str, str], tuple[str, str]]:
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    result = {}
    for row in rows:
        key = (row["escopo"], row["repositorio"], row["tag"], row["dimensao"])
        if key in result:
            raise ValueError(f"Desempate duplicado: {key}")
        result[key] = (row["rotulo"], row["justificativa"])
    return result


def evaluate(consensus_releases: list[dict], predictions: list[dict]) -> dict:
    truth = {(row["repositorio"], row["tag"]): row["corretiva"] for row in consensus_releases}
    predicted = {}
    for row in predictions:
        key = (row["repository"], row["tag_name"])
        if key in predicted:
            raise ValueError(f"Predicoes com chave duplicada: {key}")
        predicted[key] = row
    if not set(truth).issubset(predicted):
        raise ValueError("Predicoes sem todas as chaves da amostra-ouro.")
    if any(value not in ("sim", "nao") for value in truth.values()):
        raise ValueError("Consenso ainda tem desempates pendentes.")
    keys = sorted(truth)
    actual, estimated = [truth[key] for key in keys], [predicted[key]["corrective"] for key in keys]
    versions = {predicted[key].get("heuristic_version", "") for key in keys}
    if len(versions) != 1:
        raise ValueError("Predicoes da amostra misturam versoes da heuristica.")
    precision, recall, f1, support = precision_recall_fscore_support(
        actual, estimated, labels=["sim"], average=None, zero_division=0,
    )
    matrix = confusion_matrix(actual, estimated, labels=["nao", "sim"])
    return {
        "n": len(keys), "precision": float(precision[0]), "recall": float(recall[0]),
        "f1": float(f1[0]), "positive_support": int(support[0]),
        "extra_predictions_ignored": len(predicted) - len(truth),
        "heuristic_version": versions.pop(),
        "tn": int(matrix[0, 0]), "fp": int(matrix[0, 1]),
        "fn": int(matrix[1, 0]), "tp": int(matrix[1, 1]),
    }


def run(gold_dir: Path, predictions_path: Path | None = None) -> dict:
    frames = {
        name: read_labels(gold_dir / f"rotulagem_{name}.xlsx")
        for name in ("pedro", "joao", "salomao")
    }
    resolutions = load_resolutions(gold_dir / "desempates.csv")
    report: dict = {"agreement": {}}
    all_pending = []
    outputs = {}
    for scope in DIMENSIONS:
        aligned = align(frames, scope)
        for dimension in DIMENSIONS[scope]:
            matrix = pd.DataFrame({name: frame[dimension] for name, frame in aligned.items()})
            report["agreement"][dimension] = agreement(matrix)
        outputs[scope], pending = consensus(aligned, scope, resolutions)
        all_pending.extend(pending)
    write_csv(gold_dir / "desempates_pendentes.csv",
              ("escopo", "repositorio", "tag", "dimensao", "votos"), all_pending)
    report["pending_ties"] = len(all_pending)
    (gold_dir / "validacao_relatorio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    if all_pending:
        raise ValueError(f"{len(all_pending)} desempate(s) pendente(s); veja desempates_pendentes.csv.")
    write_csv(gold_dir / "consenso_repositorios.csv",
              ("repositorio", "tag", "tipo_projeto", "tipo_projeto_criterio",
               "entregas_reais", "entregas_reais_criterio"), outputs["repositorios"])
    write_csv(gold_dir / "consenso_releases.csv",
              ("repositorio", "tag", "corretiva", "corretiva_criterio"), outputs["releases"])
    if predictions_path:
        with predictions_path.open(newline="", encoding="utf-8") as file:
            report["heuristic"] = evaluate(outputs["releases"], list(csv.DictReader(file)))
        (gold_dir / "validacao_relatorio.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calcula kappa, consenso e F1 da amostra-ouro.")
    parser.add_argument("--amostra", type=Path, default=Path(__file__).resolve().parent / "amostra_ouro")
    parser.add_argument("--predicoes", type=Path)
    args = parser.parse_args(argv)
    try:
        report = run(args.amostra, args.predicoes)
    except (FileNotFoundError, ValueError) as error:
        print(f"Validacao pendente: {error}")
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
