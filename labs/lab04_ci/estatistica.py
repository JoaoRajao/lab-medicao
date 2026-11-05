"""Contas usadas pelos graficos G1 e G2 do dashboard (issue #98).

O cenario (#96) testa se a taxa de falha do CI passa da meta de 5%: H0 p <= 0,05 contra H1 p > 0,05,
unicaudal a direita, alfa = 0,05. Os dois testes do par P4 olham para o mesmo numero de falhas X em n
execucoes:

- teste Z: z = (X - n p0) / sqrt(n p0 (1 - p0)), comparado com a normal padrao;
- binomial exato: P(X >= x observado) sob Binomial(n, p0).

As distribuicoes sob H0 sao teoricas: nao dependem do gerador de simulacao da #97.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats

from labs.lab04_ci import simulacao

P0 = 0.05
ALPHA = 0.05
SEED = 42
# Mesmo caminho de ingest.CSV_PATH; sem importar ingest, o dashboard nao depende de duckdb/yaml no deploy.
CSV_PATH = Path(__file__).resolve().parent / "data" / "raw" / "ci_runs.csv"


@dataclass(frozen=True)
class Amostra:
    n: int
    falhas: int
    inicio: str
    fim: str
    repositorio: str

    @property
    def sucessos(self) -> int:
        return self.n - self.falhas

    @property
    def proporcao(self) -> float:
        return self.falhas / self.n


def carregar_amostra(path: Path = CSV_PATH) -> Amostra:
    with Path(path).open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"{path}: amostra vazia")
    datas = sorted(row["created_at"] for row in rows)
    return Amostra(n=len(rows), falhas=sum(row["conclusion"] == "failure" for row in rows),
                   inicio=datas[0], fim=datas[-1], repositorio=rows[0]["repository"])


def estatistica_z(falhas: int, n: int, p0: float = P0) -> float:
    return (falhas - n * p0) / math.sqrt(n * p0 * (1 - p0))


def p_valor_z(falhas: int, n: int, p0: float = P0) -> float:
    return float(stats.norm.sf(estatistica_z(falhas, n, p0)))


def p_valor_binomial(falhas: int, n: int, p0: float = P0) -> float:
    return float(stats.binom.sf(falhas - 1, n, p0))  # P(X >= falhas)


def z_critico(alpha: float = ALPHA) -> float:
    return float(stats.norm.isf(alpha))


def falhas_criticas_binomial(n: int, p0: float = P0, alpha: float = ALPHA) -> int:
    """Menor k com P(X >= k) <= alfa: o binomial rejeita H0 a partir de k falhas."""
    return int(next(k for k in range(n + 2) if stats.binom.sf(k - 1, n, p0) <= alpha))


def falhas_criticas_z(n: int, p0: float = P0, alpha: float = ALPHA) -> int:
    """Menor numero de falhas cujo z passa do valor critico."""
    return int(next(k for k in range(n + 1) if estatistica_z(k, n, p0) > z_critico(alpha)))


def erro_tipo_i_exato(k_critico: int, n: int, p0: float = P0) -> float:
    """Probabilidade real de rejeitar H0 quando p = p0, para a regra "rejeita se X >= k_critico"."""
    return float(stats.binom.sf(k_critico - 1, n, p0))


def amostra_simulada(n: int, p: float, seed: int = SEED) -> np.ndarray:
    """Uma amostra de n execucoes (1 = falha) com probabilidade de falha p.

    Utiliza o gerador reprodutivel do modulo simulacao (#97).
    """
    return simulacao.gerar_amostra(n, p, rng=seed)
