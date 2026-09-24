from __future__ import annotations

import json
from collections import defaultdict
from itertools import product
from pathlib import Path
from statistics import mean, median
from typing import Any


Record = dict[str, Any]


def load_trials(path: Path) -> list[Record]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def load_trials_from_paths(paths: list[Path]) -> list[Record]:
    records: list[Record] = []
    for path in paths:
        records.extend(load_trials(path))
    return records


def percentile(values: list[float], pct: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * pct
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_by_treatment(records: list[Record], metric: str) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    by_treatment: dict[str, list[float]] = defaultdict(list)
    for record in records:
        value = record.get(metric)
        if value is not None:
            by_treatment[record["treatment"]].append(float(value))

    for treatment, values in sorted(by_treatment.items()):
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        result[treatment] = {
            "n": float(len(values)),
            "mean": mean(values),
            "median": median(values),
            "q1": q1,
            "q3": q3,
            "iqr": q3 - q1,
            "min": min(values),
            "max": max(values),
        }
    return result


def detect_outliers(records: list[Record], metric: str) -> dict[str, list[Record]]:
    result: dict[str, list[Record]] = {}
    by_treatment: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        if record.get(metric) is not None:
            by_treatment[record["treatment"]].append(record)

    for treatment, group in sorted(by_treatment.items()):
        values = [float(record[metric]) for record in group]
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        result[treatment] = [
            record for record in group
            if float(record[metric]) < lower or float(record[metric]) > upper
        ]
    return result


def pair_by_participant(records: list[Record], metric: str) -> list[dict[str, float | str]]:
    by_participant_treatment: dict[tuple[str, str], list[float]] = defaultdict(list)
    for record in records:
        value = record.get(metric)
        if value is not None:
            by_participant_treatment[(record["participant"], record["treatment"])].append(float(value))

    pairs = []
    participants = sorted({record["participant"] for record in records})
    for participant in participants:
        manual = by_participant_treatment.get((participant, "manual"), [])
        ai = by_participant_treatment.get((participant, "ai_assisted"), [])
        if manual and ai:
            manual_mean = mean(manual)
            ai_mean = mean(ai)
            pairs.append({
                "participant": participant,
                "manual": manual_mean,
                "ai_assisted": ai_mean,
                "diff_ai_minus_manual": ai_mean - manual_mean,
            })
    return pairs


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        next_position = position + 1
        while next_position < len(indexed) and indexed[next_position][1] == indexed[position][1]:
            next_position += 1
        rank = (position + 1 + next_position) / 2
        for original_index, _ in indexed[position:next_position]:
            ranks[original_index] = rank
        position = next_position
    return ranks


def wilcoxon_signed_rank(differences: list[float]) -> dict[str, float | int | str]:
    non_zero = [difference for difference in differences if difference != 0]
    if not non_zero:
        return {
            "n": 0,
            "w_plus": 0.0,
            "w_minus": 0.0,
            "statistic": 0.0,
            "p_value": 1.0,
            "note": "all differences are zero",
        }

    abs_values = [abs(difference) for difference in non_zero]
    ranks = average_ranks(abs_values)
    w_plus = sum(rank for rank, difference in zip(ranks, non_zero, strict=True) if difference > 0)
    w_minus = sum(rank for rank, difference in zip(ranks, non_zero, strict=True) if difference < 0)
    statistic = min(w_plus, w_minus)
    total_rank = sum(ranks)

    possible = []
    for signs in product((0, 1), repeat=len(ranks)):
        signed_sum = sum(rank for rank, sign in zip(ranks, signs, strict=True) if sign)
        possible.append(min(signed_sum, total_rank - signed_sum))
    p_value = sum(value <= statistic for value in possible) / len(possible)

    return {
        "n": len(non_zero),
        "w_plus": w_plus,
        "w_minus": w_minus,
        "statistic": statistic,
        "p_value": min(1.0, p_value),
        "note": "exact two-sided p-value",
    }


def format_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{float(value):.{digits}f}"


def metric_table(records: list[Record], metric: str, label: str) -> str:
    summary = summarize_by_treatment(records, metric)
    rows = [
        "| Metrica | Tratamento | n | Mediana | Q1 | Q3 | IQR | Min | Max | Media |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for treatment in ("manual", "ai_assisted"):
        values = summary[treatment]
        rows.append(
            "| "
            + " | ".join(
                [
                    label,
                    treatment,
                    format_number(values["n"]),
                    format_number(values["median"]),
                    format_number(values["q1"]),
                    format_number(values["q3"]),
                    format_number(values["iqr"]),
                    format_number(values["min"]),
                    format_number(values["max"]),
                    format_number(values["mean"]),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def outlier_lines(records: list[Record], metric: str, label: str) -> list[str]:
    outliers = detect_outliers(records, metric)
    lines = []
    for treatment in ("manual", "ai_assisted"):
        group = outliers.get(treatment, [])
        if group:
            ids = ", ".join(
                f"{record['trial_id']}={format_number(float(record[metric]))}" for record in group
            )
        else:
            ids = "nenhum"
        lines.append(f"- {label} / {treatment}: {ids}.")
    return lines


def wilcoxon_line(records: list[Record], metric: str, label: str) -> str:
    pairs = pair_by_participant(records, metric)
    differences = [float(pair["diff_ai_minus_manual"]) for pair in pairs]
    result = wilcoxon_signed_rank(differences)
    median_delta = median(differences) if differences else 0.0
    return (
        f"| {label} | {len(pairs)} | {format_number(median_delta)} | "
        f"{format_number(float(result['statistic']))} | {format_number(float(result['p_value']), 4)} | "
        f"{result['note']} |"
    )
