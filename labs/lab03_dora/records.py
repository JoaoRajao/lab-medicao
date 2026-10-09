"""Entrada e saida tabular das etapas do Lab03."""

from __future__ import annotations

import csv
import os
from datetime import date, datetime, timezone
from pathlib import Path


def timestamp(value: str) -> datetime:
    """Converte datas da API para instantes UTC comparaveis."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def in_window(value: str | None, start: date, end: date) -> bool:
    return bool(value and start <= timestamp(value).date() <= end)


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
