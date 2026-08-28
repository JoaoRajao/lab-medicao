from __future__ import annotations

from datetime import datetime


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_between(start: datetime | None, end: datetime) -> int | None:
    if start is None:
        return None
    return max((end - start).days, 0)
