"""Casos de calculo e integracao das analises reexecutaveis da Sprint 3."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from labs.lab03_dora.analises_s03 import (
    DEFAULT_CONSENSUS, DEFAULT_DATASET, DEFAULT_RELEASES, _quartiles, _summary,
    descriptive, load_inputs, rework, run, sensitivity, subgroups,
)
from labs.lab03_dora.metricas.dora import classify


def test_quartis_ignoram_ausentes_e_usam_interpolacao_linear():
    assert _summary(pd.Series([1, 2, 3, 4, np.nan])) == {
        "n": 4, "mediana": 2.5, "q1": 1.75, "q3": 3.25, "iqr": 1.5,
    }
    assert _summary(pd.Series([np.nan]))["n"] == 0
    groups = _quartiles(pd.Series([1, 2, 3, 4, np.nan]))
    assert groups.iloc[:4].tolist() == ["Q1", "Q2", "Q3", "Q4"]
    assert pd.isna(groups.iloc[4])


def test_censura_usa_releases_unicas_e_episodios_como_denominadores():
    data = pd.DataFrame({
        "deployment_frequency_per_week": [1, 2], "lead_time_a_hours": [10, 20],
        "lead_time_b_hours": [9, 19], "cfr_a": [0.1, 0.2], "cfr_b": [0.3, np.nan],
        "recovery_median_hours": [2, 3], "df_points": [3, 3],
        "lead_time_points": [4, 4], "cfr_points": [4, 3],
        "recovery_points": [3, 3], "dora_points": [3, 3],
        "cfr_b_releases_evaluated": [50, 50], "cfr_b_releases_censored": [50, 50],
        "recovery_episodes": [3, 1], "censored_episodes": [1, 1],
    })
    releases = pd.DataFrame({"censored": [True, False, False]})
    summaries, categories, censored = descriptive(data, releases)
    assert summaries.loc[summaries.rq == "RQ03b", "n"].item() == 1
    assert categories.loc[(categories.metrica == "geral_C1") &
                          (categories.categoria == "High"), "repositorios"].item() == 2
    assert censored.loc[censored.rq == "RQ03b", "proporcao"].item() == pytest.approx(1 / 3)
    assert censored.loc[censored.rq == "RQ04", "proporcao"].item() == pytest.approx(0.5)


def test_rework_conta_corretivas_sobre_todas_as_releases_unicas():
    releases = pd.DataFrame({"repository": ["a", "a", "b"], "corrective": ["sim", "nao", "nao"]})
    per_repo, summary = rework(releases, pd.Series(["a", "b"]))
    assert per_repo.set_index("repository").rework_rate.to_dict() == {"a": 0.5, "b": 0.0}
    assert summary.releases.item() == 3
    assert summary.corretivas.item() == 1
    with pytest.raises(ValueError, match="Faltam releases"):
        rework(releases, pd.Series(["a", "missing"]))


def _scenario_row(name: str, frequency: float, lead: float, failure: float,
                  recovery: float, alt_frequency: float, alt_lead: float, alt_failure: float) -> dict:
    c1 = classify(frequency, lead, failure, recovery)
    return {
        "repository": name, "deployment_frequency_per_week": frequency,
        "deployment_frequency_with_prereleases_per_week": alt_frequency,
        "deployment_frequency_tags_per_week": alt_frequency,
        "lead_time_a_hours": lead, "lead_time_b_hours": alt_lead,
        "cfr_a": failure, "cfr_b": alt_failure, "recovery_median_hours": recovery,
        "df_points": c1["frequency"], "lead_time_points": c1["lead_time"],
        "cfr_points": c1["failure_rate"], "recovery_points": c1["recovery"],
        "dora_points": c1["overall"], "dora_category": c1["category"],
        "dora_metrics_used": c1["metrics_used"],
    }


def test_sensibilidade_recalcula_c1_e_compara_pares():
    data = pd.DataFrame([
        _scenario_row("low", 0.1, 1000, 0.8, 200, 0.1, 1000, 0.8),
        _scenario_row("medium", 0.5, 200, 0.4, 48, 8, 4, 0.1),
        _scenario_row("high", 2, 48, 0.2, 4, 0.1, 1000, 0.8),
        _scenario_row("elite", 8, 4, 0.1, 0.5, 8, 4, 0.1),
    ])
    categories, pairs = sensitivity(data)
    assert len(categories) == 12
    c1_c2 = pairs.loc[(pairs.cenario_a == "C1") & (pairs.cenario_b == "C2")].iloc[0]
    assert c1_c2.n == 4
    assert c1_c2.mudaram == 2
    assert c1_c2.percentual_mudou == 50
    assert -1 <= c1_c2.kappa_ponderado_linear <= 1
    data.loc[0, "dora_category"] = "Elite"
    with pytest.raises(ValueError, match="C1 difere"):
        sensitivity(data)


def test_subgrupos_aplicam_holm_e_separam_amostra_de_tipo():
    dataset, consensus, _ = load_inputs(DEFAULT_DATASET, DEFAULT_CONSENSUS, DEFAULT_RELEASES)
    descriptions, tests, pairs = subgroups(dataset, consensus)
    assert len(tests) == 16
    assert set(tests.loc[tests.fator == "tipo_projeto", "n"]) == {57, 60}
    assert (tests.p_holm >= tests.p_valor).all()
    assert (pairs.p_holm >= pairs.p_valor).all()
    assert (descriptions.n > 0).all()


def test_comando_gera_saidas_reexecutaveis_e_preserva_entrada(tmp_path):
    original = DEFAULT_DATASET.read_bytes()
    output = tmp_path / "csv"
    figures = tmp_path / "figures"
    paths = run(output_dir=output, figures_dir=figures)
    assert len(paths) == 13
    assert len(pd.read_csv(paths["classificacoes_c1_c2_c3"])) == 900
    assert len(pd.read_csv(paths["rework_por_repositorio"])) == 300
    assert (figures / "rq05_frequencia_cfr_a.png").is_file()
    assert (figures / "rq05_frequencia_cfr_b.png").is_file()
    assert DEFAULT_DATASET.read_bytes() == original
