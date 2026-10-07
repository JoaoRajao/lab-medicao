"""CFR (a) e recuperacao de falhas de CI, por repositorio."""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from labs.lab03_dora.records import timestamp

FAILURES = {"failure", "timed_out", "startup_failure"}


def classify(conclusion: str | None) -> str:
    if conclusion == "success":
        return "success"
    if conclusion in FAILURES:
        return "failure"
    return "ignored"


def cfr_a(runs: list[dict]) -> tuple[float | None, int, int, int]:
    classes = [classify(run.get("conclusion")) for run in runs]
    successes = classes.count("success")
    failures = classes.count("failure")
    denominator = successes + failures
    return (failures / denominator if denominator else None, successes, failures, classes.count("ignored"))


def recovery_episodes(runs: list[dict]) -> list[dict]:
    """Uma falha inicial so inicia episodio se houve sucesso anterior no workflow."""
    grouped: dict[int, list[dict]] = defaultdict(list)
    for run in runs:
        if classify(run.get("conclusion")) != "ignored":
            grouped[run["workflow_id"]].append(run)
    episodes: list[dict] = []
    for workflow_id, group in grouped.items():
        group.sort(key=lambda run: timestamp(run.get("run_started_at") or run["created_at"]))
        had_success = False
        first_failure: dict | None = None
        for run in group:
            classification = classify(run.get("conclusion"))
            if classification == "success":
                if first_failure is not None:
                    started = first_failure.get("run_started_at") or first_failure["created_at"]
                    ended = run["updated_at"]
                    episodes.append({
                        "workflow_id": workflow_id, "first_failure_run_id": first_failure["id"],
                        "recovery_run_id": run["id"], "started_at": started, "ended_at": ended,
                        "hours": (timestamp(ended) - timestamp(started)).total_seconds() / 3600,
                        "censored": False,
                    })
                    first_failure = None
                had_success = True
            elif had_success and first_failure is None:
                first_failure = run
        if first_failure is not None:
            episodes.append({
                "workflow_id": workflow_id, "first_failure_run_id": first_failure["id"],
                "recovery_run_id": "", "started_at": first_failure.get("run_started_at") or first_failure["created_at"],
                "ended_at": "", "hours": "", "censored": True,
            })
    return episodes


def recovery_summary(episodes: list[dict]) -> tuple[float | None, int, int, float | None]:
    complete = [episode["hours"] for episode in episodes if not episode["censored"]]
    censored = sum(episode["censored"] for episode in episodes)
    return (median(complete) if complete else None, len(complete), censored,
            censored / len(episodes) if episodes else None)
