from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from labs.lab02_ia_vs_manual.scripts import consolidate_trial_records as consolidation
from labs.lab02_ia_vs_manual.scripts import run_trial_timer as timer


def test_timer_records_elapsed_time_until_green() -> None:
    now = [0.0]
    checks = iter([(False, 1, 1, "1 failed, 1 passed"), (True, 2, 0, "2 passed")])

    def run_check(_kata: str, _timeout: int) -> tuple[bool, int, int, str]:
        now[0] += 0.2
        return next(checks)

    def sleep(seconds: float) -> None:
        now[0] += seconds

    with patch.object(timer.time, "monotonic", lambda: now[0]), patch.object(
        timer.time, "sleep", sleep
    ), patch.object(timer, "run_pytest", run_check):
        result = timer.measure_trial("warehouse_batches", 35, 5)

    assert result["time_to_green_seconds"] == 6
    assert result["censored"] is False
    assert (result["tests_passed"], result["tests_failed"]) == (2, 0)


def test_timer_censors_incomplete_trial_at_timebox() -> None:
    now = [0.0]

    def run_check(_kata: str, _timeout: int) -> tuple[bool, int, int, str]:
        now[0] += 0.2
        return False, 1, 1, "1 failed, 1 passed"

    def sleep(seconds: float) -> None:
        now[0] += seconds

    with patch.object(timer.time, "monotonic", lambda: now[0]), patch.object(
        timer.time, "sleep", sleep
    ), patch.object(timer, "run_pytest", run_check):
        result = timer.measure_trial("warehouse_batches", 10, 5)

    assert result["time_to_green_seconds"] == 10
    assert result["censored"] is True
    assert (result["tests_passed"], result["tests_failed"]) == (1, 1)


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
