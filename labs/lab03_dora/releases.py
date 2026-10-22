"""Coleta de releases, tags e commits e calculo do lead time (issue #61)."""

from __future__ import annotations

from urllib.parse import quote

from labs.lab03_dora.metricas.cfr_b import is_fix_commit
from labs.lab03_dora.metricas.lead_time import release_lead_times_hours, repository_lead_times_hours
from labs.lab03_dora.pipeline import Context
from labs.lab03_dora.records import (
    in_window, map_repositories, selected_repositories, slim_releases, timestamp, write_csv,
)
from shared.github_rest import GitHubNotFoundError

RELEASE_FIELDS = (
    "repository", "tag_name", "release_name", "published_at", "previous_tag", "compare_status", "compare_api_status",
    "commits_compared", "fix_commits", "commits_missing_from_compare", "commits_missing_author_date", "negative_lead_time_commits",
    "lead_time_release_hours",
)
COMMIT_FIELDS = ("repository", "release_tag", "commit_sha", "commit_author_at", "lead_time_hours")
TAG_FIELDS = ("repository", "tag_name", "commit_sha", "commit_author_at", "status")
PRERELEASE_FIELDS = ("repository", "tag_name", "published_at")
METRIC_FIELDS = (
    "repository", "published_releases", "pre_releases", "tags_in_window", "releases_compared",
    "compare_404_count", "releases_without_commits", "releases_diverged", "releases_incomplete_compare",
    "commits_compared",
    "commits_missing_author_date", "negative_lead_time_commits", "lead_time_a_hours", "lead_time_b_hours",
)


def collect_releases(client, repo: str, start, end) -> tuple[list[dict], list[dict]]:
    regular: list[dict] = []
    prereleases: list[dict] = []
    seen: set[str] = set()
    for release in client.paginate(f"/repos/{repo}/releases", slim=slim_releases):
        # Uma release publicada durante a paginacao empurra as demais e repete um item na pagina seguinte.
        tag = release.get("tag_name")
        if tag and tag in seen:
            continue
        seen.add(tag)
        if release.get("draft") or not release.get("published_at"):
            continue
        if release.get("prerelease"):
            if in_window(release["published_at"], start, end):
                prereleases.append(release)
        else:
            regular.append(release)
    regular.sort(key=lambda release: timestamp(release["published_at"]))
    return regular, prereleases


