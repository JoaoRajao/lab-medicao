from __future__ import annotations

import pytest

from labs.lab03_dora.metricas.dora import (
    ONCE_PER_MONTH_PER_WEEK,
    classify,
    deployment_frequency,
    failure_rate_points,
    frequency_points,
    lead_time_points,
    overall_points,
    recovery_points,
)

WEEKS = 365 / 7


def test_deployment_frequency_is_releases_per_week_of_the_window():
    assert deployment_frequency(52, 52) == 1
    assert deployment_frequency(365, WEEKS) == pytest.approx(7)
    assert deployment_frequency(0, WEEKS) == 0
    with pytest.raises(ValueError):
        deployment_frequency(5, 0)


@pytest.mark.parametrize(("per_week", "points"), [
    (7, 4), (6.99, 3), (1, 3), (0.99, 2), (ONCE_PER_MONTH_PER_WEEK, 2), (ONCE_PER_MONTH_PER_WEEK - 0.001, 1), (0, 1),
])
def test_frequency_cutoffs(per_week, points):
    assert frequency_points(per_week) == points


def test_twelve_releases_a_year_is_medium_and_eleven_is_low():
    assert frequency_points(deployment_frequency(12, WEEKS)) == 2
    assert frequency_points(deployment_frequency(11, WEEKS)) == 1


@pytest.mark.parametrize(("hours", "points"), [
    (23.9, 4), (24, 3), (167.9, 3), (168, 2), (719.9, 2), (720, 1),
])
def test_lead_time_cutoffs(hours, points):
    assert lead_time_points(hours) == points


@pytest.mark.parametrize(("rate", "points"), [
    (0, 4), (0.15, 4), (0.1501, 3), (0.30, 3), (0.45, 2), (0.4501, 1), (1, 1),
])
def test_failure_rate_cutoffs(rate, points):
    assert failure_rate_points(rate) == points


@pytest.mark.parametrize(("hours", "points"), [
    (0.99, 4), (1, 3), (23.9, 3), (24, 2), (167.9, 2), (168, 1),
])
def test_recovery_cutoffs(hours, points):
    assert recovery_points(hours) == points


def test_overall_is_the_median_rounded_down():
    assert overall_points([4, 3, 3, 1]) == 3  # exemplo do enunciado: High
    assert overall_points([4, 3, 2, 1]) == 2  # mediana 2,5 -> 2
    assert overall_points([4, 4, 3, 3]) == 3
    assert overall_points([4, None, 2, None]) == 3
    assert overall_points([None, None]) is None


def test_classify_reports_points_category_and_metrics_used():
    # 1/semana (High), lead time 2 h (Elite), CFR 20% (High), recuperacao 10 dias (Low): 4, 3, 3, 1 -> High
    result = classify(1.0, 2.0, 0.20, 240.0)
    assert (result["frequency"], result["lead_time"], result["failure_rate"], result["recovery"]) == (3, 4, 3, 1)
    assert result["overall"] == 3 and result["category"] == "High" and result["metrics_used"] == 4

    partial = classify(0.1, None, 0.5, None)
    assert partial["overall"] == 1 and partial["category"] == "Low" and partial["metrics_used"] == 2
    assert classify(None, None, None, None)["category"] == ""
