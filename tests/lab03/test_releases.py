from __future__ import annotations

import csv
from datetime import date
from types import SimpleNamespace

from labs.lab03_dora import releases
from labs.lab03_dora.config import Config, Inclusion, Window
from labs.lab03_dora.metricas.lead_time import release_lead_times_hours, repository_lead_times_hours
from labs.lab03_dora.pipeline import Context
from shared.github_rest import GitHubNotFoundError

START, END = date(2025, 10, 1), date(2026, 9, 30)


def release(tag, published, prerelease=False):
    return {"tag_name": tag, "published_at": published, "draft": False, "prerelease": prerelease}


def commit(sha, author_at):
    return {"sha": sha, "commit": {"author": {"date": author_at}}}


class Client:
    def __init__(self, release_items, comparisons=None, tags=None):
        self.release_items = release_items
        self.comparisons = comparisons or {}
        self.tags = tags or []
        self.calls = []

    def paginate(self, path, params=None, item_key=None):
        self.calls.append((path, item_key))
        if path.endswith("/releases"):
            return iter(self.release_items)
        if path.endswith("/tags"):
            return iter(self.tags)
        value = self.comparisons[path]
        if isinstance(value, Exception):
            raise value
        return iter(value)

    def get(self, path):
        sha = path.rsplit("/", 1)[-1]
        return SimpleNamespace(data={"commit": {"author": {"date": "2026-03-02T00:00:00Z"}}})


def test_rq02_example_uses_oldest_commit_and_all_commit_values():
    author_dates = ["2026-03-02T00:00:00Z", "2026-03-10T00:00:00Z", "2026-03-14T00:00:00Z"]
    lead_a, leads_b = release_lead_times_hours("2026-03-15T00:00:00Z", author_dates)
    assert lead_a == 13 * 24
    assert leads_b == [13 * 24, 5 * 24, 1 * 24]
    assert repository_lead_times_hours([lead_a], leads_b) == (13 * 24, 5 * 24)
    assert release_lead_times_hours("2026-03-15T00:00:00Z", []) == (None, [])


def test_previous_release_outside_window_is_used_and_prerelease_separated():
    path = "/repos/group/repo/compare/v1.0...v1.1"
    client = Client(
        [release("v1.1", "2026-03-15T00:00:00Z"),
         release("rc", "2026-03-12T00:00:00Z", prerelease=True),
         release("v1.0", "2025-09-01T00:00:00Z")],
        {path: [commit("a", "2026-03-02T00:00:00Z"),
                commit("b", "2026-03-10T00:00:00Z"),
                commit("c", "2026-03-14T00:00:00Z")]},
        [{"name": "v1.1", "commit": {"sha": "a"}}],
    )
    release_rows, commit_rows, tags, prereleases, metric = releases.process_repository(client, "group/repo", START, END)
    assert release_rows[0]["previous_tag"] == "v1.0"
    assert release_rows[0]["compare_status"] == "ok"
    assert len(commit_rows) == 3
    assert metric["lead_time_a_hours"] == 312
    assert metric["lead_time_b_hours"] == 120
    assert metric["published_releases"] == 1
    assert len(prereleases) == 1
    assert tags[0]["commit_author_at"] == "2026-03-02T00:00:00Z"
    assert (path, "commits") in client.calls


def test_first_release_missing_commits_and_compare_404_are_reported():
    missing = GitHubNotFoundError(404, "https://api.github.com/compare", "not found")
    client = Client(
        [release("v1", "2026-01-01T00:00:00Z"), release("v2", "2026-02-01T00:00:00Z"),
         release("v3", "2026-03-01T00:00:00Z"), release("v4", "2026-04-01T00:00:00Z")],
        {"/repos/group/repo/compare/v1...v2": [],
         "/repos/group/repo/compare/v2...v3": missing,
         "/repos/group/repo/compare/v3...v4": [commit("x", None)]},
    )
    rows, commits, _, _, metric = releases.process_repository(client, "group/repo", START, END)
    assert [row["compare_status"] for row in rows] == [
        "first_release", "no_commits", "compare_404", "no_author_dates"
    ]
    assert commits == []
    assert metric["compare_404_count"] == 1
    assert metric["releases_without_commits"] == 1
    assert metric["commits_missing_author_date"] == 1
    assert metric["lead_time_a_hours"] == ""


def test_compare_paginates_all_commits_and_encodes_tag_slashes():
    path = "/repos/group/repo/compare/release%2F1...release%2F2"
    client = Client([], {path: [commit(str(i), "2026-03-02T00:00:00Z") for i in range(251)]})
    assert len(releases.compare_commits(client, "group/repo", "release/1", "release/2")) == 251
    assert client.calls == [(path, "commits")]


def test_stage_reads_selection_and_writes_reproducible_csvs(tmp_path):
    (tmp_path / "repositories.csv").write_text("repository,default_branch\ngroup/repo,main\n", encoding="utf-8")
    client = Client(
        [release("v1", "2025-09-01T00:00:00Z"), release("v2", "2026-03-15T00:00:00Z")],
        {"/repos/group/repo/compare/v1...v2": [commit("a", "2026-03-02T00:00:00Z")]},
    )
    cfg = Config(Window(START, END), Inclusion(5, 50), 1, tmp_path, tmp_path / "cache", 5, 30)
    releases.run(Context(cfg, client))
    with (tmp_path / "lead_time_metrics.csv").open(newline="") as file:
        metrics = list(csv.DictReader(file))
    assert metrics[0]["lead_time_a_hours"] == "312.0"
    assert metrics[0]["lead_time_b_hours"] == "312.0"
    assert (tmp_path / "release_commits.csv").is_file()
    assert (tmp_path / "tags.csv").is_file()
    assert (tmp_path / "pre_releases.csv").is_file()
