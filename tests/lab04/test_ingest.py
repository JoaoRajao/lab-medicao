from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from labs.lab04_ci import ingest
from shared.warehouse import create_and_load_table, export_table


def make_run(index: int, *, conclusion: str = "success", **overrides: object) -> dict:
    run = {
        "id": 1000 + index,
        "run_attempt": 1,
        "workflow_id": ingest.WORKFLOW_ID,
        "head_sha": f"sha-{index}",
        "event": "push",
        "head_branch": "main",
        "status": "completed",
        "created_at": f"2026-11-01T00:{index:02d}:00Z",
        "conclusion": conclusion,
        "html_url": f"https://github.com/astral-sh/ruff/actions/runs/{1000 + index}",
    }
    run.update(overrides)
    return run


def test_selection_filters_before_counting_and_keeps_one_run_per_commit() -> None:
    runs = [make_run(i, conclusion="failure" if i < 5 else "success") for i in range(30)]
    runs += [
        make_run(40, event="pull_request"),
        make_run(41, head_branch="feature"),
        make_run(42, conclusion="cancelled"),
        make_run(43, status="in_progress"),
        make_run(44, created_at="2026-11-03T00:00:00Z"),
        make_run(45, head_sha="sha-29"),
    ]
    selected = ingest.select_runs(runs)
    assert len(selected) == 30
    assert len({row["head_sha"] for row in selected}) == 30
    assert sum(row["conclusion"] == "failure" for row in selected) == 5
    assert selected[0]["head_sha"] == "sha-29"


def test_csv_rejects_duplicate_commits(tmp_path: Path) -> None:
    rows = ingest.select_runs([make_run(i) for i in range(30)])
    rows[-1]["head_sha"] = rows[0]["head_sha"]
    path = tmp_path / "runs.csv"
    ingest.write_csv(rows, path)
    with pytest.raises(ValueError, match="Commits repetidos"):
        ingest.read_csv(path)


def test_versioned_sample_reconstructs_warehouse_and_parquet(tmp_path: Path) -> None:
    rows = ingest.read_csv()
    assert len(rows) == 30
    assert sum(row["conclusion"] == "failure" for row in rows) == 5
    warehouse = tmp_path / "warehouse.duckdb"
    parquet = tmp_path / "ci_runs.parquet"
    create_and_load_table("lab04_ci_runs", ingest.TABLE_COLUMNS, rows, duckdb_path=warehouse)
    export_table("lab04_ci_runs", duckdb_path=warehouse, parquet_path=parquet)
    with duckdb.connect(str(warehouse), read_only=True) as conn:
        assert conn.execute("select count(*) from lab04_ci_runs").fetchone()[0] == 30
    with duckdb.connect() as conn:
        assert conn.execute("select count(*) from read_parquet(?)", [str(parquet)]).fetchone()[0] == 30
        assert conn.execute("select count(*) from read_parquet(?) where conclusion = 'failure'", [str(parquet)]).fetchone()[0] == 5
