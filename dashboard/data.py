"""Leitura isolada dos snapshots gold publicados."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from shared.publish_gold import DEFAULT_OUTPUT, GOLD_TABLES


def available_labs(root: Path = DEFAULT_OUTPUT) -> list[str]:
    return [lab for lab, tables in GOLD_TABLES.items()
            if all((root / lab / f"{table}.parquet").is_file() for table in tables)]


def table_path(lab: str, table: str, root: Path = DEFAULT_OUTPUT) -> Path:
    if lab not in GOLD_TABLES or table not in GOLD_TABLES[lab]:
        raise ValueError(f"Tabela nao publicada: {lab}/{table}")
    return root / lab / f"{table}.parquet"


def read_gold(lab: str, table: str, root: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    path = table_path(lab, table, root)
    if not path.is_file():
        raise FileNotFoundError(path)
    with duckdb.connect(":memory:") as conn:
        return conn.execute("select * from read_parquet(?)", [str(path)]).df()
