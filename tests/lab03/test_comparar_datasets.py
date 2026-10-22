from __future__ import annotations

import math

import pandas as pd
import pytest

from labs.lab03_dora import comparar_datasets as cmp

ORIGINAL = pd.DataFrame({
    "repository": ["a/a", "b/b", "c/c", "d/d"],
    "cfr_a": [0.10, 0.20, 0.0, 0.5],
    "lead_time_a_hours": [100.0, 50.0, None, 10.0],
    "dora_category": ["High", "Medium", "Elite", "Low"],
})
REPLICATED = pd.DataFrame({
    "repository": ["a/a", "b/b", "c/c", "x/x"],
    "cfr_a": [0.105, 0.30, 0.0, 0.1],
    "lead_time_a_hours": [100.0, 60.0, 5.0, 1.0],
    "dora_category": ["High", "High", "Elite", "Low"],
})


def test_relative_difference_handles_zero_baselines():
    result = cmp.relative_difference(pd.Series([10.0, 0.0, 0.0]), pd.Series([11.0, 0.0, 2.0]))
    assert result.iloc[0] == pytest.approx(0.1)
    assert result.iloc[1] == 0.0
    assert math.isinf(result.iloc[2])


def test_compare_summarizes_metrics_and_dora_agreement():
    summary_rows, detail, summary = cmp.compare(ORIGINAL, REPLICATED, [("cfr_a", "cfr_a"), ("lead_time_a_hours", "lead_time_a_hours")])
    by_metric = summary_rows.set_index("metrica")
    assert summary["em_comum"] == 3 and summary["so_no_original"] == ["d/d"] and summary["so_no_replicado"] == ["x/x"]
    assert by_metric.loc["cfr_a", "pares"] == 3
    assert by_metric.loc["cfr_a", "mediana_dif_relativa"] == pytest.approx(0.05)
    assert by_metric.loc["cfr_a", "dentro_de_10pct"] == pytest.approx(2 / 3, abs=1e-4)
    assert by_metric.loc["lead_time_a_hours", "so_no_replicado"] == 1
    assert summary["mesma_classe_dora_pct"] == pytest.approx(66.67)
    assert list(detail["mesma_classe_dora"]) == [True, False, True]


def test_column_names_can_differ_between_groups(tmp_path):
    other = REPLICATED.rename(columns={"repository": "repo", "cfr_a": "taxa_falha_ci", "dora_category": "classe"})
    original, replicated = tmp_path / "o.csv", tmp_path / "r.csv"
    ORIGINAL.to_csv(original, index=False)
    other.to_csv(replicated, index=False)
    code = cmp.main(["--original", str(original), "--replicado", str(replicated), "--metricas", "cfr_a=taxa_falha_ci",
                     "--chave", "repository=repo", "--classe", "dora_category=classe", "--saida", str(tmp_path / "out")])
    assert code == 0
    assert (tmp_path / "out" / "comparacao_metricas.csv").is_file()
    assert cmp.main(["--original", str(original), "--replicado", str(replicated), "--metricas", "nao_existe"]) == 1
