from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from labs.lab03_dora import pipeline
from labs.lab03_dora.pipeline import Stage, main, resolve, run_pipeline
from shared.github_rest import GitHubAPIError

CONFIG = """
janela:
  inicio: 2025-10-01
  fim: 2026-09-30
"""
TOKEN = "ghp_nao_deve_aparecer_no_log"


class FakeClient:
    def __init__(self, error: GitHubAPIError | None = None) -> None:
        self.error = error
        self.requests_made = 0

    def rate_limit(self):
        if self.error:
            raise self.error
        return {"resources": {"core": {"remaining": 4999, "limit": 5000}}}


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG, encoding="utf-8")
    return path


@pytest.fixture
def fake_stages(monkeypatch):
    """Registra modulos de etapa falsos e devolve a ordem em que rodaram."""
    calls: list[str] = []
    stages = []
    for name in ("primeira", "segunda"):
        module = types.ModuleType(f"fake_stage_{name}")
        module.run = lambda ctx, name=name: calls.append(name)
        monkeypatch.setitem(sys.modules, module.__name__, module)
        stages.append(Stage(name, f"{module.__name__}:run", 0))
    monkeypatch.setattr(pipeline, "STAGES", tuple(stages))
    return calls


def run_main(config_path, monkeypatch, client=None, extra=()):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.setattr(pipeline, "load_env_file", lambda path: None)
    lines: list[str] = []
    code = main(["--config", str(config_path), *extra], client_factory=lambda tok, cfg: client or FakeClient(), log=lines.append)
    return code, lines


def test_runs_every_stage_in_order(config_path, monkeypatch, fake_stages):
    code, lines = run_main(config_path, monkeypatch)

    assert code == 0
    assert fake_stages == ["primeira", "segunda"]
    assert any("4999/5000" in line for line in lines)
    assert all(TOKEN not in line for line in lines)


def test_only_runs_the_selected_stage(config_path, monkeypatch, fake_stages):
    monkeypatch.setattr(pipeline, "parse_args", lambda argv: pipeline.argparse.Namespace(config=config_path, etapa=["segunda"]))

    code, _ = run_main(config_path, monkeypatch)

    assert code == 0
    assert fake_stages == ["segunda"]


def test_stops_at_a_stage_that_is_not_implemented_yet(config_path, tmp_path):
    from labs.lab03_dora.config import load_config

    lines: list[str] = []
    stages = (Stage("pendente", "labs.lab03_dora.modulo_que_nao_existe:run", 60),)
    code = run_pipeline(pipeline.Context(load_config(config_path), FakeClient()), stages=stages, log=lines.append)

    assert code == 2
    assert "issue #60" in lines[0]


def test_resolve_returns_none_for_missing_function_and_reraises_inner_import_errors(monkeypatch, tmp_path):
    module = types.ModuleType("fake_stage_sem_run")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    assert resolve(Stage("x", f"{module.__name__}:run", 0)) is None

    (tmp_path / "fake_stage_quebrado.py").write_text("import pacote_que_nao_existe_xyz\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(ModuleNotFoundError, match="pacote_que_nao_existe_xyz"):
        resolve(Stage("y", "fake_stage_quebrado:run", 0))


def test_default_registry_points_to_the_component_issues():
    assert [(s.name, s.issue) for s in pipeline.STAGES] == [("selecao", 60), ("releases", 61), ("workflow_runs", 62)]


def test_missing_token_is_reported(config_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(pipeline, "load_env_file", lambda path: None)
    lines: list[str] = []

    assert main(["--config", str(config_path)], log=lines.append) == 1
    assert "GITHUB_TOKEN" in lines[0]


def test_invalid_config_is_reported(tmp_path, monkeypatch):
    lines: list[str] = []
    assert main(["--config", str(tmp_path / "x.yaml")], log=lines.append) == 1
    assert "Configuracao invalida" in lines[0]


def test_invalid_token_is_reported(config_path, monkeypatch):
    client = FakeClient(error=GitHubAPIError(401, "https://api.github.com/rate_limit", "Bad credentials"))

    code, lines = run_main(config_path, monkeypatch, client=client)

    assert code == 1
    assert "HTTP 401" in lines[-1]
