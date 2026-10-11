"""Consolida as metricas por repositorio em `dataset.csv`, com a classificacao DORA de referencia (issue #66).

Le apenas os CSVs gerados pelas etapas anteriores: roda de novo sem token e sem chamar a API.

    python -m labs.lab03_dora.consolidacao --config labs/lab03_dora/config.yaml
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Sequence

from labs.lab03_dora.config import ConfigError, load_config
from labs.lab03_dora.metricas.dora import classify, deployment_frequency
from labs.lab03_dora.records import write_csv

DATASET_FIELDS = (
    "repository", "stars", "language", "contributors", "created_at", "age_days", "default_branch",
    "releases_in_window", "pre_releases_in_window", "tags_in_window",
    "deployment_frequency_per_week", "deployment_frequency_with_prereleases_per_week",
    "deployment_frequency_tags_per_week",
    "releases_compared", "compare_404_count", "releases_without_commits", "releases_diverged",
    "lead_time_a_hours", "lead_time_b_hours",
    "workflow_runs_valid", "successful_runs", "failed_runs", "ignored_runs", "cfr_a",
    "cfr_b", "cfr_b_releases_evaluated", "cfr_b_releases_censored",
    "recovery_median_hours", "recovery_episodes", "censored_episodes", "censored_episode_ratio",
    "df_points", "lead_time_points", "cfr_points", "recovery_points",
    "dora_points", "dora_category", "dora_metrics_used",
)
# Contrato da etapa de CFR (b) (issue #72): uma linha por repositorio.
CFR_B_FILE = "cfr_b_metrics.csv"
CFR_B_FIELDS = ("repository", "cfr_b", "releases_evaluated", "releases_censored")


def read_rows(path: Path, key: str = "repository") -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return {row[key]: row for row in csv.DictReader(file)}


def _number(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def _rounded(value: float | None, digits: int = 6) -> float | str:
    return "" if value is None else round(value, digits)


def consolidate(
    repositories: dict[str, dict[str, str]],
    lead_times: dict[str, dict[str, str]],
    workflows: dict[str, dict[str, str]],
    cfr_b: dict[str, dict[str, str]],
    window_weeks: float,
) -> list[dict]:
    missing = [repo for repo in repositories if repo not in lead_times or repo not in workflows]
    if missing:
        raise ValueError(f"Metricas ausentes para {len(missing)} repositorio(s), ex.: {missing[:3]}. "
                         "Rode as etapas releases e workflow_runs para a amostra inteira.")
    rows = []
    for repo, meta in repositories.items():
        lead, runs, failure = lead_times[repo], workflows[repo], cfr_b.get(repo, {})
        releases = int(lead["published_releases"])
        pre_releases = int(lead["pre_releases"])
        tags = int(lead["tags_in_window"])
        frequency = deployment_frequency(releases, window_weeks)
        lead_a, cfr_a = _number(lead["lead_time_a_hours"]), _number(runs["cfr_a"])
        recovery = _number(runs["recovery_median_hours"])
        # C1, a combinacao de referencia da RQ 07: release, lead time (a), CFR (a).
        reference = classify(frequency, lead_a, cfr_a, recovery)
        rows.append({
            "repository": repo, "stars": meta["stars"], "language": meta["language"],
            "contributors": meta["contributors"], "created_at": meta["created_at"], "age_days": meta["age_days"],
            "default_branch": meta["default_branch"],
            "releases_in_window": releases, "pre_releases_in_window": pre_releases, "tags_in_window": tags,
            "deployment_frequency_per_week": _rounded(frequency),
            "deployment_frequency_with_prereleases_per_week": _rounded(
                deployment_frequency(releases + pre_releases, window_weeks)),
            "deployment_frequency_tags_per_week": _rounded(deployment_frequency(tags, window_weeks)),
            "releases_compared": lead["releases_compared"], "compare_404_count": lead["compare_404_count"],
            "releases_without_commits": lead["releases_without_commits"],
            "releases_diverged": lead.get("releases_diverged", ""),
            "lead_time_a_hours": lead["lead_time_a_hours"], "lead_time_b_hours": lead["lead_time_b_hours"],
            "workflow_runs_valid": int(runs["successful_runs"]) + int(runs["failed_runs"]),
            "successful_runs": runs["successful_runs"], "failed_runs": runs["failed_runs"],
            "ignored_runs": runs["ignored_runs"], "cfr_a": runs["cfr_a"],
            "cfr_b": failure.get("cfr_b", ""), "cfr_b_releases_evaluated": failure.get("releases_evaluated", ""),
            "cfr_b_releases_censored": failure.get("releases_censored", ""),
            "recovery_median_hours": runs["recovery_median_hours"], "recovery_episodes": runs["recovery_episodes"],
            "censored_episodes": runs["censored_episodes"], "censored_episode_ratio": runs["censored_episode_ratio"],
            "df_points": reference["frequency"], "lead_time_points": _blank(reference["lead_time"]),
            "cfr_points": _blank(reference["failure_rate"]), "recovery_points": _blank(reference["recovery"]),
            "dora_points": _blank(reference["overall"]), "dora_category": reference["category"],
            "dora_metrics_used": reference["metrics_used"],
        })
    return rows


def _blank(value):
    return "" if value is None else value


def build_dataset(output_dir: Path, window_weeks: float) -> Path:
    cfr_b_path = output_dir / CFR_B_FILE
    rows = consolidate(
        read_rows(output_dir / "repositories.csv"),
        read_rows(output_dir / "lead_time_metrics.csv"),
        read_rows(output_dir / "workflow_metrics.csv"),
        read_rows(cfr_b_path) if cfr_b_path.is_file() else {},
        window_weeks,
    )
    path = output_dir / "dataset.csv"
    write_csv(path, DATASET_FIELDS, rows)
    return path


def run(ctx) -> None:
    build_dataset(ctx.config.output_dir, ctx.config.window.weeks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera dataset.csv a partir dos CSVs da coleta (sem API).")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parent / "config.yaml")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        path = build_dataset(config.output_dir, config.window.weeks)
    except (ConfigError, FileNotFoundError, ValueError) as error:
        print(f"Nao foi possivel gerar o dataset: {error}")
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
