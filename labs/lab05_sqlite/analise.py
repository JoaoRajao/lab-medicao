"""Analise estatistica do Lab05: descritiva, atipicos, testes pareados, tamanho do efeito e poder (issue #122).

Le os dados versionados em ``labs/lab05_sqlite/data/raw/coleta_completa.csv`` (e ``piloto.csv``
para a simulacao de erro tipo I e poder com n = 30), aplica exatamente o plano registrado na
proposta (``docs/lab05/proposta.md``) e grava as tabelas em ``labs/lab05_sqlite/data/processed/``.

    python -m labs.lab05_sqlite.analise
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from labs.lab05_sqlite import coleta

SEED = coleta.SEED
ALPHA = 0.05
BOOTSTRAP_REPS = 10_000
SIM_REPS = 5_000
FATOR_ATIPICO = 3.0

BASE_DIR = Path(__file__).resolve().parent
RAW_COMPLETA = BASE_DIR / "data" / "raw" / "coleta_completa.csv"
RAW_PILOTO = BASE_DIR / "data" / "raw" / "piloto.csv"
SAIDA_DIR = BASE_DIR / "data" / "processed"

METRICAS = ("ops_por_s", "latencia_mediana_ms", "latencia_p95_ms", "duracao_s")
METRICAS_ATIPICOS = ("ops_por_s", "latencia_mediana_ms", "latencia_p95_ms")

# M6: durabilidade nominal segundo a documentacao oficial do SQLite (pragma.html / wal.html)
DURABILIDADE_M6: dict[tuple[str, str], str] = {
    ("DELETE", "FULL"): "Duravel",
    ("DELETE", "NORMAL"): "Duravel (risco minimo antes do commit)",
    ("WAL", "FULL"): "Duravel",
    ("WAL", "NORMAL"): "Nao duravel apos queda de energia",
}


@dataclass(frozen=True)
class Comparacao:
    codigo: str
    descricao: str
    carga: str
    tratamento_a: tuple[str, str]
    tratamento_b: tuple[str, str]
    cauda: str  # "greater", "less" ou "two-sided"
    confirmatoria: bool


COMPARACOES: tuple[Comparacao, ...] = (
    Comparacao(
        codigo="H-1",
        descricao="Escrita (synchronous=FULL): WAL > DELETE",
        carga="escrita",
        tratamento_a=("WAL", "FULL"),
        tratamento_b=("DELETE", "FULL"),
        cauda="greater",
        confirmatoria=True,
    ),
    Comparacao(
        codigo="H-2",
        descricao="Leitura avulsa (synchronous=FULL): WAL != DELETE",
        carga="leitura",
        tratamento_a=("WAL", "FULL"),
        tratamento_b=("DELETE", "FULL"),
        cauda="two-sided",
        confirmatoria=True,
    ),
    Comparacao(
        codigo="H-3",
        descricao="Escrita (journal=WAL): NORMAL > FULL",
        carga="escrita",
        tratamento_a=("WAL", "NORMAL"),
        tratamento_b=("WAL", "FULL"),
        cauda="greater",
        confirmatoria=True,
    ),
    Comparacao(
        codigo="Exp-1",
        descricao="Leitura em transacao unica (synchronous=FULL): WAL != DELETE",
        carga="leitura_transacao",
        tratamento_a=("WAL", "FULL"),
        tratamento_b=("DELETE", "FULL"),
        cauda="two-sided",
        confirmatoria=False,
    ),
    Comparacao(
        codigo="Exp-2",
        descricao="Escrita (journal=DELETE): NORMAL > FULL",
        carga="escrita",
        tratamento_a=("DELETE", "NORMAL"),
        tratamento_b=("DELETE", "FULL"),
        cauda="greater",
        confirmatoria=False,
    ),
)


def carregar_dados(caminho: Path = RAW_COMPLETA) -> pd.DataFrame:
    """Carrega o CSV de coleta e valida colunas obrigatorias."""
    df = pd.read_csv(caminho)
    faltantes = set(coleta.COLUNAS) - set(df.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes em {caminho}: {sorted(faltantes)}")
    return df


def estatistica_descritiva(
    df: pd.DataFrame,
    metricas: tuple[str, ...] = METRICAS,
) -> pd.DataFrame:
    """Calcula mediana, IQR, extremos e CV (M7) por carga, configuracao e metrica."""
    linhas = []
    grupos = df.groupby(["carga", "journal_mode", "synchronous"], sort=True)
    for (carga, journal, synchronous), grupo in grupos:
        durabilidade = DURABILIDADE_M6.get((journal, synchronous), "Desconhecida")
        for metrica in metricas:
            valores = grupo[metrica].to_numpy(dtype=float)
            q1, mediana, q3 = np.percentile(valores, [25.0, 50.0, 75.0])
            media = float(np.mean(valores))
            dp = float(np.std(valores, ddof=1)) if len(valores) > 1 else 0.0
            cv = dp / media if media != 0.0 else 0.0
            linhas.append({
                "carga": carga,
                "journal_mode": journal,
                "synchronous": synchronous,
                "configuracao": f"{journal}/{synchronous}",
                "durabilidade_m6": durabilidade,
                "metrica": metrica,
                "n": int(len(valores)),
                "mediana": float(mediana),
                "q1": float(q1),
                "q3": float(q3),
                "iqr": float(q3 - q1),
                "minimo": float(np.min(valores)),
                "maximo": float(np.max(valores)),
                "media": media,
                "desvio_padrao": dp,
                "cv": cv,
            })
    return pd.DataFrame(linhas)


def detectar_atipicos(
    df: pd.DataFrame,
    metricas: tuple[str, ...] = METRICAS_ATIPICOS,
    fator: float = FATOR_ATIPICO,
) -> pd.DataFrame:
    """Identifica medicoes alem de fator * IQR dos quartis por carga e configuracao."""
    colunas = [
        "bloco", "ordem", "carga", "journal_mode", "synchronous",
        "metrica", "valor", "q1", "q3", "iqr", "limite_inferior", "limite_superior",
    ]
    registros = []
    grupos = df.groupby(["carga", "journal_mode", "synchronous"], sort=True)
    for (carga, journal, synchronous), grupo in grupos:
        for metrica in metricas:
            valores = grupo[metrica].to_numpy(dtype=float)
            q1, q3 = np.percentile(valores, [25.0, 75.0])
            iqr = float(q3 - q1)
            lim_inf = float(q1 - fator * iqr)
            lim_sup = float(q3 + fator * iqr)
            mascara = (valores < lim_inf) | (valores > lim_sup)
            for _, row in grupo.loc[mascara].iterrows():
                registros.append({
                    "bloco": int(row["bloco"]),
                    "ordem": int(row["ordem"]),
                    "carga": carga,
                    "journal_mode": journal,
                    "synchronous": synchronous,
                    "metrica": metrica,
                    "valor": float(row[metrica]),
                    "q1": float(q1),
                    "q3": float(q3),
                    "iqr": iqr,
                    "limite_inferior": lim_inf,
                    "limite_superior": lim_sup,
                })
    return pd.DataFrame(registros, columns=colunas)


def razao_medianas_bootstrap(
    a: np.ndarray,
    b: np.ndarray,
    reps: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Calcula mediana(a)/mediana(b) e IC 95% via bootstrap pareado por bloco."""
    if len(a) != len(b) or len(a) == 0:
        raise ValueError("Vetores pareados devem ter o mesmo tamanho nao nulo.")
    med_b = float(np.median(b))
    if med_b == 0.0:
        raise ValueError("Mediana do denominador e zero.")
    razao_obs = float(np.median(a)) / med_b
    rng = np.random.default_rng(seed)
    n = len(a)
    indices = rng.integers(0, n, size=(reps, n))
    med_a_boot = np.median(a[indices], axis=1)
    med_b_boot = np.median(b[indices], axis=1)
    razoes = med_a_boot / med_b_boot
    ic_inf, ic_sup = np.percentile(razoes, [2.5, 97.5])
    return razao_obs, float(ic_inf), float(ic_sup)


