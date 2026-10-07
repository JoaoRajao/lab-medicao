"""Coleta de runs e calculo de CFR (a) e recuperacao (issue #62)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from labs.lab03_dora.metricas.workflows import cfr_a, classify, recovery_episodes, recovery_summary
from labs.lab03_dora.pipeline import Context
from labs.lab03_dora.records import in_window, selected_repositories, write_csv
from shared.github_rest import page_number

RUN_FIELDS = (
    "repository", "run_id", "workflow_id", "event", "head_branch", "conclusion", "classification",
    "created_at", "run_started_at", "updated_at",
)
MONTH_FIELDS = ("repository", "month", "api_total_count", "hit_cap", "runs_collected")
EPISODE_FIELDS = (
    "repository", "workflow_id", "first_failure_run_id", "recovery_run_id", "started_at", "ended_at",
    "hours", "censored",
)
METRIC_FIELDS = (
    "repository", "workflow_runs_collected", "successful_runs", "failed_runs", "ignored_runs",
    "cfr_a", "recovery_episodes", "recovered_episodes", "censored_episodes",
    "censored_episode_ratio", "recovery_median_hours", "months_with_runs",
    "first_observed_run_at", "last_observed_run_at",
)


def months(start: date, end: date):
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        first = max(start, date(year, month, 1))
        last = min(end, date(year, month, monthrange(year, month)[1]))
        yield first, last
        month = month % 12 + 1
        year += month == 1


def collect_interval(client, repo: str, branch: str, first: date, last: date) -> tuple[list[dict], int, bool]:
    """Coleta tudo; subdivide um intervalo que pode ter sido truncado em 1.000."""
    path = f"/repos/{repo}/actions/runs"
    params = {"branch": branch, "event": "push", "created": f"{first}..{last}", "per_page": 100}
    response = client.get(path, params)
    total = response.data["total_count"]
    if total >= 1000:
        if first == last:
            raise RuntimeError(f"{repo}: >=1.000 workflow runs em {first}; nao e possivel garantir coleta completa.")
        middle = first + timedelta(days=(last - first).days // 2)
        left, _, _ = collect_interval(client, repo, branch, first, middle)
        right, _, _ = collect_interval(client, repo, branch, middle + timedelta(days=1), last)
        return left + right, total, True
    runs = list(response.data["workflow_runs"])
    next_page = page_number(response.links.get("next"))
    while next_page is not None:
        response = client.get(path, {**params, "page": next_page})
        runs.extend(response.data["workflow_runs"])
        next_page = page_number(response.links.get("next"))
    return runs, total, False


def collect_repository(client, repo: str, branch: str, start: date, end: date) -> tuple[list[dict], list[dict]]:
    runs: list[dict] = []
    audits: list[dict] = []
    seen_ids: set[int] = set()
    for first, last in months(start, end):
        page_runs, reported_total, hit_cap = collect_interval(client, repo, branch, first, last)
        accepted = 0
        for run in page_runs:
            if run["id"] in seen_ids:
                continue
            if run.get("event") != "push" or run.get("head_branch") != branch:
                continue
            if not in_window(run.get("created_at"), start, end):
                continue
            runs.append(run)
            seen_ids.add(run["id"])
            accepted += 1
        audits.append(dict(repository=repo, month=first.strftime("%Y-%m"), api_total_count=reported_total,
                           hit_cap=hit_cap, runs_collected=accepted))
    return runs, audits


def process_repository(client, repo: str, branch: str, start: date, end: date) -> tuple[list[dict], list[dict], list[dict], dict]:
    runs, audits = collect_repository(client, repo, branch, start, end)
    cfr, successes, failures, ignored = cfr_a(runs)
    episodes = recovery_episodes(runs)
    recovery, completed, censored, censored_ratio = recovery_summary(episodes)
    run_rows = [dict(repository=repo, run_id=run["id"], workflow_id=run["workflow_id"],
                     event=run["event"], head_branch=run["head_branch"], conclusion=run.get("conclusion") or "",
                     classification=classify(run.get("conclusion")), created_at=run["created_at"],
                     run_started_at=run.get("run_started_at") or "", updated_at=run.get("updated_at") or "")
                for run in runs]
    episode_rows = [dict(repository=repo, **episode) for episode in episodes]
    metric = dict(repository=repo, workflow_runs_collected=len(runs), successful_runs=successes,
                  failed_runs=failures, ignored_runs=ignored, cfr_a=cfr if cfr is not None else "",
                  recovery_episodes=len(episodes), recovered_episodes=completed, censored_episodes=censored,
                  censored_episode_ratio=censored_ratio if censored_ratio is not None else "",
                  recovery_median_hours=recovery if recovery is not None else "",
                  months_with_runs=sum(audit["runs_collected"] > 0 for audit in audits),
                  first_observed_run_at=min((run["created_at"] for run in runs), default=""),
                  last_observed_run_at=max((run["created_at"] for run in runs), default=""))
    return run_rows, audits, episode_rows, metric


def run(ctx: Context) -> None:
    output = ctx.config.output_dir
    all_runs: list[dict] = []
    all_audits: list[dict] = []
    all_episodes: list[dict] = []
    metrics: list[dict] = []
    for repo, branch in selected_repositories(output):
        runs, audits, episodes, metric = process_repository(
            ctx.client, repo, branch, ctx.config.window.start, ctx.config.window.end
        )
        all_runs.extend(runs)
        all_audits.extend(audits)
        all_episodes.extend(episodes)
        metrics.append(metric)
    write_csv(output / "workflow_runs.csv", RUN_FIELDS, all_runs)
    write_csv(output / "workflow_run_months.csv", MONTH_FIELDS, all_audits)
    write_csv(output / "recovery_episodes.csv", EPISODE_FIELDS, all_episodes)
    write_csv(output / "workflow_metrics.csv", METRIC_FIELDS, metrics)
