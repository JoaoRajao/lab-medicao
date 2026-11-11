"""Resultados de Q1, Q2 e Q3 consumidos pelos graficos G3 e G4 (issue #101).

Contrato com as simulacoes (#99 e #100): `labs/lab04_ci/data/simulacao/resultados.csv`, uma linha por
situacao x teste x taxa de falha verdadeira, com as colunas de `COLUNAS`. O erro tipo I (Q1) e a linha com
`p_verdadeiro == p0`; o poder (Q2) sao as demais. Uma situacao adversa (Q3) e so outro valor de `situacao`.

Para dados Bernoulli independentes (`modelo == "bernoulli"`), a taxa de rejeicao tem valor exato pela
binomial: serve de referencia no dashboard e de conferencia da simulacao (margem de cerca de +-0,4 p.p.
com 10.000 repeticoes).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from labs.lab04_ci import estatistica as est

RESULTADOS_PATH = Path(__file__).resolve().parent / "data" / "simulacao" / "resultados.csv"
TESTES = ("Z", "Binomial")
MODELO_EXATO = "bernoulli"
COLUNAS = {
    "situacao": "Nome curto mostrado nos graficos, ex.: 'Base (n = 30)'.",
    "modelo": "Como os dados foram gerados; 'bernoulli' = execucoes independentes com a mesma p.",
    "n": "Execucoes por conjunto simulado.",
    "p0": "Meta de H0 (0,05).",
    "alpha": "Nivel de significancia (0,05).",
    "p_verdadeiro": "Taxa de falha usada para gerar os dados.",
    "efeito": "p_verdadeiro - p0, em proporcao (0 = H0 verdadeira).",
    "teste": "'Z' ou 'Binomial'.",
    "repeticoes": "Conjuntos simulados (10.000).",
    "rejeicoes": "Conjuntos com p-valor < alpha.",
    "taxa_rejeicao": "rejeicoes / repeticoes.",
    "seed": "Semente do numpy.random.default_rng.",
}
# Grade de efeitos registrada no README da S01: de H0 (0,05) ate 0,30, cobrindo a taxa real (~0,167).
P_GRADE = (0.05, 0.075, 0.10, 0.15, 0.20, 0.30)
SITUACAO_BASE = "Base (n = 30)"


def validar(df: pd.DataFrame) -> pd.DataFrame:
    """Confere o contrato e devolve as linhas ordenadas; erro claro se a simulacao gravou algo diferente."""
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        raise ValueError(f"resultados sem as colunas {faltando}")
    if not set(df["teste"]) <= set(TESTES):
        raise ValueError(f"teste deve ser um de {TESTES}: {sorted(set(df['teste']) - set(TESTES))}")
    if df.duplicated(["situacao", "teste", "p_verdadeiro"]).any():
        raise ValueError("linha repetida para a mesma situacao, teste e p_verdadeiro")
    if not np.allclose(df["taxa_rejeicao"], df["rejeicoes"] / df["repeticoes"]):
        raise ValueError("taxa_rejeicao diferente de rejeicoes / repeticoes")
    if not np.allclose(df["efeito"], df["p_verdadeiro"] - df["p0"]):
        raise ValueError("efeito diferente de p_verdadeiro - p0")
    sem_h0 = set(df["situacao"]) - set(df.loc[np.isclose(df["efeito"], 0), "situacao"])
    if sem_h0:
        raise ValueError(f"situacoes sem a linha de H0 verdadeira (erro tipo I): {sorted(sem_h0)}")
    ordem = {nome: i for i, nome in enumerate(dict.fromkeys(df["situacao"]))}  # situacoes na ordem do CSV
    return df.sort_values(["situacao", "teste", "p_verdadeiro"], key=lambda c: c.map(ordem) if c.name == "situacao" else c,
                          ignore_index=True)


def carregar(path: Path = RESULTADOS_PATH) -> pd.DataFrame | None:
    """Resultados versionados das simulacoes, ou None enquanto #99/#100 nao gravaram o arquivo."""
    if not Path(path).exists():
        return None
    return validar(pd.read_csv(path))


def salvar(df: pd.DataFrame, path: Path = RESULTADOS_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    validar(df)[list(COLUNAS)].to_csv(path, index=False)
    return path


def taxa_exata(teste: str, n: int, p: float, p0: float = est.P0, alpha: float = est.ALPHA) -> float:
    """P(rejeitar H0) quando X ~ Binomial(n, p), pela regra de rejeicao de cada teste."""
    k = est.falhas_criticas_z(n, p0, alpha) if teste == "Z" else est.falhas_criticas_binomial(n, p0, alpha)
    return est.erro_tipo_i_exato(k, n, p)


def exatos(simulados: pd.DataFrame | None = None, alpha: float = est.ALPHA) -> pd.DataFrame:
    """Taxas exatas para cada situacao Bernoulli dos resultados (ou para o cenario base, sem resultados)."""
    if simulados is None:
        situacoes = [(SITUACAO_BASE, 30, est.P0, P_GRADE)]
    else:
        bernoulli = simulados[simulados["modelo"] == MODELO_EXATO]
        situacoes = [(nome, int(g["n"].iloc[0]), float(g["p0"].iloc[0]), tuple(sorted(set(g["p_verdadeiro"]))))
                     for nome, g in bernoulli.groupby("situacao", sort=False)]
    linhas = [
        {"situacao": nome, "n": n, "p0": p0, "alpha": alpha, "p_verdadeiro": p, "efeito": p - p0, "teste": teste,
         "taxa_exata": taxa_exata(teste, n, p, p0, alpha)}
        for nome, n, p0, grade in situacoes for teste in TESTES for p in grade
    ]
    return pd.DataFrame(linhas)


def margem(taxa: float | pd.Series, repeticoes: int | pd.Series) -> float | pd.Series:
    """Meia largura do intervalo de 95% da proporcao estimada (1,96 * erro padrao)."""
    return 1.96 * np.sqrt(taxa * (1 - taxa) / repeticoes)


def erro_tipo_i(df: pd.DataFrame) -> pd.DataFrame:
    return df[np.isclose(df["efeito"], 0)].reset_index(drop=True)


def poder(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("efeito", kind="stable", ignore_index=True)
