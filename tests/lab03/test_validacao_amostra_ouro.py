from __future__ import annotations

import pandas as pd
import pytest

from labs.lab03_dora.validacao_amostra_ouro import agreement, align, consensus, evaluate


def frames():
    data = {}
    for name, types, corrective in (
        ("pedro", ["biblioteca/framework", "ferramenta CLI"], ["sim", "nao"]),
        ("joao", ["biblioteca/framework", "aplicacao/servico"], ["sim", "nao"]),
        ("salomao", ["biblioteca/framework", "outro"], ["nao", "nao"]),
    ):
        repos = pd.DataFrame({"repositorio": ["a/x", "b/y"], "tipo_projeto": types,
                              "entregas_reais": ["sim", "sim"]})
        releases = pd.DataFrame({"repositorio": ["a/x", "b/y"], "tag": ["v1", "v2"],
                                 "corretiva": corrective})
        data[name] = repos, releases
    return data


def test_align_by_keys_and_reject_duplicate_or_missing():
    data = frames()
    data["joao"] = data["joao"][0].iloc[::-1].reset_index(drop=True), data["joao"][1]
    assert list(align(data, "repositorios")["joao"].index) == ["a/x", "b/y"]
    duplicate = frames()
    duplicate["joao"] = pd.concat([duplicate["joao"][0], duplicate["joao"][0].iloc[:1]]), duplicate["joao"][1]
    with pytest.raises(ValueError, match="duplicadas"):
        align(duplicate, "repositorios")
    missing = frames()
    missing["joao"] = missing["joao"][0].iloc[:1], missing["joao"][1]
    with pytest.raises(ValueError, match="diferentes"):
        align(missing, "repositorios")


def test_consensus_requires_documented_tie_break():
    aligned = align(frames(), "repositorios")
    rows, pending = consensus(aligned, "repositorios", {})
    assert rows[0]["tipo_projeto"] == "biblioteca/framework"
    assert rows[1]["tipo_projeto"] == ""
    assert pending[0]["dimensao"] == "tipo_projeto"
    resolved, pending = consensus(aligned, "repositorios",
                                  {("repositorios", "b/y", "", "tipo_projeto"): ("outro", "reuniao")})
    assert not pending and resolved[1]["tipo_projeto"] == "outro"


def test_kappa_and_f1():
    labels = pd.DataFrame({"pedro": ["sim", "nao", "sim"], "joao": ["sim", "nao", "sim"],
                           "salomao": ["sim", "sim", "nao"]})
    result = agreement(labels)
    assert result["n"] == 3 and -1 <= result["kappa"] <= 1
    consensus_rows = [{"repositorio": "a/x", "tag": "v1", "corretiva": "sim"},
                      {"repositorio": "b/y", "tag": "v2", "corretiva": "nao"}]
    predictions = [{"repository": "a/x", "tag_name": "v1", "corrective": "sim"},
                   {"repository": "b/y", "tag_name": "v2", "corrective": "sim"}]
    score = evaluate(consensus_rows, predictions)
    assert (score["precision"], score["recall"], score["f1"]) == (0.5, 1.0, pytest.approx(2 / 3))
    assert evaluate(consensus_rows, predictions + [
        {"repository": "extra/repo", "tag_name": "v9", "corrective": "nao"}
    ])["extra_predictions_ignored"] == 1
    with pytest.raises(ValueError, match="chaves"):
        evaluate(consensus_rows, predictions[:1])
