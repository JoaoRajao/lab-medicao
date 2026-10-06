from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

MIN_WINDOW_DAYS = 360
MAX_WINDOW_DAYS = 370


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def weeks(self) -> float:
        return self.days / 7


@dataclass(frozen=True)
class Inclusion:
    min_releases: int
    min_workflow_runs: int


@dataclass(frozen=True)
class Config:
    window: Window
    inclusion: Inclusion
    target_repositories: int
    output_dir: Path
    cache_dir: Path
    max_retries: int
    timeout: int


def _date(section: dict[str, Any], key: str) -> date:
    value = section.get(key)
    if value in (None, ""):
        raise ConfigError(f"janela.{key} nao preenchida: informe a data no formato AAAA-MM-DD.")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ConfigError(f"janela.{key} invalida ({value!r}); use AAAA-MM-DD.") from error


def _positive_int(section: dict[str, Any], key: str, default: int, prefix: str) -> int:
    value = section.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(f"{prefix}.{key} deve ser um inteiro positivo (recebido {value!r}).")
    return value


def load_config(path: Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"arquivo de configuracao nao encontrado: {path}")
    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    window_raw = raw.get("janela") or {}
    window = Window(_date(window_raw, "inicio"), _date(window_raw, "fim"))
    if window.end <= window.start:
        raise ConfigError("janela.fim deve ser posterior a janela.inicio.")
    if not MIN_WINDOW_DAYS <= window.days <= MAX_WINDOW_DAYS:
        raise ConfigError(f"a janela deve ter 12 meses; a configurada tem {window.days} dias.")

    inclusion_raw = raw.get("inclusao") or {}
    sample_raw = raw.get("amostra") or {}
    output_raw = raw.get("saida") or {}
    api_raw = raw.get("api") or {}
    base = path.parent

    return Config(
        window=window,
        inclusion=Inclusion(
            min_releases=_positive_int(inclusion_raw, "min_releases", 5, "inclusao"),
            min_workflow_runs=_positive_int(inclusion_raw, "min_workflow_runs", 50, "inclusao"),
        ),
        target_repositories=_positive_int(sample_raw, "repositorios", 100, "amostra"),
        output_dir=base / output_raw.get("dados", "data"),
        cache_dir=base / output_raw.get("cache", "data/cache"),
        max_retries=_positive_int(api_raw, "max_tentativas", 5, "api"),
        timeout=_positive_int(api_raw, "timeout_segundos", 30, "api"),
    )
