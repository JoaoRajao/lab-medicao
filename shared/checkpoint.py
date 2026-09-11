from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.dates import parse_datetime


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Tipo nao serializavel em JSON: {type(value)!r}")


def load_checkpoint(path: Path, datetime_columns: list[str] = ()) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            for column in datetime_columns:
                record[column] = parse_datetime(record.get(column))
            records.append(record)
    return records


def append_checkpoint(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=_json_default, ensure_ascii=True))
        file.write("\n")
