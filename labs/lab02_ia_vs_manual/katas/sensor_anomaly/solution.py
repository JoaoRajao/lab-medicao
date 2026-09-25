from __future__ import annotations


def detect_anomalies(
    readings: list[float],
    max_jump: float,
    min_value: float,
    max_value: float,
) -> list[dict[str, float | int | str]]:
    anomalies: list[dict[str, float | int | str]] = []

    for index, value in enumerate(readings):
        if value < min_value or value > max_value:
            anomalies.append({"index": index, "value": value, "reason": "range"})
            continue
        if index > 0 and abs(value - readings[index - 1]) > max_jump:
            anomalies.append({"index": index, "value": value, "reason": "jump"})

    return anomalies