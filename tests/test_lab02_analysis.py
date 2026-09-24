from __future__ import annotations

import numpy as np
import pandas as pd

from labs.lab02_ia_vs_manual.analysis import data
from labs.lab02_ia_vs_manual.analysis.stats import cliffs_delta, cliffs_magnitude, iqr_outliers, summarize


def make_trial(participant: str, kata: str, treatment: str, seconds: int = 300, **overrides) -> dict:
    started = pd.Timestamp("2026-09-18T10:00:00.250000", tz="UTC")
    row = {
        "trial_id": f"{participant}-{kata}-{treatment}",
        "participant": participant,
        "kata": kata,
        "treatment": treatment,
        "censored": False,
        "time_to_green_seconds": seconds,
        "started_at": started,
        "finished_at": started + pd.Timedelta(seconds=seconds, milliseconds=600),
    }
    return {**row, **overrides}


def full_participant(participant: str) -> list[dict]:
    return [make_trial(participant, kata, EXPECTED) for kata, EXPECTED in
            zip(data.KATAS, data.DESIGN[participant])]


def test_cliffs_delta_extremes_and_magnitude() -> None:
    assert cliffs_delta(np.array([1, 2, 3]), np.array([4, 5, 6])) == -1.0
    assert cliffs_delta(np.array([4, 5, 6]), np.array([1, 2, 3])) == 1.0
    assert cliffs_delta(np.array([1, 2]), np.array([1, 2])) == 0.0
    assert cliffs_magnitude(-1.0) == "grande"
    assert cliffs_magnitude(0.1) == "desprezivel"


def test_summarize_uses_median_and_quartiles() -> None:
    df = pd.DataFrame({"treatment": ["manual"] * 5, "value": [1, 2, 3, 4, 100]})
    row = summarize(df, "value").iloc[0]
    assert (row["median"], row["q1"], row["q3"], row["n"]) == (3, 2, 4, 5)


def test_iqr_outliers_flags_extreme_trial() -> None:
    df = pd.DataFrame({"treatment": ["manual"] * 6, "value": [10, 11, 12, 11, 10, 200]})
    assert iqr_outliers(df, "value")["value"].tolist() == [200]


def test_validate_accepts_complete_consistent_data() -> None:
    df = pd.DataFrame(full_participant("P1") + full_participant("P2") + full_participant("P3"))
    assert data.validate(df) == []


def test_validate_flags_missing_participant_zero_time_and_wrong_treatment() -> None:
    rows = full_participant("P1")
    rows[0] = make_trial("P1", data.KATAS[0], "manual", seconds=0)
    rows[1] = make_trial("P1", data.KATAS[1], "manual")
    problems = data.validate(pd.DataFrame(rows))
    assert any("P2: sem dados" in p for p in problems)
    assert any("time_to_green_seconds = 0" in p for p in problems)
    assert any("desenho preve ai_assisted" in p for p in problems)


def test_validate_flags_elapsed_time_mismatch() -> None:
    rows = full_participant("P1")
    rows[0]["time_to_green_seconds"] = 10
    assert any("diverge" in p for p in data.validate(pd.DataFrame(rows)))


def test_sample_loads_and_is_marked_synthetic() -> None:
    df = data.load_trials(sample=True)
    assert len(df) == 18
    assert "SINTETICOS" in data.validate(df, sample=True)[0]
