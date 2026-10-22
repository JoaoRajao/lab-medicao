from __future__ import annotations

import pandas as pd
import pytest

from labs.lab03_dora import avaliar_heuristicas as av
from labs.lab03_dora.metricas.cfr_b import VERSION

RELEASES = pd.DataFrame([
    # patch: corretiva pela v1 e pela v2
    {"repository": "o/r", "tag_name": "v1.0.1", "previous_tag": "v1.0.0", "commits_compared": 4, "fix_commits": 0},
    # minor com 2 de 4 commits fix: so as versoes com sinal de commits marcam
    {"repository": "o/r", "tag_name": "v1.1.0", "previous_tag": "v1.0.1", "commits_compared": 4, "fix_commits": 2},
    # minor com 1 de 10 commits fix: so "qualquer commit fix" marca
    {"repository": "o/r", "tag_name": "v1.2.0", "previous_tag": "v1.1.0", "commits_compared": 10, "fix_commits": 1},
    {"repository": "o/r", "tag_name": "v1.2.0", "previous_tag": "v1.1.0", "commits_compared": 10, "fix_commits": 1},
    # primeira release, sem commits comparados
    {"repository": "o/r", "tag_name": "v0.9.0", "previous_tag": None, "commits_compared": 0, "fix_commits": 0},
])
KEYS = pd.MultiIndex.from_tuples([("o/r", "v1.0.1"), ("o/r", "v1.1.0"), ("o/r", "v1.2.0"), ("o/r", "v0.9.0")],
                                 names=["repository", "tag_name"])


def test_versions_are_scored_on_the_same_releases_without_duplicates():
    truth = pd.Series([True, True, False, False], index=KEYS)
    result = av.evaluate(RELEASES, {"consenso": truth}).set_index("versao")

    assert result.loc["semver-patch-v1", "f1"] == pytest.approx(2 / 3, abs=1e-3)
    assert result.loc[VERSION, "f1"] == 1.0
    assert result.loc["patch-ou-qualquer-commit-fix", "positivos_previstos"] == 3
    assert result.loc["referencia-tudo-corretiva", "positivos_previstos"] == 4


def test_missing_gold_release_is_an_error():
    truth = pd.Series([True], index=pd.MultiIndex.from_tuples([("o/r", "v9.9.9")], names=["repository", "tag_name"]))
    with pytest.raises(ValueError, match="ausentes"):
        av.evaluate(RELEASES, {"consenso": truth})


def test_patch_increment_requires_same_major_and_minor():
    assert av.patch_increment("v2.3.1", "v2.3.0")
    assert not av.patch_increment("v2.4.0", "v2.3.1")
    assert not av.patch_increment("release-q3", "release-q2")
    assert not av.patch_increment("v1.0.0", "")
