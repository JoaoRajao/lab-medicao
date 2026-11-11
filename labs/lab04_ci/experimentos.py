"""Q1 e Q2: erro tipo I e poder dos testes do par P4 (issue #99)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from labs.lab04_ci import simulacao

REPETICOES = 10_000
N_BASE = 30
P_GRADE = (0.05, 0.075, 0.10, 0.15, 0.20, 0.30)
SITUACAO_BASE = "Base (n = 30)"
COLUNAS = (
    "situacao", "modelo", "n", "p0", "alpha", "p_verdadeiro", "efeito",
    "teste", "repeticoes", "rejeicoes", "taxa_rejeicao", "seed",
)
SAIDA = Path(__file__).resolve().parent / "data" / "simulacao" / "resultados.csv"


def gerar_resultados(seed: int = simulacao.SEED_PADRAO) -> pd.DataFrame:
    """Gera 10.000 contagens por efeito; ambos os testes recebem as mesmas contagens."""
    rng = np.random.default_rng(seed)
    linhas = []
    for p in P_GRADE:
        falhas = simulacao.gerar_contagens_binomiais(REPETICOES, N_BASE, p, rng=rng)
        _, p_z, _ = simulacao.simular_repeticoes_z(falhas, N_BASE)
        p_binomial, _ = simulacao.simular_repeticoes_binomial(falhas, N_BASE)
        for teste, p_valores in (("Z", p_z), ("Binomial", p_binomial)):
            rejeicoes = int(np.count_nonzero(p_valores < simulacao.ALPHA_PADRAO))
            linhas.append({
                "situacao": SITUACAO_BASE,
                "modelo": "bernoulli",
                "n": N_BASE,
                "p0": simulacao.P0_PADRAO,
                "alpha": simulacao.ALPHA_PADRAO,
                "p_verdadeiro": p,
                "efeito": round(p - simulacao.P0_PADRAO, 6),
                "teste": teste,
                "repeticoes": REPETICOES,
                "rejeicoes": rejeicoes,
                "taxa_rejeicao": rejeicoes / REPETICOES,
                "seed": seed,
            })
    return pd.DataFrame(linhas, columns=COLUNAS)


def main() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    gerar_resultados().to_csv(SAIDA, index=False, lineterminator="\n")
    print(f"Q1/Q2: {SAIDA} ({REPETICOES} repetições por efeito e teste)")


if __name__ == "__main__":
    main()
