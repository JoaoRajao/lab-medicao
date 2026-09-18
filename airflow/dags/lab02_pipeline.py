from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import Asset, dag, task

PROJECT_ROOT = Path(os.getenv("LAB_MEDICAO_PROJECT_ROOT", "/opt/airflow/project"))
DEFAULT_TRIALS_INPUT = (
    PROJECT_ROOT / "labs" / "lab02_ia_vs_manual" / "data" / "raw" / "trials_sample.jsonl"
)
TRIALS_PARQUET = (
    PROJECT_ROOT / "labs" / "lab02_ia_vs_manual" / "data" / "parquet" / "trials.parquet"
)
TRIALS_ASSET = Asset(f"file://{TRIALS_PARQUET}")
LAB02_DBT_SELECTION = ["staging.lab02", "gold.lab02"]

DEFAULT_ARGS = {
    "owner": "lab-medicao",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def run_project_command(command: list[str]) -> None:
    environment = os.environ.copy()
    environment["DBT_PROFILES_DIR"] = str(PROJECT_ROOT / "airflow" / "dbt")
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)


@dag(
    dag_id="lab02_ingestion_daily",
    description="Converte os registros dos trials do Lab 2 para DuckDB e Parquet.",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["lab02", "ingestion", "duckdb"],
)
def build_lab02_ingestion_dag():
    @task(
        outlets=[TRIALS_ASSET],
        execution_timeout=timedelta(minutes=10),
        pool="lab02_duckdb",
    )
    def ingest_trials() -> None:
        input_path = Path(os.getenv("LAB02_TRIALS_INPUT", str(DEFAULT_TRIALS_INPUT)))
        if not input_path.is_file():
            raise FileNotFoundError(f"Arquivo de trials nao encontrado: {input_path}")
        if input_path.suffix.lower() not in {".jsonl", ".csv"}:
            raise ValueError("LAB02_TRIALS_INPUT precisa apontar para um arquivo .jsonl ou .csv")

        run_project_command(
            [
                sys.executable,
                "-m",
                "labs.lab02_ia_vs_manual.scripts.ingest_trials_to_parquet",
                "--input",
                str(input_path),
                "--output",
                str(TRIALS_PARQUET),
            ]
        )

    ingest_trials()


@dag(
    dag_id="lab02_dbt_models",
    description="Materializa e testa as camadas staging e gold do Lab 2.",
    schedule=[TRIALS_ASSET],
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["lab02", "dbt", "duckdb"],
)
def build_lab02_dbt_dag():
    @task(execution_timeout=timedelta(minutes=10), pool="lab02_duckdb")
    def dbt_run() -> None:
        run_project_command(["dbt", "run", "--select", *LAB02_DBT_SELECTION])

    @task(execution_timeout=timedelta(minutes=10), pool="lab02_duckdb")
    def dbt_test() -> None:
        run_project_command(["dbt", "test", "--select", *LAB02_DBT_SELECTION])

    dbt_run() >> dbt_test()


build_lab02_ingestion_dag()
build_lab02_dbt_dag()
