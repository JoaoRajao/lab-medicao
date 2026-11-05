"""Modulo de simulacao e aplicacao dos testes do par P4 (issue #97).

Cenario:
- Taxa de falha do workflow de CI do Ruff excede a meta de 5%?
- Par P4: teste Z para uma proporcao x teste binomial exato.
- H0: p <= 0,05 contra H1: p > 0,05 (unicaudal a direita, alfa = 0,05).
- Amostra real de referencia: n = 30 execucoes, 5 falhas (p ≈ 0,167).

Este modulo fornece:
1. Gerador reprodutivel de amostras de Bernoulli com semente fixa (default_rng).
2. Aplicacao dos testes Z e Binomial a uma amostra com estatistica, p-valor,
   decisao para alfa = 0,05 e interpretacao contextualizada.
3. Funcoes vetorizadas reutilizaveis para simular 10.000 repeticoes (US #99).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import stats

P0_PADRAO = 0.05
ALPHA_PADRAO = 0.05
SEED_PADRAO = 42


def obter_rng(rng: np.random.Generator | int | None = None) -> np.random.Generator:
    """Retorna uma instancia de np.random.Generator a partir de semente ou instancia existente."""
    if isinstance(rng, np.random.Generator):
        return rng
    if rng is None:
        return np.random.default_rng(SEED_PADRAO)
    return np.random.default_rng(rng)


def gerar_amostra(n: int, p: float, rng: np.random.Generator | int | None = None) -> np.ndarray:
    """Gera uma amostra de n execucoes binarias (1 = falha, 0 = sucesso) com probabilidade p.

    Usa Bernoulli independente com np.random.default_rng.
    """
    if n <= 0:
        raise ValueError(f"Tamanho da amostra deve ser positivo: n={n}")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"Probabilidade p deve estar no intervalo [0, 1]: p={p}")

    gerador = obter_rng(rng)
    return (gerador.random(n) < p).astype(int)


def gerar_matriz_amostras(r: int, n: int, p: float, rng: np.random.Generator | int | None = None) -> np.ndarray:
    """Gera matriz (r, n) com r repeticoes de amostras de tamanho n."""
    if r <= 0 or n <= 0:
        raise ValueError(f"Dimensoes devem ser positivas: r={r}, n={n}")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"Probabilidade p deve estar no intervalo [0, 1]: p={p}")

    gerador = obter_rng(rng)
    return (gerador.random((r, n)) < p).astype(int)


def gerar_contagens_binomiais(r: int, n: int, p: float, rng: np.random.Generator | int | None = None) -> np.ndarray:
    """Gera vetor 1D de tamanho r com o numero de falhas X ~ Binomial(n, p) diretamente.

    Otimizado para grandes volumes de repeticoes (ex.: 10.000 simulacoes na S02).
    """
    if r <= 0 or n <= 0:
        raise ValueError(f"Dimensoes devem ser positivas: r={r}, n={n}")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"Probabilidade p deve estar no intervalo [0, 1]: p={p}")

    gerador = obter_rng(rng)
    return gerador.binomial(n, p, size=r)


@dataclass(frozen=True)
class ResultadoTeste:
    """Resultado da aplicacao de um teste de hipotese."""

    nome: str
    estatistica: float
    p_valor: float
    alpha: float
    rejeita_h0: bool
    decisao: str
    interpretacao: str


@dataclass(frozen=True)
class ComparacaoPar:
    """Comparacao simultanea do par P4 (Z x Binomial) aplicado ao mesmo conjunto."""

    n: int
    falhas: int
    proporcao: float
    p0: float
    alpha: float
    teste_z: ResultadoTeste
    binomial: ResultadoTeste

    @property
    def concordam(self) -> bool:
        return self.teste_z.rejeita_h0 == self.binomial.rejeita_h0


def aplicar_teste_z(falhas: int, n: int, p0: float = P0_PADRAO, alpha: float = ALPHA_PADRAO) -> ResultadoTeste:
    """Aplica o teste Z para uma proporcao unicaudal a direita sob variancia de H0.

    z = (X - n*p0) / sqrt(n*p0*(1 - p0))
    p-valor = P(Z >= z) na distribuicao normal padrao N(0, 1).
    """
    if n <= 0:
        raise ValueError(f"Tamanho da amostra deve ser positivo: n={n}")
    if not 0 <= falhas <= n:
        raise ValueError(f"Contagem de falhas fora do intervalo [0, n]: falhas={falhas}, n={n}")
    if not 0.0 < p0 < 1.0:
        raise ValueError(f"p0 de fronteira deve estar em (0, 1): p0={p0}")

    variancia_sob_h0 = n * p0 * (1.0 - p0)
    z = (falhas - n * p0) / math.sqrt(variancia_sob_h0)
    p_val = float(stats.norm.sf(z))
    rejeita = p_val <= alpha
    decisao = "Rejeita H₀" if rejeita else "Não rejeita H₀"

    if rejeita:
        interp = (
            f"O teste Z rejeita H₀ (z = {z:.3f}, p = {p_val:.4f} <= {alpha:.2f}): há evidência "
            f"estatística de que a taxa de falha ({falhas}/{n} = {falhas / n:.1%}) supera a meta de {p0:.1%}."
        )
    else:
        interp = (
            f"O teste Z não rejeita H₀ (z = {z:.3f}, p = {p_val:.4f} > {alpha:.2f}): não há evidência "
            f"suficiente para afirmar que a taxa de falha ({falhas}/{n} = {falhas / n:.1%}) excede a meta de {p0:.1%}."
        )

    return ResultadoTeste(
        nome="Teste Z para uma proporção",
        estatistica=z,
        p_valor=p_val,
        alpha=alpha,
        rejeita_h0=rejeita,
        decisao=decisao,
        interpretacao=interp,
    )


def aplicar_teste_binomial(falhas: int, n: int, p0: float = P0_PADRAO, alpha: float = ALPHA_PADRAO) -> ResultadoTeste:
    """Aplica o teste binomial exato unicaudal a direita sob X ~ Binomial(n, p0).

    p-valor = P(X >= falhas) = sf(falhas - 1, n, p0).
    """
    if n <= 0:
        raise ValueError(f"Tamanho da amostra deve ser positivo: n={n}")
    if not 0 <= falhas <= n:
        raise ValueError(f"Contagem de falhas fora do intervalo [0, n]: falhas={falhas}, n={n}")
    if not 0.0 < p0 < 1.0:
        raise ValueError(f"p0 de fronteira deve estar em (0, 1): p0={p0}")

    p_val = float(stats.binom.sf(falhas - 1, n, p0)) if falhas > 0 else 1.0
    rejeita = p_val <= alpha
    decisao = "Rejeita H₀" if rejeita else "Não rejeita H₀"

    if rejeita:
        interp = (
            f"O teste Binomial exato rejeita H₀ (k = {falhas}, p = {p_val:.4f} <= {alpha:.2f}): há evidência "
            f"estatística de que a probabilidade de falha ({falhas}/{n} = {falhas / n:.1%}) é superior a {p0:.1%}."
        )
    else:
        interp = (
            f"O teste Binomial exato não rejeita H₀ (k = {falhas}, p = {p_val:.4f} > {alpha:.2f}): a probabilidade "
            f"exata de observar {falhas} ou mais falhas sob H₀ é {p_val:.1%}, sem evidência de quebra da meta de {p0:.1%}."
        )

    return ResultadoTeste(
        nome="Teste binomial exato",
        estatistica=float(falhas),
        p_valor=p_val,
        alpha=alpha,
        rejeita_h0=rejeita,
        decisao=decisao,
        interpretacao=interp,
    )


def comparar_testes(
    amostra_ou_falhas: Sequence[int] | np.ndarray | int,
    n: int | None = None,
    p0: float = P0_PADRAO,
    alpha: float = ALPHA_PADRAO,
) -> ComparacaoPar:
    """Aplica os dois testes escolhidos ao mesmo conjunto de dados e compara as decisoes."""
    if isinstance(amostra_ou_falhas, (int, np.integer)):
        if n is None:
            raise ValueError("Ao informar o numero de falhas diretamente, o tamanho n deve ser fornecido.")
        falhas = int(amostra_ou_falhas)
        tamanho = int(n)
    else:
        arr = np.asarray(amostra_ou_falhas, dtype=int)
        tamanho = len(arr)
        falhas = int(np.sum(arr == 1))

    res_z = aplicar_teste_z(falhas, tamanho, p0=p0, alpha=alpha)
    res_b = aplicar_teste_binomial(falhas, tamanho, p0=p0, alpha=alpha)

    return ComparacaoPar(
        n=tamanho,
        falhas=falhas,
        proporcao=falhas / tamanho,
        p0=p0,
        alpha=alpha,
        teste_z=res_z,
        binomial=res_b,
    )


# --- Funcoes vetorizadas reutilizaveis para a S02 (10.000 repeticoes) ---


def simular_repeticoes_z(
    falhas_arr: np.ndarray,
    n: int,
    p0: float = P0_PADRAO,
    alpha: float = ALPHA_PADRAO,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calcula estatistica z, p-valores e rejeicoes para um vetor de contagens de falhas (vetorizado).

    Retorna: (estatisticas_z, p_valores, rejeicoes_bool).
    """
    falhas = np.asarray(falhas_arr, dtype=float)
    desvio = math.sqrt(n * p0 * (1.0 - p0))
    z = (falhas - n * p0) / desvio
    p_valores = stats.norm.sf(z)
    rejeicoes = p_valores <= alpha
    return z, p_valores, rejeicoes


