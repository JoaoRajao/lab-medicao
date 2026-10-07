from __future__ import annotations

import csv
from datetime import date

import pytest

from labs.lab03_dora import selecao
from labs.lab03_dora.config import Config, Inclusion, Window
from labs.lab03_dora.pipeline import Context
from shared.github_rest import Response, build_url


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, path, params=None):
        url = build_url(path, params)
        self.calls.append(url)
        return self.responses[url]

    def paginate(self, path):
        return self.responses[path]


def response(data, next_page=None, last_page=None):
    links = []
    if next_page:
        links.append(f'<https://api.github.com/?page={next_page}>; rel="next"')
    if last_page:
        links.append(f'<https://api.github.com/?page={last_page}>; rel="last"')
    return Response(200, data, {"link": ", ".join(links)})


def config(tmp_path, target=1):
    return Config(Window(date(2025, 10, 1), date(2026, 9, 30)), Inclusion(5, 50), target,
                  tmp_path, tmp_path / "cache", 5, 30)


def candidate(name, stars=2000):
    return {"full_name": name, "stargazers_count": stars, "default_branch": "main",
            "language": "Python", "created_at": "2020-01-01T00:00:00Z"}


def test_search_splits_over_1000_and_paginates_without_losing_items():
    def key(low, high, page=None):
        params = {"q": f"stars:{low}..{high}", "sort": "stars", "order": "desc", "per_page": 100}
        if page:
            params["page"] = page
        return build_url("/search/repositories", params)

    client = FakeClient({
        key(1001, 1004): response({"total_count": 1001, "items": []}),
        key(1003, 1004): response({"total_count": 1, "items": [candidate("a/repo")]}),
        key(1001, 1002): response({"total_count": 2, "items": [candidate("b/repo")]}, next_page=2),
        key(1001, 1002, 2): response({"total_count": 2, "items": [candidate("c/repo")]}),
    })
    assert [r["full_name"] for r in selecao._search_range(client, 1001, 1004)] == ["a/repo", "b/repo", "c/repo"]
    assert len(client.calls) == 4


def test_inspect_filters_actions_releases_and_valid_runs(monkeypatch, tmp_path):
    cfg = config(tmp_path)
    month = (date(2025, 10, 1), date(2025, 10, 31))
    monkeypatch.setattr(selecao, "_months", lambda start, end: iter([month]))
    run_path = "/repos/c/repo/actions/runs"
    run_params = {"branch": "main", "event": "push", "created": "2025-10-01..2025-10-31", "per_page": 100}
    valid = {"event": "push", "head_branch": "main", "conclusion": "success", "created_at": "2025-10-02T00:00:00Z"}
    invalid = {**valid, "conclusion": "cancelled"}
    responses = {
        build_url("/repos/a/repo/actions/workflows", {"per_page": 1}): response({"total_count": 0}),
        build_url("/repos/b/repo/actions/workflows", {"per_page": 1}): response({"total_count": 1}),
        build_url("/repos/c/repo/actions/workflows", {"per_page": 1}): response({"total_count": 1}),
        "/repos/b/repo/releases": [{"draft": False, "published_at": "2026-01-01T00:00:00Z"}],
        "/repos/c/repo/releases": [{"draft": False, "published_at": "2026-01-01T00:00:00Z"}] * 5
        + [{"draft": True, "published_at": "2026-01-01T00:00:00Z"},
           {"prerelease": True, "published_at": "2026-01-01T00:00:00Z"}],
        build_url(run_path, run_params): response({"total_count": 2, "workflow_runs": [valid, invalid]}, next_page=2),
        build_url(run_path, {**run_params, "page": 2}): response({"total_count": 2, "workflow_runs": [valid] * 49}),
        build_url("/repos/c/repo/contributors", {"per_page": 1, "anon": "true"}): response([{}], last_page=7),
    }
    client = FakeClient(responses)
    assert selecao.inspect(client, candidate("a/repo"), cfg)[0]["reason"] == "no_actions"
    assert selecao.inspect(client, candidate("b/repo"), cfg)[0]["reason"] == "insufficient_releases"
    decision, metadata = selecao.inspect(client, candidate("c/repo"), cfg)
    assert decision["decision"] == "included"
    assert metadata["valid_workflow_runs"] == 50
    assert metadata["published_releases"] == 5
    assert metadata["contributors"] == 7
    assert not any("/repos/a/repo/releases" in call for call in client.calls)


def test_run_writes_sample_decisions_and_funnel(monkeypatch, tmp_path):
    cfg = config(tmp_path)
    outcomes = iter([
        ({"repository": "a/repo", "decision": "excluded", "reason": "no_actions", "stars": 2000,
          "releases": "", "valid_workflow_runs": ""}, None),
        ({"repository": "b/repo", "decision": "included", "reason": "included", "stars": 2000,
          "releases": 5, "valid_workflow_runs": 50},
         {field: "x" for field in selecao.REPOSITORY_FIELDS}),
    ])
    monkeypatch.setattr(selecao, "candidates", lambda client: iter([candidate("a/repo"), candidate("b/repo")]))
    monkeypatch.setattr(selecao, "inspect", lambda client, item, config: next(outcomes))
    selecao.run(Context(cfg, object()))
    with (tmp_path / "selection_funnel.csv").open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0] == {"stage": "candidates_examined", "remaining": "2", "excluded": "0"}
    assert rows[-1]["remaining"] == "1"
    with (tmp_path / "repositories.csv").open(newline="") as file:
        assert len(list(csv.DictReader(file))) == 1


def test_month_at_cap_refuses_incomplete_count(monkeypatch, tmp_path):
    monkeypatch.setattr(selecao, "_months", lambda start, end: iter([(date(2025, 10, 1), date(2025, 10, 1))]))
    params = {"branch": "main", "event": "push", "created": "2025-10-01..2025-10-01", "per_page": 100}
    client = FakeClient({build_url("/repos/a/repo/actions/runs", params): response({"total_count": 1000, "workflow_runs": []})})
    with pytest.raises(RuntimeError, match="teto de 1.000"):
        selecao._valid_runs(client, "a/repo", "main", date(2025, 10, 1), date(2026, 9, 30))


def test_run_count_splits_a_month_at_the_api_cap(monkeypatch):
    monkeypatch.setattr(selecao, "_months", lambda start, end: iter([(date(2025, 10, 1), date(2025, 10, 2))]))
    def key(first, last):
        return build_url("/repos/a/repo/actions/runs", {
            "branch": "main", "event": "push", "created": f"{first}..{last}", "per_page": 100,
        })
    valid = lambda day: {"event": "push", "head_branch": "main", "conclusion": "success",
                         "created_at": f"2025-10-0{day}T00:00:00Z"}
    client = FakeClient({
        key("2025-10-01", "2025-10-02"): response({"total_count": 1000, "workflow_runs": []}),
        key("2025-10-01", "2025-10-01"): response({"total_count": 1, "workflow_runs": [valid(1)]}),
        key("2025-10-02", "2025-10-02"): response({"total_count": 1, "workflow_runs": [valid(2)]}),
    })
    assert selecao._valid_runs(client, "a/repo", "main", date(2025, 10, 1), date(2026, 9, 30)) == 2