def rank_bisserial_pareado(a: np.ndarray, b: np.ndarray) -> float:
    """Correlacao rank-bisserial pareada de Kerby (W+ - W-) / (W+ + W-)."""
    diffs = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    nao_nulos = diffs[diffs != 0.0]
    if len(nao_nulos) == 0:
        return 0.0
    postos = stats.rankdata(np.abs(nao_nulos))
    w_pos = float(np.sum(postos[nao_nulos > 0.0]))
    w_neg = float(np.sum(postos[nao_nulos < 0.0]))
    total = w_pos + w_neg
    return (w_pos - w_neg) / total if total > 0.0 else 0.0


def correcao_holm(p_valores: list[float] | np.ndarray) -> np.ndarray:
    """Ajusta p-valores pelo procedimento sequencial de Holm-Bonferroni."""
    p = np.asarray(p_valores, dtype=float)
    m = len(p)
    if m == 0:
        return p
    ordem = np.argsort(p)
    ajustados = np.empty(m, dtype=float)
    acumulado = 0.0
    for rank, idx in enumerate(ordem):
        candidato = (m - rank) * p[idx]
        acumulado = max(acumulado, candidato)
        ajustados[idx] = min(1.0, acumulado)
    return ajustados


def _extrair_pares_por_bloco(
    df: pd.DataFrame,
    carga: str,
    tratamento_a: tuple[str, str],
    tratamento_b: tuple[str, str],
    metrica: str = "ops_por_s",
) -> tuple[np.ndarray, np.ndarray]:
    sub = df[df["carga"] == carga]
    a = (
        sub[(sub["journal_mode"] == tratamento_a[0]) & (sub["synchronous"] == tratamento_a[1])]
        .set_index("bloco")[metrica]
        .sort_index()
    )
    b = (
        sub[(sub["journal_mode"] == tratamento_b[0]) & (sub["synchronous"] == tratamento_b[1])]
        .set_index("bloco")[metrica]
        .sort_index()
    )
    if not a.index.equals(b.index):
        raise ValueError(f"Blocos desalinhados para {carga}: {tratamento_a} vs {tratamento_b}")
    return a.to_numpy(dtype=float), b.to_numpy(dtype=float)


