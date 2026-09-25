from __future__ import annotations

from pathlib import Path

import pandas as pd

LAB_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = LAB_DIR / "data" / "raw"

TRIAL_FILES = {
    "P1": RAW_DIR / "trials_pedro.jsonl",
    "P2": RAW_DIR / "trials_joao.jsonl",
    "P3": RAW_DIR / "trials_salomao.jsonl",
}
SAMPLE_FILE = RAW_DIR / "trials_sample.jsonl"

KATAS = [
    "warehouse_batches",
    "route_reconciliation",
    "invoice_window",
    "sensor_anomaly",
    "support_queue",
    "dependency_unlock",
]
KATA_CODES = {kata: f"K{index}" for index, kata in enumerate(KATAS, start=1)}

# Ordem contrabalanceada de docs/lab02/experiment_design.md (K1..K6).
DESIGN = {
    "P1": ["manual", "ai_assisted", "manual", "ai_assisted", "manual", "ai_assisted"],
    "P2": ["ai_assisted", "manual", "ai_assisted", "manual", "ai_assisted", "manual"],
    "P3": ["manual", "ai_assisted", "ai_assisted", "manual", "manual", "ai_assisted"],
}
EXPECTED_TREATMENT = {(p, k): t for p, order in DESIGN.items() for k, t in zip(KATAS, order)}

# started_at/finished_at vem de duas chamadas independentes a datetime.now(); o tempo
# registrado e o inteiro truncado da diferenca, entao uma folga de 2s cobre so arredondamento.
CLOCK_TOLERANCE_SECONDS = 2


def load_trials(sample: bool = False) -> pd.DataFrame:
    """Une os JSONL de trials dos participantes (ou o sample sintetico) num DataFrame unico."""
    paths = [SAMPLE_FILE] if sample else [path for path in TRIAL_FILES.values() if path.exists()]
    if not paths:
        return pd.DataFrame()
    frames = [pd.read_json(path, lines=True) for path in paths]
    df = pd.concat(frames, ignore_index=True)
    df["kata_code"] = df["kata"].map(KATA_CODES)
    df["started_at"] = pd.to_datetime(df["started_at"], utc=True)
    df["finished_at"] = pd.to_datetime(df["finished_at"], utc=True)
    df["time_to_green_min"] = df["time_to_green_seconds"] / 60
    return df


def validate(df: pd.DataFrame, sample: bool = False) -> list[str]:
    """Devolve problemas de integridade que tornam os resultados preliminares ou invalidos."""
    problems: list[str] = []
    if sample:
        return ["dados SINTETICOS (trials_sample.jsonl) -- so para testar o pipeline"]

    present = set(df["participant"]) if not df.empty else set()
    for participant, path in TRIAL_FILES.items():
        if participant not in present:
            problems.append(f"{participant}: sem dados ({path.name} ausente ou vazio)")

    if df.empty:
        return problems

    for trial_id in df.loc[df["trial_id"].duplicated(), "trial_id"]:
        problems.append(f"trial_id duplicado: {trial_id}")

    for participant, group in df.groupby("participant"):
        if len(group) != len(KATAS):
            problems.append(f"{participant}: {len(group)} trials (esperado {len(KATAS)})")

    for row in df.itertuples():
        expected = EXPECTED_TREATMENT.get((row.participant, row.kata))
        if expected is not None and expected != row.treatment:
            problems.append(f"{row.trial_id}: tratamento {row.treatment}, desenho preve {expected}")

        elapsed = (row.finished_at - row.started_at).total_seconds()
        if elapsed < 0:
            problems.append(f"{row.trial_id}: finished_at anterior a started_at")
        elif not row.censored:
            if row.time_to_green_seconds == 0:
                problems.append(f"{row.trial_id}: time_to_green_seconds = 0 (tempo real nao medido)")
            elif abs(elapsed - row.time_to_green_seconds) > CLOCK_TOLERANCE_SECONDS:
                problems.append(
                    f"{row.trial_id}: time_to_green_seconds ({row.time_to_green_seconds}) "
                    f"diverge de finished_at - started_at ({elapsed:.0f}s)"
                )
    return problems
