from __future__ import annotations

import argparse
import importlib
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Sequence

from labs.lab03_dora.config import Config, ConfigError, load_config
from shared.github_client import load_env_file
from shared.github_rest import GitHubAPIError, GitHubRestClient, ResponseCache

LAB_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAB_DIR.parents[1]
DEFAULT_CONFIG = LAB_DIR / "config.yaml"


@dataclass(frozen=True)
class Stage:
    name: str
    target: str  # "modulo:funcao", com assinatura run(ctx: Context) -> None
    issue: int


@dataclass
class Context:
    config: Config
    client: GitHubRestClient


STAGES: tuple[Stage, ...] = (
    Stage("selecao", "labs.lab03_dora.selecao:run", 60),
    Stage("releases", "labs.lab03_dora.releases:run", 61),
    Stage("workflow_runs", "labs.lab03_dora.workflow_runs:run", 62),
    Stage("cfr_b", "labs.lab03_dora.cfr_b:run", 72),
    Stage("dataset", "labs.lab03_dora.consolidacao:run", 66),
)


def resolve(stage: Stage) -> Callable[[Context], None] | None:
    """Funcao da etapa, ou None se o modulo/funcao ainda nao existir."""
    module_name, function_name = stage.target.split(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            return None
        raise
    return getattr(module, function_name, None)


def run_pipeline(
    context: Context,
    stages: Sequence[Stage] | None = None,
    only: Sequence[str] | None = None,
    log: Callable[[str], None] = print,
) -> int:
    selected = [stage for stage in (stages or STAGES) if not only or stage.name in only]
    context.config.output_dir.mkdir(parents=True, exist_ok=True)
    for stage in selected:
        function = resolve(stage)
        if function is None:
            log(f"Etapa '{stage.name}' ainda nao implementada (issue #{stage.issue}). Pipeline interrompido.")
            return 2
        log(f"Etapa '{stage.name}': iniciando.")
        function(context)
        log(f"Etapa '{stage.name}': concluida.")
    log(f"Pipeline concluido. Requisicoes feitas a API nesta execucao: {context.client.requests_made}.")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline do Lab03: mineracao de metricas DORA.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Arquivo YAML de configuracao.")
    parser.add_argument(
        "--etapa",
        action="append",
        choices=[stage.name for stage in STAGES],
        help="Roda so esta etapa (pode repetir). Sem a opcao, roda todas em ordem.",
    )
    parser.add_argument(
        "--repositorios",
        type=Path,
        help="CSV com a coluna `repository`: coleta so esses repositorios, sem a busca (ex.: replicacao com 30).",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        help="Pasta para os CSVs e o cache desta execucao (padrao: saida.dados e saida.cache do config).",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    client_factory: Callable[[str, Config], GitHubRestClient] | None = None,
    log: Callable[[str], None] = print,
) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        log(f"Configuracao invalida: {error}")
        return 1
    output, repositories = getattr(args, "saida", None), getattr(args, "repositorios", None)
    if output is not None:
        config = replace(config, output_dir=output, cache_dir=output / "cache")
    if repositories is not None:
        if not repositories.is_file():
            log(f"Lista de repositorios nao encontrada: {repositories}")
            return 1
        config = replace(config, repository_list=repositories)

    load_env_file(REPO_ROOT / ".env")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log("Defina a variavel de ambiente GITHUB_TOKEN (ou GITHUB_TOKEN=... no .env da raiz).")
        return 1

    factory = client_factory or (
        lambda tok, cfg: GitHubRestClient(
            tok, cache=ResponseCache(cfg.cache_dir), max_retries=cfg.max_retries, timeout=cfg.timeout, log=log
        )
    )
    client = factory(token, config)
    try:
        core = client.rate_limit().get("resources", {}).get("core", {})
    except GitHubAPIError as error:
        log(f"Nao foi possivel acessar a API do GitHub (HTTP {error.status}). Verifique o GITHUB_TOKEN.")
        return 1
    log(f"Cota da API: {core.get('remaining', '?')}/{core.get('limit', '?')} requisicoes restantes.")
    log(f"Janela: {config.window.start} a {config.window.end} ({config.window.weeks:.1f} semanas).")
    return run_pipeline(Context(config, client), only=args.etapa, log=log)
