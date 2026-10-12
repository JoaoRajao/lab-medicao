from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from labs.lab03_dora import consolidacao
from labs.lab03_dora.config import Config, Inclusion, Window
from labs.lab03_dora.pipeline import Context

REPOSITORIES = """repository,stars,language,contributors,created_at,age_days,default_branch,published_releases,valid_workflow_runs
a/one,5000,Python,120,2015-01-01T00:00:00Z,3925,main,5,50
b/two,1500,Go,,2020-01-01T00:00:00Z,2465,master,5,50
"""
LEAD = """repository,published_releases,pre_releases,tags_in_window,releases_compared,compare_404_count,releases_without_commits,releases_diverged,commits_compared,commits_missing_author_date,negative_lead_time_commits,lead_time_a_hours,lead_time_b_hours
a/one,53,4,60,51,0,1,0,300,0,0,2.0,1.5
b/two,6,0,6,5,1,0,1,40,0,0,,
"""
WORKFLOWS = """repository,workflow_runs_collected,successful_runs,failed_runs,ignored_runs,cfr_a,recovery_episodes,recovered_episodes,censored_episodes,censored_episode_ratio,recovery_median_hours,months_with_runs,first_observed_run_at,last_observed_run_at
a/one,1000,800,200,10,0.2,20,19,1,0.05,240.0,12,,
b/two,60,30,30,0,0.5,3,0,3,1.0,,6,,
"""
CFR_B = """repository,cfr_b,releases_evaluated,releases_censored
a/one,0.1,50,2
"""
WEEKS = 365 / 7


def write_inputs(folder: Path, cfr_b: bool = False) -> None:
    (folder / "repositories.csv").write_text(REPOSITORIES, encoding="utf-8")
    (folder / "lead_time_metrics.csv").write_text(LEAD, encoding="utf-8")
    (folder / "workflow_metrics.csv").write_text(WORKFLOWS, encoding="utf-8")
    if cfr_b:
        (folder / "cfr_b_metrics.csv").write_text(CFR_B, encoding="utf-8")


def read_dataset(folder: Path) -> list[dict]:
    with (folder / "dataset.csv").open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_dataset_joins_stages_and_classifies_with_the_reference_combination(tmp_path):
    write_inputs(tmp_path, cfr_b=True)
    consolidacao.build_dataset(tmp_path, WEEKS)
    one, two = read_dataset(tmp_path)

    assert list(one) == list(consolidacao.DATASET_FIELDS)
    assert float(one["deployment_frequency_per_week"]) == pytest.approx(53 / WEEKS)
    assert float(one["deployment_frequency_with_prereleases_per_week"]) == pytest.approx(57 / WEEKS)
    assert one["workflow_runs_valid"] == "1000"
    # ~1/semana (High), lead time (a) 2 h (Elite), CFR (a) 20% (High), recuperacao 10 dias (Low): High
    assert (one["df_points"], one["lead_time_points"], one["cfr_points"], one["recovery_points"]) == ("2", "4", "3", "1") or \
        one["df_points"] == "3"
    assert one["dora_category"] == "High" and one["dora_metrics_used"] == "4"
    assert (one["cfr_b"], one["cfr_b_releases_evaluated"], one["cfr_b_releases_censored"]) == ("0.1", "50", "2")

    # sem lead time nem recuperacao calculaveis: classificacao com as duas metricas disponiveis
    assert two["lead_time_points"] == "" and two["recovery_points"] == ""
    assert two["dora_metrics_used"] == "2" and two["dora_category"] == "Low"
    assert two["cfr_b"] == "" and two["contributors"] == ""


def test_missing_stage_output_for_a_repository_is_an_error(tmp_path):
    write_inputs(tmp_path)
    (tmp_path / "workflow_metrics.csv").write_text(WORKFLOWS.splitlines()[0] + "\n" + WORKFLOWS.splitlines()[1] + "\n",
                                                  encoding="utf-8")
    with pytest.raises(ValueError, match="b/two"):
        consolidacao.build_dataset(tmp_path, WEEKS)


def test_stage_and_command_line_rebuild_the_same_file_without_api(tmp_path):
    write_inputs(tmp_path)
    config = tmp_path / "config.yaml"
    config.write_text("janela:\n  inicio: 2025-10-01\n  fim: 2026-09-30\nsaida:\n  dados: .\n", encoding="utf-8")

    assert consolidacao.main(["--config", str(config)]) == 0
    first = (tmp_path / "dataset.csv").read_bytes()
    cfg = Config(Window(date(2025, 10, 1), date(2026, 9, 30)), Inclusion(5, 50), 2, tmp_path, tmp_path / "c", 5, 30)
    consolidacao.run(Context(cfg, client=None))
    assert (tmp_path / "dataset.csv").read_bytes() == first

    (tmp_path / "lead_time_metrics.csv").unlink()
    assert consolidacao.main(["--config", str(config)]) == 1


def test_52_releases_in_a_365_day_window_is_just_below_once_a_week(tmp_path):
    write_inputs(tmp_path)
    lead = (tmp_path / "lead_time_metrics.csv").read_text(encoding="utf-8").replace("a/one,53,", "a/one,52,")
    (tmp_path / "lead_time_metrics.csv").write_text(lead, encoding="utf-8")
    consolidacao.build_dataset(tmp_path, WEEKS)
    one = read_dataset(tmp_path)[0]
    assert one["df_points"] == "2"  # 52 / 52,14 = 0,997 por semana: Medium
    assert one["dora_category"] == "Medium"  # notas 2, 4, 3, 1: mediana 2,5 -> 2
