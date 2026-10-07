"""Selecao reproduzivel da amostra do Lab03 (issue #60)."""

from __future__ import annotations

import csv
import os
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from labs.lab03_dora.pipeline import Context
from shared.github_rest import GitHubNotFoundError, page_number

SEARCH_RANGES = ((10001, 1000000), (5001, 10000), (2001, 5000), (1001, 2000))
VALID_CONCLUSIONS = {"success", "failure", "timed_out", "startup_failure"}
DECISION_FIELDS = ("repository", "decision", "reason", "stars", "releases", "valid_workflow_runs")
REPOSITORY_FIELDS = (
    "repository", "stars", "language", "contributors", "created_at", "age_days",
    "default_branch", "published_releases", "valid_workflow_runs",
)


def _search_range(client, low: int, high: int) -> Iterator[dict]:
    """Divide uma faixa sempre que a busca atingiria o teto de 1.000 itens."""
    params = {"q": f"stars:{low}..{high}", "sort": "stars", "order": "desc", "per_page": 100}
    first = client.get("/search/repositories", params)
    if first.data.get("incomplete_results"):
        raise RuntimeError(f"Busca incompleta para stars:{low}..{high}; tente novamente.")
    total = first.data["total_count"]
    if total > 1000:
        if low == high:
            raise RuntimeError(f"Mais de 1.000 repositorios com {low} estrelas; subdivida a busca por data.")
        mid = (low + high) // 2
        yield from _search_range(client, mid + 1, high)
        yield from _search_range(client, low, mid)
        return
    response = first
    while True:
        yield from response.data["items"]
        next_page = page_number(response.links.get("next"))
        if next_page is None:
            break
        response = client.get("/search/repositories", {**params, "page": next_page})


def candidates(client) -> Iterator[dict]:
    for low, high in SEARCH_RANGES:
        yield from _search_range(client, low, high)


def _in_window(value: str | None, start: date, end: date) -> bool:
    return bool(value and start <= date.fromisoformat(value[:10]) <= end)


def _months(start: date, end: date) -> Iterator[tuple[date, date]]:
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        first = max(start, date(year, month, 1))
        last = min(end, date(year, month, monthrange(year, month)[1]))
        yield first, last
        month = month % 12 + 1
        year += month == 1


def _published_releases(client, repo: str, start: date, end: date) -> int:
    return sum(
        not release.get("draft", False)
        and not release.get("prerelease", False)
        and _in_window(release.get("published_at"), start, end)
        for release in client.paginate(f"/repos/{repo}/releases")
    )


def _valid_runs(client, repo: str, branch: str, start: date, end: date) -> int:
    def between(first: date, last: date) -> int:
        path = f"/repos/{repo}/actions/runs"
        params = {"branch": branch, "event": "push", "created": f"{first}..{last}", "per_page": 100}
        response = client.get(path, params)
        if response.data["total_count"] >= 1000:
            if first == last:
                raise RuntimeError(f"{repo}: teto de 1.000 workflow runs em {first}; nao e possivel contar com exatidao.")
            middle = first + timedelta(days=(last - first).days // 2)
            return between(first, middle) + between(middle + timedelta(days=1), last)
        count = 0
        while True:
            count += sum(
                run.get("event") == "push"
                and run.get("head_branch") == branch
                and run.get("conclusion") in VALID_CONCLUSIONS
                and _in_window(run.get("created_at"), first, last)
                for run in response.data["workflow_runs"]
            )
            next_page = page_number(response.links.get("next"))
            if next_page is None:
                return count
            response = client.get(path, {**params, "page": next_page})

    return sum(between(first, last) for first, last in _months(start, end))


def _contributors(client, repo: str) -> int:
    response = client.get(f"/repos/{repo}/contributors", {"per_page": 1, "anon": "true"})
    return page_number(response.links.get("last")) or len(response.data or [])


def inspect(client, candidate: dict, config) -> tuple[dict, dict | None]:
    repo = candidate["full_name"]
    decision = dict(repository=repo, decision="excluded", reason="", stars=candidate["stargazers_count"],
                    releases="", valid_workflow_runs="")
    try:
        workflows = client.get(f"/repos/{repo}/actions/workflows", {"per_page": 1}).data
        if workflows["total_count"] == 0:
            decision["reason"] = "no_actions"
            return decision, None
        start, end = config.window.start, config.window.end
        releases = _published_releases(client, repo, start, end)
        decision["releases"] = releases
        if releases < config.inclusion.min_releases:
            decision["reason"] = "insufficient_releases"
            return decision, None
        branch = candidate["default_branch"]
        runs = _valid_runs(client, repo, branch, start, end)
        decision["valid_workflow_runs"] = runs
        if runs < config.inclusion.min_workflow_runs:
            decision["reason"] = "insufficient_workflow_runs"
            return decision, None
        created_at = candidate["created_at"]
        metadata = dict(repository=repo, stars=candidate["stargazers_count"],
                        language=candidate.get("language") or "", contributors=_contributors(client, repo),
                        created_at=created_at, age_days=(end - date.fromisoformat(created_at[:10])).days,
                        default_branch=branch, published_releases=releases, valid_workflow_runs=runs)
        decision.update(decision="included", reason="included")
        return decision, metadata
    except GitHubNotFoundError:
        decision["reason"] = "repository_unavailable"
        return decision, None


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def run(ctx: Context) -> None:
    decisions: list[dict] = []
    selected: list[dict] = []
    for candidate in candidates(ctx.client):
        decision, metadata = inspect(ctx.client, candidate, ctx.config)
        decisions.append(decision)
        if metadata is not None:
            selected.append(metadata)
        if len(selected) >= ctx.config.target_repositories:
            break
    output = ctx.config.output_dir
    _write_csv(output / "repositories.csv", REPOSITORY_FIELDS, selected)
    _write_csv(output / "selection_decisions.csv", DECISION_FIELDS, decisions)
    reasons = ("no_actions", "insufficient_releases", "insufficient_workflow_runs", "repository_unavailable")
    counts = {reason: sum(d["reason"] == reason for d in decisions) for reason in reasons}
    remaining = len(decisions)
    funnel = [dict(stage="candidates_examined", remaining=remaining, excluded=0)]
    for reason in reasons:
        remaining -= counts[reason]
        funnel.append(dict(stage=reason, remaining=remaining, excluded=counts[reason]))
    _write_csv(output / "selection_funnel.csv", ("stage", "remaining", "excluded"), funnel)
    if len(selected) < ctx.config.target_repositories:
        raise RuntimeError(f"A busca terminou com {len(selected)} repositorios; meta: {ctx.config.target_repositories}.")
