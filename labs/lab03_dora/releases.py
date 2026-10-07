"""Coleta de releases, tags e commits e calculo do lead time (issue #61)."""

from __future__ import annotations

from urllib.parse import quote

from labs.lab03_dora.metricas.lead_time import release_lead_times_hours, repository_lead_times_hours
from labs.lab03_dora.pipeline import Context
from labs.lab03_dora.records import in_window, selected_repositories, timestamp, write_csv
from shared.github_rest import GitHubNotFoundError

RELEASE_FIELDS = (
    "repository", "tag_name", "published_at", "previous_tag", "compare_status",
    "commits_compared", "commits_missing_author_date", "lead_time_release_hours",
)
COMMIT_FIELDS = ("repository", "release_tag", "commit_sha", "commit_author_at", "lead_time_hours")
TAG_FIELDS = ("repository", "tag_name", "commit_sha", "commit_author_at", "status")
PRERELEASE_FIELDS = ("repository", "tag_name", "published_at")
METRIC_FIELDS = (
    "repository", "published_releases", "pre_releases", "tags_in_window", "releases_compared",
    "compare_404_count", "releases_without_commits", "commits_compared", "commits_missing_author_date",
    "lead_time_a_hours", "lead_time_b_hours",
)


def collect_releases(client, repo: str, start, end) -> tuple[list[dict], list[dict]]:
    regular: list[dict] = []
    prereleases: list[dict] = []
    for release in client.paginate(f"/repos/{repo}/releases"):
        if release.get("draft") or not release.get("published_at"):
            continue
        if release.get("prerelease"):
            if in_window(release["published_at"], start, end):
                prereleases.append(release)
        else:
            regular.append(release)
    regular.sort(key=lambda release: timestamp(release["published_at"]))
    return regular, prereleases


def collect_tags(client, repo: str, start, end) -> list[dict]:
    rows: list[dict] = []
    commit_dates: dict[str, str | None] = {}
    for tag in client.paginate(f"/repos/{repo}/tags"):
        sha = tag["commit"]["sha"]
        if sha not in commit_dates:
            try:
                commit_dates[sha] = client.get(f"/repos/{repo}/commits/{quote(sha, safe='')}").data["commit"]["author"]["date"]
            except GitHubNotFoundError:
                commit_dates[sha] = None
        author_at = commit_dates[sha]
        if author_at and in_window(author_at, start, end):
            rows.append(dict(repository=repo, tag_name=tag["name"], commit_sha=sha,
                             commit_author_at=author_at, status="ok"))
        elif author_at is None:
            rows.append(dict(repository=repo, tag_name=tag["name"], commit_sha=sha,
                             commit_author_at="", status="commit_404"))
    return rows


def compare_commits(client, repo: str, base_tag: str, head_tag: str) -> list[dict]:
    base = quote(base_tag, safe="")
    head = quote(head_tag, safe="")
    return list(client.paginate(f"/repos/{repo}/compare/{base}...{head}", item_key="commits"))


def process_repository(client, repo: str, start, end) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    regular, prereleases = collect_releases(client, repo, start, end)
    tag_rows = collect_tags(client, repo, start, end)
    pre_rows = [dict(repository=repo, tag_name=r["tag_name"], published_at=r["published_at"]) for r in prereleases]
    release_rows: list[dict] = []
    commit_rows: list[dict] = []
    by_release: list[float] = []
    by_commit: list[float] = []
    compare_404 = no_commits = missing_author = compared = 0
    in_window_releases = 0
    for index, release in enumerate(regular):
        if not in_window(release["published_at"], start, end):
            continue
        in_window_releases += 1
        previous = regular[index - 1] if index else None
        row = dict(repository=repo, tag_name=release["tag_name"], published_at=release["published_at"],
                   previous_tag=previous["tag_name"] if previous else "", compare_status="",
                   commits_compared=0, commits_missing_author_date=0, lead_time_release_hours="")
        if previous is None:
            row["compare_status"] = "first_release"
            release_rows.append(row)
            continue
        try:
            commits = compare_commits(client, repo, previous["tag_name"], release["tag_name"])
        except GitHubNotFoundError:
            compare_404 += 1
            row["compare_status"] = "compare_404"
            release_rows.append(row)
            continue
        if not commits:
            no_commits += 1
            row["compare_status"] = "no_commits"
            release_rows.append(row)
            continue
        author_dates: list[str] = []
        for commit in commits:
            author_at = (commit.get("commit", {}).get("author") or {}).get("date")
            if not author_at:
                missing_author += 1
                row["commits_missing_author_date"] += 1
                continue
            author_dates.append(author_at)
            hours = (timestamp(release["published_at"]) - timestamp(author_at)).total_seconds() / 3600
            commit_rows.append(dict(repository=repo, release_tag=release["tag_name"], commit_sha=commit["sha"],
                                    commit_author_at=author_at, lead_time_hours=hours))
        row["commits_compared"] = len(commits)
        compared += len(commits)
        lead_a, leads_b = release_lead_times_hours(release["published_at"], author_dates)
        if lead_a is None:
            row["compare_status"] = "no_author_dates"
        else:
            row["compare_status"] = "ok"
            row["lead_time_release_hours"] = lead_a
            by_release.append(lead_a)
            by_commit.extend(leads_b)
        release_rows.append(row)
    lead_a, lead_b = repository_lead_times_hours(by_release, by_commit)
    metric = dict(repository=repo, published_releases=in_window_releases, pre_releases=len(pre_rows),
                  tags_in_window=sum(row["status"] == "ok" for row in tag_rows),
                  releases_compared=len(by_release), compare_404_count=compare_404,
                  releases_without_commits=no_commits, commits_compared=compared,
                  commits_missing_author_date=missing_author,
                  lead_time_a_hours=lead_a if lead_a is not None else "",
                  lead_time_b_hours=lead_b if lead_b is not None else "")
    return release_rows, commit_rows, tag_rows, pre_rows, metric


def run(ctx: Context) -> None:
    output = ctx.config.output_dir
    all_releases: list[dict] = []
    all_commits: list[dict] = []
    all_tags: list[dict] = []
    all_prereleases: list[dict] = []
    metrics: list[dict] = []
    for repo, _branch in selected_repositories(output):
        releases, commits, tags, prereleases, metric = process_repository(
            ctx.client, repo, ctx.config.window.start, ctx.config.window.end
        )
        all_releases.extend(releases)
        all_commits.extend(commits)
        all_tags.extend(tags)
        all_prereleases.extend(prereleases)
        metrics.append(metric)
    write_csv(output / "releases.csv", RELEASE_FIELDS, all_releases)
    write_csv(output / "release_commits.csv", COMMIT_FIELDS, all_commits)
    write_csv(output / "tags.csv", TAG_FIELDS, all_tags)
    write_csv(output / "pre_releases.csv", PRERELEASE_FIELDS, all_prereleases)
    write_csv(output / "lead_time_metrics.csv", METRIC_FIELDS, metrics)
