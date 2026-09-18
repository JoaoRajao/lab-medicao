from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from labs.lab02_ia_vs_manual.scripts import consolidate_trial_records as consolidation
from labs.lab02_ia_vs_manual.scripts import run_trial_timer as timer


def _frozen_datetime(*instants: datetime) -> type[datetime]:
    remaining = iter(instants)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001 - matches datetime.now signature
            return next(remaining)

    return FrozenDatetime


def test_timer_start_stop_records_real_elapsed_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timer, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(
        timer,
        "datetime",
        _frozen_datetime(
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(timer, "run_pytest", lambda _kata: (True, 2, 0, "2 passed"))
    output_path = tmp_path / "trials.jsonl"

    timer.cmd_start(
        SimpleNamespace(
            participant="P9", kata="warehouse_batches", treatment="manual",
            timebox_seconds=2100, assistant=None, force=False,
        )
    )
    timer.cmd_stop(
        SimpleNamespace(
            participant="P9", kata="warehouse_batches", treatment="manual",
            solution_path=None, output=output_path,
        )
    )

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["time_to_green_seconds"] == 10
    assert records[0]["censored"] is False
    assert (records[0]["tests_passed"], records[0]["tests_failed"]) == (2, 0)


def test_timer_stop_censors_when_timebox_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timer, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(
        timer,
        "datetime",
        _frozen_datetime(
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 0, 0, 20, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(timer, "run_pytest", lambda _kata: (False, 1, 1, "1 failed, 1 passed"))
    output_path = tmp_path / "trials.jsonl"

    timer.cmd_start(
        SimpleNamespace(
            participant="P9", kata="warehouse_batches", treatment="manual",
            timebox_seconds=10, assistant=None, force=False,
        )
    )
    timer.cmd_stop(
        SimpleNamespace(
            participant="P9", kata="warehouse_batches", treatment="manual",
            solution_path=None, output=output_path,
        )
    )

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["time_to_green_seconds"] == 10
    assert records[0]["censored"] is True
    assert (records[0]["tests_passed"], records[0]["tests_failed"]) == (1, 1)


def make_records() -> tuple[dict, dict]:
    timing = {}
    metrics = {}
    for index, (kata, treatment) in enumerate(consolidation.P2_ORDER):
        trial_id = f"P2-{kata}-{treatment}"
        common = {
            "trial_id": trial_id,
            "participant": "P2",
            "kata": kata,
            "treatment": treatment,
            "solution_path": f"labs/lab02_ia_vs_manual/katas/{kata}/solution.py",
        }
        timing[trial_id] = {**common, "started_at": f"2026-09-16T10:{index:02d}:00+00:00"}
        metrics[trial_id] = {**common, **{field: 1 for field in consolidation.STATIC_FIELDS}}
    return timing, metrics


def test_consolidation_requires_six_matched_trials_in_p2_order() -> None:
    timing, metrics = make_records()
    records = consolidation.consolidate(timing, metrics)
    assert len(records) == 6
    assert [record["treatment"] for record in records] == [
        treatment for _, treatment in consolidation.P2_ORDER
    ]
    assert all("loc" in record for record in records)


def test_consolidation_rejects_missing_metrics() -> None:
    timing, metrics = make_records()
    metrics.pop(next(iter(metrics)))
    with pytest.raises(ValueError, match="seis IDs P2"):
        consolidation.consolidate(timing, metrics)


def test_consolidation_rejects_out_of_order_trials() -> None:
    timing, metrics = make_records()
    first_id = next(iter(timing))
    timing[first_id]["started_at"] = "2026-09-16T11:00:00+00:00"
    with pytest.raises(ValueError, match="Ordem"):
        consolidation.consolidate(timing, metrics)


def test_consolidation_rejects_wrong_treatment() -> None:
    timing, metrics = make_records()
    first_id = next(iter(timing))
    timing[first_id]["treatment"] = "manual"
    with pytest.raises(ValueError, match="Metadados"):
        consolidation.consolidate(timing, metrics)


def test_consolidation_cli_writes_complete_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    timing, metrics = make_records()
    timing_path = tmp_path / "timing.jsonl"
    metrics_path = tmp_path / "metrics.jsonl"
    output_path = tmp_path / "trials_joao.jsonl"
    timing_path.write_text(
        "".join(json.dumps(record) + "\n" for record in timing.values()), encoding="utf-8"
    )
    metrics_path.write_text(
        "".join(json.dumps(record) + "\n" for record in metrics.values()), encoding="utf-8"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "consolidate_trial_records",
            "--timing",
            str(timing_path),
            "--metrics",
            str(metrics_path),
            "--output",
            str(output_path),
        ],
    )

    consolidation.main()

    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 6
    assert not (tmp_path / ".trials_joao.jsonl.tmp").exists()