def simular_repeticoes_binomial(
    falhas_arr: np.ndarray,
    n: int,
    p0: float = P0_PADRAO,
    alpha: float = ALPHA_PADRAO,
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula p-valores exatos e rejeicoes para um vetor de contagens de falhas (vetorizado).

    Retorna: (p_valores, rejeicoes_bool).
    """
    falhas = np.asarray(falhas_arr, dtype=int)
    # sf(k - 1, n, p0) equivale a P(X >= k)
    p_valores = stats.binom.sf(falhas - 1, n, p0)
    # Correcao para contagem zero: P(X >= 0) = 1.0
    p_valores = np.where(falhas <= 0, 1.0, p_valores)
    rejeicoes = p_valores <= alpha
    return p_valores, rejeicoes


def demonstracao_interpretada() -> None:
    """Executa e imprime a comparacao dos testes para conjuntos sob H0 e sob efeito."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 80)
    print("LAB04 — SIMULAÇÃO E APLICAÇÃO DOS TESTES DO PAR P4 (ISSUE #97)")
    print("=" * 80)

    cenarios = [
        ("Cenário 1: Sob H₀ (sem efeito)", 30, 0.05, 42),
        ("Cenário 2: Sob efeito real observado no Ruff", 30, 5 / 30, 42),
        ("Cenário 3: Situação adversa / amostra pequena com efeito", 10, 0.20, 42),
    ]

    for titulo, n, p, seed in cenarios:
        print(f"\n>>> {titulo} (n = {n}, p = {p:.3f}, seed = {seed})")
        amostra = gerar_amostra(n, p, rng=seed)
        comp = comparar_testes(amostra, p0=P0_PADRAO, alpha=ALPHA_PADRAO)

        print(f"Amostra gerada: {amostra.tolist()}")
        print(f"Falhas observadas: {comp.falhas}/{comp.n} ({comp.proporcao:.1%}) | Meta p₀: {comp.p0:.1%}")
        print("-" * 80)
        print(f"1. Teste Z: estatística z = {comp.teste_z.estatistica:.3f} | p-valor = {comp.teste_z.p_valor:.4f} "
              f"| Decisão (α=0.05): {comp.teste_z.decisao}")
        print(f"   Interpretação: {comp.teste_z.interpretacao}")
        print(f"2. Binomial: estatística k = {int(comp.binomial.estatistica)} | p-valor = {comp.binomial.p_valor:.4f} "
              f"| Decisão (α=0.05): {comp.binomial.decisao}")
        print(f"   Interpretação: {comp.binomial.interpretacao}")
        print(f"Concordância entre os testes: {'SIM (ambos convergem na decisão)' if comp.concordam else 'NÃO (divergem na fronteira)'}")
    print("=" * 80)


if __name__ == "__main__":
    demonstracao_interpretada()