TAGS_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/tags/", first: 100, after: $after,
         orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        target {
          __typename
          ... on Commit { oid authoredDate committedDate }
          ... on Tag { target { __typename ... on Commit { oid authoredDate committedDate } } }
        }
      }
    }
  }
}
"""


def _tag_commit(target: dict | None) -> dict | None:
    """Commit apontado pela tag (leve ou anotada); None se apontar para outra coisa."""
    if target and target.get("__typename") == "Tag":
        target = target.get("target")
    return target if target and target.get("__typename") == "Commit" else None


def collect_tags(client, repo: str, start, end) -> list[dict]:
    """Tags com a data do commit apontado (variante da RQ 07), via GraphQL.

    As tags vem ordenadas pela data do commit, da mais nova para a mais antiga: a coleta para quando a
    pagina ja chegou antes da janela, em vez de consultar um commit por tag em toda a historia.
    """
    owner, name = repo.split("/", 1)
    rows: list[dict] = []
    after = None
    while True:
        data = client.graphql(TAGS_QUERY, {"owner": owner, "name": name, "after": after}, f"repos/{repo}/tags")
        refs = data["repository"]["refs"]
        reached_before_window = False
        for node in refs["nodes"]:
            commit = _tag_commit(node.get("target"))
            if commit is None:
                rows.append(dict(repository=repo, tag_name=node["name"], commit_sha="",
                                 commit_author_at="", status="not_a_commit"))
                continue
            if timestamp(commit["committedDate"]).date() < start:
                reached_before_window = True
            if in_window(commit["authoredDate"], start, end):
                rows.append(dict(repository=repo, tag_name=node["name"], commit_sha=commit["oid"],
                                 commit_author_at=commit["authoredDate"], status="ok"))
        if reached_before_window or not refs["pageInfo"]["hasNextPage"]:
            return rows
        after = refs["pageInfo"]["endCursor"]


MAX_MESSAGE_CHARS = 2000


def slim_compare(data: dict) -> dict:
    """So o que o lab usa do compare. Cada pagina traz ate 300 arquivos com diffs, que o cache nao precisa."""
    commits = []
    for item in data.get("commits") or []:
        commit = item.get("commit") or {}
        commits.append({"sha": item.get("sha"), "commit": {
            "author": {"date": (commit.get("author") or {}).get("date")},
            "message": (commit.get("message") or "")[:MAX_MESSAGE_CHARS],
        }})
    return {"status": data.get("status"), "total_commits": data.get("total_commits"), "commits": commits}


def compare_commits(client, repo: str, base_tag: str, head_tag: str) -> tuple[list[dict], dict]:
    """Commits de `base...head`, paginando ate o fim, e o resumo do compare (status e total)."""
    path = f"/repos/{repo}/compare/{quote(base_tag, safe='')}...{quote(head_tag, safe='')}"
    # mesma URL da 1a pagina do paginate: vem do cache
    first = client.get(path, {"per_page": 100}, slim=slim_compare).data
    commits = list(client.paginate(path, item_key="commits", slim=slim_compare))
    return commits, {"status": first.get("status", ""), "total_commits": first.get("total_commits", len(commits))}


def process_repository(client, repo: str, start, end) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    regular, prereleases = collect_releases(client, repo, start, end)
    tag_rows = collect_tags(client, repo, start, end)
    pre_rows = [dict(repository=repo, tag_name=r["tag_name"], published_at=r["published_at"]) for r in prereleases]
    release_rows: list[dict] = []
    commit_rows: list[dict] = []
    by_release: list[float] = []
    by_commit: list[float] = []
    compare_404 = no_commits = missing_author = compared = diverged = negative = incomplete = 0
    in_window_releases = 0
    for index, release in enumerate(regular):
        if not in_window(release["published_at"], start, end):
            continue
        in_window_releases += 1
        previous = regular[index - 1] if index else None
        row = dict(repository=repo, tag_name=release["tag_name"], release_name=release.get("name") or "",
                   published_at=release["published_at"],
                   previous_tag=previous["tag_name"] if previous else "", compare_status="", compare_api_status="",
                   commits_compared=0, fix_commits=0, commits_missing_from_compare=0, commits_missing_author_date=0,
                   negative_lead_time_commits=0,
                   lead_time_release_hours="")
        if previous is None:
            row["compare_status"] = "first_release"
            release_rows.append(row)
            continue
        try:
            commits, summary = compare_commits(client, repo, previous["tag_name"], release["tag_name"])
        except GitHubNotFoundError:
            compare_404 += 1
            row["compare_status"] = "compare_404"
            release_rows.append(row)
            continue
        # Em compares muito grandes a paginacao da API pode devolver alguns commits a menos que `total_commits`:
        # a release segue no calculo e a diferenca fica registrada para auditoria.
        missing = max(0, (summary["total_commits"] or 0) - len(commits))
        row["commits_missing_from_compare"] = missing
        incomplete += missing > 0
        # "diverged": a release anterior por data nao e ancestral de R (ex.: backport em outro branch).
        row["compare_api_status"] = summary["status"]
        diverged += summary["status"] == "diverged"
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
            if hours < 0:  # data de autoria posterior a release (relogio errado, rebase): mantido e contado
                negative += 1
                row["negative_lead_time_commits"] += 1
            commit_rows.append(dict(repository=repo, release_tag=release["tag_name"], commit_sha=commit["sha"],
                                    commit_author_at=author_at, lead_time_hours=hours))
        row["commits_compared"] = len(commits)
        row["fix_commits"] = sum(is_fix_commit((commit.get("commit") or {}).get("message")) for commit in commits)
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
                  releases_without_commits=no_commits, releases_diverged=diverged,
                  releases_incomplete_compare=incomplete, commits_compared=compared,
                  commits_missing_author_date=missing_author, negative_lead_time_commits=negative,
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
    window = ctx.config.window
    results = map_repositories(
        lambda pair: process_repository(ctx.client, pair[0], window.start, window.end),
        selected_repositories(output), ctx.config.workers,
    )
    for releases, commits, tags, prereleases, metric in results:
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
