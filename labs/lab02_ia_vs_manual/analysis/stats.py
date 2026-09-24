from __future__ import annotations

import numpy as np
import pandas as pd

TREATMENTS = ["manual", "ai_assisted"]


def summarize(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Mediana, Q1, Q3, IQR e N por tratamento (nunca media/desvio: N pequeno e assimetria)."""
    rows = []
    for treatment in TREATMENTS:
        values = df.loc[df["treatment"] == treatment, column].dropna().to_numpy(dtype=float)
        if values.size == 0:
            continue
        q1, median, q3 = np.percentile(values, [25, 50, 75])
        rows.append(
            {"treatment": treatment, "n": values.size, "median": median, "q1": q1, "q3": q3, "iqr": q3 - q1}
        )
    return pd.DataFrame(rows)


def iqr_outliers(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Trials fora de [Q1 - 1,5*IQR, Q3 + 1,5*IQR] dentro de cada tratamento (regra do boxplot)."""
    flagged = []
    for treatment, group in df.groupby("treatment"):
        q1, q3 = np.percentile(group[column].dropna(), [25, 75])
        low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        flagged.append(group[(group[column] < low) | (group[column] > high)])
    return pd.concat(flagged) if flagged else df.iloc[0:0]


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Cliff's delta = P(a > b) - P(a < b), em [-1, 1]. Nao parametrico, robusto a N pequeno."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return float("nan")
    greater = (a[:, None] > b[None, :]).sum()
    less = (a[:, None] < b[None, :]).sum()
    return float((greater - less) / (a.size * b.size))


def cliffs_magnitude(delta: float) -> str:
    """Limiares de Romano et al. (2006): 0,147 / 0,33 / 0,474."""
    size = abs(delta)
    if np.isnan(size):
        return "indefinido"
    if size < 0.147:
        return "desprezivel"
    if size < 0.33:
        return "pequeno"
    if size < 0.474:
        return "medio"
    return "grande"


def effect_size(df: pd.DataFrame, column: str) -> tuple[float, str]:
    """Cliff's delta de ai_assisted contra manual (negativo = IA tem valores menores)."""
    ai = df.loc[df["treatment"] == "ai_assisted", column].dropna().to_numpy()
    manual = df.loc[df["treatment"] == "manual", column].dropna().to_numpy()
    delta = cliffs_delta(ai, manual)
    return delta, cliffs_magnitude(delta)