def executar_testes_hipoteses(
    df: pd.DataFrame,
    comparacoes: tuple[Comparacao, ...] = COMPARACOES,
    alpha: float = ALPHA,
    seed: int = SEED,
) -> pd.DataFrame:
    """Executa Wilcoxon pareado, Holm, t pareado (sensibilidade) e tamanho do efeito."""
    resultados = []
    for i, comp in enumerate(comparacoes):
        a, b = _extrair_pares_por_bloco(df, comp.carga, comp.tratamento_a, comp.tratamento_b)
        w_res = stats.wilcoxon(a, b, alternative=comp.cauda, zero_method="wilcox")
        t_res = stats.ttest_rel(a, b, alternative=comp.cauda)
        razao, ic_inf, ic_sup = razao_medianas_bootstrap(a, b, seed=seed + i)
        r_rb = rank_bisserial_pareado(a, b)
        med_a = float(np.median(a))
        med_b = float(np.median(b))
        resultados.append({
            "codigo": comp.codigo,
            "descricao": comp.descricao,
            "confirmatoria": comp.confirmatoria,
            "carga": comp.carga,
            "tratamento_a": f"{comp.tratamento_a[0]}/{comp.tratamento_a[1]}",
            "tratamento_b": f"{comp.tratamento_b[0]}/{comp.tratamento_b[1]}",
            "cauda": comp.cauda,
            "n_blocos": int(len(a)),
            "mediana_a": med_a,
            "mediana_b": med_b,
            "razao_medianas": razao,
            "variacao_pct": (razao - 1.0) * 100.0,
            "ic95_razao_inf": ic_inf,
            "ic95_razao_sup": ic_sup,
            "wilcoxon_stat": float(w_res.statistic),
            "p_wilcoxon": float(w_res.pvalue),
            "p_holm": np.nan,
            "rejeita_h0": False,
            "rank_bisserial": r_rb,
            "t_stat": float(t_res.statistic),
            "p_ttest": float(t_res.pvalue),
            "sensibilidade_t_coincide": bool((w_res.pvalue < alpha) == (t_res.pvalue < alpha)),
        })

    tabela = pd.DataFrame(resultados)
    mask_conf = tabela["confirmatoria"].to_numpy(dtype=bool)
    p_holm = correcao_holm(tabela.loc[mask_conf, "p_wilcoxon"].to_numpy(dtype=float))
    tabela.loc[mask_conf, "p_holm"] = p_holm
    tabela.loc[mask_conf, "rejeita_h0"] = p_holm < alpha
    tabela.loc[~mask_conf, "rejeita_h0"] = tabela.loc[~mask_conf, "p_wilcoxon"] < alpha
    return tabela


