from __future__ import annotations

import csv
from datetime import date

import pytest

from labs.lab03_dora import workflow_runs
from labs.lab03_dora.config import Config, Inclusion, Window
from labs.lab03_dora.metricas.workflows import cfr_a, classify, recovery_episodes, recovery_summary
from labs.lab03_dora.pipeline import Context
from shared.github_rest import Response, build_url


def run(run_id, workflow, started, conclusion, updated=None, event="push", branch="main"):
    return {"id": run_id, "workflow_id": workflow, "event": event, "head_branch": branch,
            "conclusion": conclusion, "created_at": started, "run_started_at": started,
            "updated_at": updated or started}


def test_rq04_recovery_is_per_workflow_and_reports_censoring():
    runs = [
        run(1, 10, "2026-03-01T09:00:00Z", "success"),
        run(2, 10, "2026-03-01T10:00:00Z", "failure"),
        run(3, 10, "2026-03-01T10:30:00Z", "timed_out"),
        run(4, 10, "2026-03-01T11:15:00Z", "success", "2026-03-01T11:20:00Z"),
        run(5, 10, "2026-03-01T12:00:00Z", "startup_failure"),
        run(6, 10, "2026-03-01T12:30:00Z", "cancelled"),
        run(7, 20, "2026-03-01T09:30:00Z", "failure"),  # sem sucesso anterior: nao inicia episodio
        run(8, 20, "2026-03-01T10:45:00Z", "success"),
    ]
    assert classify("cancelled") == "ignored"
    assert cfr_a(runs) == (4 / 7, 3, 4, 1)
    episodes = recovery_episodes(list(reversed(runs)))
    assert len(episodes) == 2
    assert episodes[0]["hours"] == pytest.approx(1 + 20 / 60)
    assert episodes[1]["censored"] is True
    assert recovery_summary(episodes) == pytest.approx((1 + 20 / 60, 1, 1, 0.5))


def test_no_valid_runs_has_undefined_cfr_and_recovery():
    runs = [run(1, 10, "2026-03-01T09:00:00Z", "skipped")]
    assert cfr_a(runs) == (None, 0, 0, 1)
    assert recovery_summary(recovery_episodes(runs)) == (None, 0, 0, None)


class Client:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, path, params):
        url = build_url(path, params)
        self.calls.append(url)
        return self.responses[url]


def response(total, runs, next_page=None):
    headers = {"link": f'<https://api.github.com/?page={next_page}>; rel="next"'} if next_page else {}
    return Response(200, {"total_count": total, "workflow_runs": runs}, headers)


def key(first, last, page=None):
    params = {"branch": "main", "event": "push", "created": f"{first}..{last}", "per_page": 100}
    if page:
        params["page"] = page
    return build_url("/repos/g/r/actions/runs", params)


def test_collection_splits_capped_interval_and_paginates(monkeypatch):
    monkeypatch.setattr(workflow_runs, "months", lambda start, end: iter([(date(2026, 3, 1), date(2026, 3, 2))]))
    first = run(1, 10, "2026-03-01T09:00:00Z", "success")
    second = run(2, 10, "2026-03-02T09:00:00Z", "failure")
    client = Client({
        key("2026-03-01", "2026-03-02"): response(1000, []),
        key("2026-03-01", "2026-03-01"): response(2, [first], next_page=2),
        key("2026-03-01", "2026-03-01", 2): response(2, [first]),  # deduplicado por ID
        key("2026-03-02", "2026-03-02"): response(1, [second]),
    })
    runs, audit = workflow_runs.collect_repository(client, "g/r", "main", date(2026, 3, 1), date(2026, 3, 2))
    assert [item["id"] for item in runs] == [1, 2]
    assert audit == [{"repository": "g/r", "month": "2026-03", "api_total_count": 1000,
                      "hit_cap": True, "runs_collected": 2}]
    assert len(client.calls) == 4


def test_single_day_at_cap_fails_closed():
    client = Client({key("2026-03-01", "2026-03-01"): response(1000, [])})
    with pytest.raises(RuntimeError, match="nao e possivel garantir"):
        workflow_runs.collect_interval(client, "g/r", "main", date(2026, 3, 1), date(2026, 3, 1))


def test_stage_reads_selection_and_writes_metric_csvs(monkeypatch, tmp_path):
    (tmp_path / "repositories.csv").write_text("repository,default_branch\ng/r,main\n", encoding="utf-8")
    monkeypatch.setattr(workflow_runs, "months", lambda start, end: iter([(date(2026, 3, 1), date(2026, 3, 1))]))
    rows = [run(1, 10, "2026-03-01T09:00:00Z", "success"),
            run(2, 10, "2026-03-01T10:00:00Z", "failure"),
            run(3, 10, "2026-03-01T11:15:00Z", "success", "2026-03-01T11:20:00Z")]
    client = Client({key("2026-03-01", "2026-03-01"): response(3, rows)})
    cfg = Config(Window(date(2025, 10, 1), date(2026, 9, 30)), Inclusion(5, 50), 1,
                 tmp_path, tmp_path / "cache", 5, 30)
    workflow_runs.run(Context(cfg, client))
    with (tmp_path / "workflow_metrics.csv").open(newline="") as file:
        metrics = list(csv.DictReader(file))
    assert metrics[0]["cfr_a"] == str(1 / 3)
    assert metrics[0]["recovery_median_hours"] == str(1 + 20 / 60)
    assert metrics[0]["months_with_runs"] == "1"
    assert metrics[0]["first_observed_run_at"] == "2026-03-01T09:00:00Z"
    assert (tmp_path / "workflow_runs.csv").is_file()
    assert (tmp_path / "recovery_episodes.csv").is_file()
