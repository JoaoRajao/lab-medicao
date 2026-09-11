from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse.duckdb"


def create_and_load_table(
    table_name: str,
    columns: list[tuple[str, str]],
    records: list[dict[str, Any]],
    duckdb_path: Path = DEFAULT_WAREHOUSE_PATH,
) -> None:
    """Cria (substituindo) uma tabela no warehouse compartilhado e insere os registros.

    `columns` e uma lista de pares (nome, tipo_sql). Sem conhecimento de nenhum
    tema/lab -- qualquer lab pode chamar isso com seu proprio schema.
    """
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    column_names = [name for name, _ in columns]
    columns_sql = ", ".join(f"{name} {sql_type}" for name, sql_type in columns)

    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"drop table if exists {table_name}")
        conn.execute(f"create table {table_name} ({columns_sql})")
        placeholders = ", ".join(["?"] * len(column_names))
        conn.executemany(
            f"insert into {table_name} values ({placeholders})",
            [[record.get(column) for column in column_names] for record in records],
        )


def export_table(
    table_name: str,
    duckdb_path: Path = DEFAULT_WAREHOUSE_PATH,
    parquet_path: Path | None = None,
    csv_path: Path | None = None,
) -> None:
    """Copia uma tabela ja existente no warehouse para Parquet e/ou CSV."""
    with duckdb.connect(str(duckdb_path)) as conn:
        if parquet_path is not None:
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            escaped = str(parquet_path).replace("'", "''")
            conn.execute(f"copy {table_name} to '{escaped}' (format parquet, compression zstd)")
        if csv_path is not None:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            escaped = str(csv_path).replace("'", "''")
            conn.execute(f"copy {table_name} to '{escaped}' (format csv, header)")


def read_table(
    table_name: str,
    columns: list[str],
    duckdb_path: Path = DEFAULT_WAREHOUSE_PATH,
) -> list[dict[str, Any]]:
    """Le uma tabela ja existente no warehouse, retornando lista de dicts."""
    if not duckdb_path.exists():
        raise RuntimeError(f"Warehouse nao encontrado em {duckdb_path}.")
    with duckdb.connect(str(duckdb_path), read_only=True) as conn:
        columns_sql = ", ".join(columns)
        rows = conn.execute(f"select {columns_sql} from {table_name}").fetchall()
    return [dict(zip(columns, row)) for row in rows]
