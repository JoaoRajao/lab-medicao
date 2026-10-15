"""Gera CFR (b) a partir dos CSVs de releases já coletados, sem novas chamadas à API."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from labs.lab03_dora.config import load_config
from labs.lab03_dora.metricas.cfr_b import cfr_b_for_repository
from labs.lab03_dora.records import selected_repositories, write_csv

DETAIL_FIELDS = (
    "repository", "tag_name", "published_at", "corrective", "evidence",
    "heuristic_version", "censored", "failed", "following_corrective_tag",
)
METRIC_FIELDS = ("repository", "cfr_b", "releases_evaluated", "releases_censored")


def build(output_dir: Path, window_end) -> tuple[Path, Path]:
    by_repo: dict[str, list[dict]] = defaultdict(list)
    with (output_dir / "releases.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            by_repo[row["repository"]].append(row)
    details, metrics = [], []
    for repository, _ in selected_repositories(output_dir):
        if repository not in by_repo:
            raise ValueError(f"Sem releases para {repository}")
        own_details, own_metric = cfr_b_for_repository(by_repo[repository], window_end)
        details.extend(own_details)
        metrics.append(own_metric)
    detail_path = output_dir / "cfr_b_releases.csv"
    metric_path = output_dir / "cfr_b_metrics.csv"
    write_csv(detail_path, DETAIL_FIELDS, details)
    write_csv(metric_path, METRIC_FIELDS, metrics)
    return detail_path, metric_path


def run(ctx) -> None:
    build(ctx.config.output_dir, ctx.config.window.end)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calcula CFR (b) a partir de releases.csv.")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parent / "config.yaml")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        paths = build(config.output_dir, config.window.end)
    except (FileNotFoundError, ValueError) as error:
        print(f"Nao foi possivel calcular CFR (b): {error}")
        return 1
    for path in paths:
        print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