def simular_poder_piloto(
    piloto_df: pd.DataFrame,
    n_blocos: int = 30,
    reps: int = SIM_REPS,
    alpha: float = ALPHA,
    seed: int = SEED,
) -> pd.DataFrame:
    """Simula erro tipo I e poder do Wilcoxon pareado com n=30 usando a variabilidade do piloto."""
    rng = np.random.default_rng(seed)
    cenarios = (
        ("H-1", "escrita", ("WAL", "FULL"), ("DELETE", "FULL"), "greater"),
        ("H-2", "leitura", ("WAL", "FULL"), ("DELETE", "FULL"), "two-sided"),
        ("H-3", "escrita", ("WAL", "NORMAL"), ("WAL", "FULL"), "greater"),
    )
    linhas = []
    for codigo, carga, trat_a, trat_b, cauda in cenarios:
        a_pil, b_pil = _extrair_pares_por_bloco(piloto_df, carga, trat_a, trat_b)
        log_diffs = np.log(a_pil / b_pil)
        efeito_log = float(np.median(log_diffs))
        dp_log = float(np.std(log_diffs, ddof=1))

        # Sob H0 (sem diferenca em escala log), erro tipo I deve ficar proximo de alpha
        amostras_h0 = rng.normal(loc=0.0, scale=dp_log, size=(reps, n_blocos))
        p_h0 = stats.wilcoxon(amostras_h0, axis=1, alternative=cauda).pvalue
        erro_tipo_i = float(np.mean(p_h0 < alpha))

        # Sob H1 (efeito observado no piloto), estima o poder estatistico com n_blocos=30
        amostras_h1 = rng.normal(loc=efeito_log, scale=dp_log, size=(reps, n_blocos))
        p_h1 = stats.wilcoxon(amostras_h1, axis=1, alternative=cauda).pvalue
        poder_obs = float(np.mean(p_h1 < alpha))

        linhas.append({
            "hipotese": codigo,
            "carga": carga,
            "n_piloto": int(len(a_pil)),
            "n_blocos_planejado": n_blocos,
            "efeito_razao_piloto": float(np.exp(efeito_log)),
            "dp_log_razao_piloto": dp_log,
            "repeticoes": reps,
            "erro_tipo_i_simulado": erro_tipo_i,
            "poder_simulado": poder_obs,
        })
    return pd.DataFrame(linhas)


def executar_analise(
    caminho_completa: Path = RAW_COMPLETA,
    caminho_piloto: Path = RAW_PILOTO,
    saida_dir: Path = SAIDA_DIR,
) -> dict[str, pd.DataFrame]:
    """Executa toda a analise e salva as tabelas processadas em CSV e JSON."""
    saida_dir.mkdir(parents=True, exist_ok=True)
    df = carregar_dados(caminho_completa)
    piloto_df = carregar_dados(caminho_piloto)

    descritiva = estatistica_descritiva(df)
    atipicos = detectar_atipicos(df)
    testes = executar_testes_hipoteses(df)
    poder = simular_poder_piloto(piloto_df)

    descritiva.to_csv(saida_dir / "descritiva.csv", index=False, lineterminator="\n")
    atipicos.to_csv(saida_dir / "atipicos.csv", index=False, lineterminator="\n")
    testes.to_csv(saida_dir / "testes_hipoteses.csv", index=False, lineterminator="\n")
    poder.to_csv(saida_dir / "simulacao_poder.csv", index=False, lineterminator="\n")

    resumo = {
        "n_medicoes": int(len(df)),
        "n_blocos": int(df["bloco"].nunique()),
        "n_atipicos_3iqr": int(len(atipicos)),
        "alpha": ALPHA,
        "seed": SEED,
        "testes": testes.to_dict(orient="records"),
        "poder_piloto": poder.to_dict(orient="records"),
    }
    (saida_dir / "resumo.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "descritiva": descritiva,
        "atipicos": atipicos,
        "testes": testes,
        "poder": poder,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analise estatistica do Lab05 (SQLite)")
    parser.add_argument("--dados", type=Path, default=RAW_COMPLETA)
    parser.add_argument("--piloto", type=Path, default=RAW_PILOTO)
    parser.add_argument("--saida", type=Path, default=SAIDA_DIR)
    args = parser.parse_args()

    resultados = executar_analise(args.dados, args.piloto, args.saida)
    print(f"Descritiva: {len(resultados['descritiva'])} linhas")
    print(f"Atipicos (3xIQR): {len(resultados['atipicos'])}")
    print("\nTestes de hipotese:")
    cols = ["codigo", "razao_medianas", "p_wilcoxon", "p_holm", "rejeita_h0", "rank_bisserial", "p_ttest"]
    print(resultados["testes"][cols].to_string(index=False))
    print("\nSimulacao de poder (piloto -> n=30):")
    print(resultados["poder"][["hipotese", "erro_tipo_i_simulado", "poder_simulado"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
