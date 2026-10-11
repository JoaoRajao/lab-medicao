"""Entrada e saida tabular das etapas do Lab03."""

from __future__ import annotations

import csv
import os
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator


def timestamp(value: str) -> datetime:
    """Converte datas da API para instantes UTC comparaveis."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def in_window(value: str | None, start: date, end: date) -> bool:
    return bool(value and start <= timestamp(value).date() <= end)


RUN_KEYS = ("id", "workflow_id", "event", "head_branch", "status", "conclusion", "created_at", "run_started_at",
            "updated_at")
RELEASE_KEYS = ("tag_name", "name", "draft", "prerelease", "created_at", "published_at")


def slim_runs(data: dict) -> dict:
    """Pagina de workflow runs so com os campos usados (cada run traz o repositorio e o commit inteiros)."""
    runs = [{key: run.get(key) for key in RUN_KEYS} for run in data.get("workflow_runs") or []]
    return {"total_count": data.get("total_count"), "workflow_runs": runs}


def slim_releases(items: list) -> list:
    """Pagina de releases sem o texto das notas, que pode passar de 30 MB por pagina."""
    return [{key: release.get(key) for key in RELEASE_KEYS} for release in items or []]


def months(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Fatia a janela em meses de calendario (o primeiro e o ultimo podem ser parciais)."""
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield max(start, date(year, month, 1)), min(end, date(year, month, monthrange(year, month)[1]))
        month = month % 12 + 1
        year += month == 1


def selected_repositories(output_dir: Path) -> list[tuple[str, str]]:
    path = output_dir / "repositories.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Amostra ausente: {path}. Rode --etapa selecao primeiro.")
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not {"repository", "default_branch"}.issubset(reader.fieldnames or []):
            raise ValueError(f"Amostra sem repository/default_branch: {path}")
        rows = [(row["repository"], row["default_branch"]) for row in reader]
    if not rows or any(not repo or not branch for repo, branch in rows):
        raise ValueError(f"Amostra vazia ou incompleta: {path}")
    return rows


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)
