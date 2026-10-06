from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from labs.lab03_dora.config import ConfigError, load_config

DEFAULT_CONFIG = Path("labs/lab03_dora/config.yaml")


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


VALID = """
janela:
  inicio: 2025-10-01
  fim: 2026-09-30
inclusao:
  min_releases: 5
  min_workflow_runs: 50
amostra:
  repositorios: 100
saida:
  dados: data
  cache: data/cache
api:
  max_tentativas: 5
  timeout_segundos: 30
"""


def test_loads_a_valid_configuration(tmp_path):
    config = load_config(write(tmp_path, VALID))

    assert config.window.start == date(2025, 10, 1)
    assert config.window.end == date(2026, 9, 30)
    assert config.window.days == 365
    assert round(config.window.weeks, 1) == 52.1
    assert (config.inclusion.min_releases, config.inclusion.min_workflow_runs) == (5, 50)
    assert config.target_repositories == 100
    assert config.output_dir == tmp_path / "data"
    assert config.cache_dir == tmp_path / "data/cache"


def test_defaults_apply_when_optional_sections_are_missing(tmp_path):
    config = load_config(write(tmp_path, "janela:\n  inicio: '2025-01-01'\n  fim: '2025-12-31'\n"))

    assert (config.inclusion.min_releases, config.inclusion.min_workflow_runs) == (5, 50)
    assert (config.max_retries, config.timeout, config.target_repositories) == (5, 30, 100)


def test_shipped_config_covers_the_12_months_before_the_lab():
    config = load_config(DEFAULT_CONFIG)

    assert (config.window.start, config.window.end) == (date(2025, 10, 1), date(2026, 9, 30))


def test_empty_window_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="nao preenchida"):
        load_config(write(tmp_path, "janela:\n  inicio:\n  fim:\n"))


@pytest.mark.parametrize(
    ("window", "message"),
    [
        ("inicio: 2025-10-01\n  fim: 2025-09-30", "posterior"),
        ("inicio: 2025-10-01\n  fim: 2026-03-31", "12 meses"),
        ("inicio: 01/10/2025\n  fim: 2026-09-30", "AAAA-MM-DD"),
    ],
)
def test_rejects_invalid_windows(tmp_path, window, message):
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, f"janela:\n  {window}\n"))


@pytest.mark.parametrize("value", ["0", "-1", "dois", "true"])
def test_rejects_non_positive_criteria(tmp_path, value):
    text = f"janela:\n  inicio: 2025-10-01\n  fim: 2026-09-30\ninclusao:\n  min_releases: {value}\n"
    with pytest.raises(ConfigError, match="inclusao.min_releases"):
        load_config(write(tmp_path, text))


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="nao encontrado"):
        load_config(tmp_path / "nao_existe.yaml")
