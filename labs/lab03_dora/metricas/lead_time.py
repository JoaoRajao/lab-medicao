"""Lead time for changes, com as duas unidades exigidas pela RQ 02."""

from __future__ import annotations

from statistics import median

from labs.lab03_dora.records import timestamp


def release_lead_times_hours(published_at: str, author_dates: list[str]) -> tuple[float | None, list[float]]:
    """Retorna (variante por release, variantes por commit), em horas."""
    if not author_dates:
        return None, []
    released = timestamp(published_at)
    per_commit = [(released - timestamp(author_date)).total_seconds() / 3600 for author_date in author_dates]
    return max(per_commit), per_commit


def repository_lead_times_hours(release_values: list[float], commit_values: list[float]) -> tuple[float | None, float | None]:
    return (
        median(release_values) if release_values else None,
        median(commit_values) if commit_values else None,
    )
