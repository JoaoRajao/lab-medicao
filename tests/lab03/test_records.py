from __future__ import annotations

from datetime import date

import pytest

from labs.lab03_dora.records import months, selected_repositories


def test_months_cover_the_window_with_partial_edges():
    slices = list(months(date(2025, 10, 15), date(2026, 2, 10)))
    assert slices[0] == (date(2025, 10, 15), date(2025, 10, 31))
    assert slices[2] == (date(2025, 12, 1), date(2025, 12, 31))
    assert slices[-1] == (date(2026, 2, 1), date(2026, 2, 10))
    assert len(slices) == 5


def test_selected_repositories_rejects_missing_or_incomplete_samples(tmp_path):
    with pytest.raises(FileNotFoundError, match="selecao"):
        selected_repositories(tmp_path)
    path = tmp_path / "repositories.csv"
    path.write_text("repository,stars\na/b,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="default_branch"):
        selected_repositories(tmp_path)
    path.write_text("repository,default_branch\na/b,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="incompleta"):
        selected_repositories(tmp_path)
