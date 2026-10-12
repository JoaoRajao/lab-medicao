"""Deployment frequency (RQ 01) e classificacao DORA com os cortes fixos da secao 5 do enunciado."""

from __future__ import annotations

import math
from statistics import median

CATEGORIES = {4: "Elite", 3: "High", 2: "Medium", 1: "Low"}
# "1 por mes" em releases por semana: um mes medio (365,25 / 12 dias) tem ~4,35 semanas.
ONCE_PER_MONTH_PER_WEEK = 7 / (365.25 / 12)
HOURS_PER_DAY = 24
HOURS_PER_WEEK = 7 * HOURS_PER_DAY


def deployment_frequency(releases_in_window: int, window_weeks: float) -> float:
    """Releases publicadas na janela por semana (RQ 01)."""
    if window_weeks <= 0:
        raise ValueError("A janela precisa ter duracao positiva.")
    return releases_in_window / window_weeks


def frequency_points(per_week: float) -> int:
    if per_week >= 7:
        return 4
    if per_week >= 1:
        return 3
    if per_week >= ONCE_PER_MONTH_PER_WEEK:
        return 2
    return 1


def lead_time_points(hours: float) -> int:
    if hours < HOURS_PER_DAY:
        return 4
    if hours < HOURS_PER_WEEK:
        return 3
    if hours < 30 * HOURS_PER_DAY:
        return 2
    return 1


def failure_rate_points(rate: float) -> int:
    if rate <= 0.15:
        return 4
    if rate <= 0.30:
        return 3
    if rate <= 0.45:
        return 2
    return 1


def recovery_points(hours: float) -> int:
    if hours < 1:
        return 4
    if hours < HOURS_PER_DAY:
        return 3
    if hours < HOURS_PER_WEEK:
        return 2
    return 1


def overall_points(points: list[int | None]) -> int | None:
    """Mediana das notas disponiveis, arredondada para baixo (ex.: 4, 3, 3, 1 -> 3, High).

    Metricas sem valor (ex.: repositorio sem nenhum episodio de falha) ficam fora da mediana; quem consome o
    resultado deve reportar quantas notas entraram.
    """
    available = [p for p in points if p is not None]
    return math.floor(median(available)) if available else None


def classify(
    frequency_per_week: float | None,
    lead_time_hours: float | None,
    failure_rate: float | None,
    recovery_hours: float | None,
) -> dict[str, int | str | None]:
    """Notas por metrica, nota geral e nome da categoria, para uma combinacao de definicoes."""
    points = {
        "frequency": None if frequency_per_week is None else frequency_points(frequency_per_week),
        "lead_time": None if lead_time_hours is None else lead_time_points(lead_time_hours),
        "failure_rate": None if failure_rate is None else failure_rate_points(failure_rate),
        "recovery": None if recovery_hours is None else recovery_points(recovery_hours),
    }
    overall = overall_points(list(points.values()))
    return {
        **points,
        "overall": overall,
        "category": CATEGORIES.get(overall, "") if overall is not None else "",
        "metrics_used": sum(p is not None for p in points.values()),
    }
