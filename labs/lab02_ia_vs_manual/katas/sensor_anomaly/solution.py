from __future__ import annotations


def detect_anomalies(
    readings: list[float],
    max_jump: float,
    min_value: float,
    max_value: float,
) -> list[dict[str, float | int | str]]:
    raise NotImplementedError

