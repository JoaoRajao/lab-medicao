from __future__ import annotations

import threading
import time
from datetime import date

import pytest

from labs.lab03_dora.records import (
    RUN_KEYS, map_repositories, months, selected_repositories, slim_releases, slim_runs,
)


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


def test_slim_pages_keep_only_the_fields_the_stages_read():
    run = {key: f"v-{key}" for key in RUN_KEYS} | {"repository": {"big": "x"}, "head_commit": {"message": "m"}}
    assert slim_runs({"total_count": 1, "workflow_runs": [run]}) == {
        "total_count": 1, "workflow_runs": [{key: f"v-{key}" for key in RUN_KEYS}]}
    release = {"tag_name": "v1", "draft": False, "prerelease": False, "published_at": "2026-01-01T00:00:00Z",
               "body": "x" * 10_000, "assets": [{}]}
    assert slim_releases([release]) == [{"tag_name": "v1", "name": None, "draft": False, "prerelease": False,
                                         "created_at": None, "published_at": "2026-01-01T00:00:00Z"}]


def test_map_repositories_runs_in_parallel_and_keeps_input_order():
    active, peak, lock = [0], [0], threading.Lock()

    def slow(item):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.05 if item % 2 else 0.01)
        with lock:
            active[0] -= 1
        return item * 10

    assert map_repositories(slow, list(range(8)), workers=4) == [i * 10 for i in range(8)]
    assert peak[0] > 1
    assert map_repositories(lambda item: item + 1, [1, 2], workers=1) == [2, 3]


def test_errors_in_one_repository_stop_the_stage():
    def broken(item):
        if item == 3:
            raise RuntimeError("falhou")
        return item

    with pytest.raises(RuntimeError, match="falhou"):
        map_repositories(broken, list(range(6)), workers=3)
