from __future__ import annotations

import csv
from datetime import date
from types import SimpleNamespace

import pytest

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


def tag(name, sha, authored, committed=None, annotated=False):
    target = {"__typename": "Commit", "oid": sha, "authoredDate": authored, "committedDate": committed or authored}
    return {"name": name, "target": {"__typename": "Tag", "target": target} if annotated else target}


class Client:
    def __init__(self, release_items, comparisons=None, tag_pages=None, statuses=None):
        self.release_items = release_items
        self.comparisons = comparisons or {}
        self.tag_pages = tag_pages or [[]]
        self.statuses = statuses or {}
        self.calls = []

    def paginate(self, path, params=None, item_key=None, slim=None):
        self.calls.append((path, item_key))
        if path.endswith("/releases"):
            return iter(self.release_items)
        value = self.comparisons[path]
        if isinstance(value, Exception):
            raise value
        return iter(value)

    def get(self, path, params=None, slim=None):
        value = self.comparisons[path]
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(data={"status": self.statuses.get(path, "ahead"), "total_commits": len(value)})

    def graphql(self, query, variables, cache_key):
        self.calls.append(("graphql", variables["after"]))
        page = int(variables["after"] or 0)
        has_next = page + 1 < len(self.tag_pages)
        return {"repository": {"refs": {"nodes": self.tag_pages[page],
                                        "pageInfo": {"hasNextPage": has_next, "endCursor": str(page + 1)}}}}


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
        [[tag("v1.1", "a", "2026-03-02T00:00:00Z")]],
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
    commits, summary = releases.compare_commits(client, "group/repo", "release/1", "release/2")
    assert len(commits) == summary["total_commits"] == 251
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


def test_tags_use_commit_date_and_stop_paging_before_the_window():
    client = Client([], tag_pages=[
        [tag("v3", "c", "2026-05-01T00:00:00Z", annotated=True),
         {"name": "odd", "target": {"__typename": "Tree"}},
         tag("v2", "b", "2025-09-20T00:00:00Z", committed="2025-10-02T00:00:00Z")],
        [tag("v1", "a", "2025-08-01T00:00:00Z")],
        [tag("v0", "z", "2024-01-01T00:00:00Z")],
    ])
    rows = releases.collect_tags(client, "group/repo", START, END)
    assert [(r["tag_name"], r["status"]) for r in rows] == [("v3", "ok"), ("odd", "not_a_commit")]
    assert rows[0]["commit_sha"] == "c"
    assert client.calls == [("graphql", None), ("graphql", "1")]


def test_diverged_compare_and_negative_lead_time_are_flagged():
    path = "/repos/group/repo/compare/v2.0...v1.9"
    client = Client(
        [release("v2.0", "2026-01-01T00:00:00Z"), release("v1.9", "2026-02-01T00:00:00Z")],
        {path: [commit("a", "2026-01-20T00:00:00Z"), commit("b", "2026-02-02T00:00:00Z")]},
        statuses={path: "diverged"},
    )
    rows, _, _, _, metric = releases.process_repository(client, "group/repo", START, END)
    assert rows[1]["compare_api_status"] == "diverged"
    assert rows[1]["negative_lead_time_commits"] == 1
    assert metric["releases_diverged"] == 1
    assert metric["negative_lead_time_commits"] == 1


def test_compare_with_missing_commits_is_flagged_and_still_measured():
    path = "/repos/group/repo/compare/v1...v2"

    class Truncated(Client):
        def get(self, path, params=None, slim=None):
            return SimpleNamespace(data={"status": "ahead", "total_commits": 4})

    client = Truncated([release("v1", "2026-01-01T00:00:00Z"), release("v2", "2026-02-01T00:00:00Z")],
                       {path: [commit("a", "2026-01-20T00:00:00Z")]})
    rows, _, _, _, metric = releases.process_repository(client, "group/repo", START, END)
    assert rows[1]["commits_missing_from_compare"] == 3
    assert rows[1]["compare_status"] == "ok"
    assert metric["releases_incomplete_compare"] == 1


def test_slim_compare_keeps_only_what_the_lab_uses():
    page = {"status": "ahead", "total_commits": 1, "files": [{"patch": "x" * 10_000}], "base_commit": {},
            "commits": [{"sha": "a", "url": "u", "author": {"login": "x"},
                         "commit": {"author": {"date": "2026-03-02T00:00:00Z", "name": "n"}, "message": "fix: y" * 1000}}]}
    slim = releases.slim_compare(page)
    assert slim == {"status": "ahead", "total_commits": 1, "commits": [
        {"sha": "a", "commit": {"author": {"date": "2026-03-02T00:00:00Z"}, "message": ("fix: y" * 1000)[:2000]}}
    ]}
