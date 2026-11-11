"""Textos do dashboard, montados a partir dos dados para nao ficarem desatualizados (issues #98 e #101)."""

from __future__ import annotations

import pandas as pd

from labs.lab04_ci import estatistica as est
from labs.lab04_ci import resultados as res
from labs.lab04_ci.graficos import _taxas, br

CURTO = {"Z": "Z", "Binomial": "binomial"}


def pct(valor: float, casas: int = 1) -> str:
    return br(100 * valor, casas) + "%"


def pergunta(a: est.Amostra) -> str:
    return f"A taxa de falha do workflow de CI do `{a.repositorio}` passa da meta de **5%**?"


def hipoteses() -> list[tuple[str, str]]:
    return [
        ("H₀", "A probabilidade de uma execução falhar é no máximo 5% (p ≤ 0,05)."),
        ("H₁", "A probabilidade de falha é maior que 5% (p > 0,05)."),
    ]


def desenho() -> str:
    return ("Os dois testes são **unicaudais à direita**, com α = 0,05: só interessa saber se a meta foi "
            "**ultrapassada**. Par P4: **teste Z para uma proporção** × **binomial exato**.")


def fonte(a: est.Amostra) -> str:
    return (f"**{a.n} execuções** do workflow `CI` disparadas por `push` em `main`, uma por commit, de "
            f"{a.inicio[:10]} a {a.fim[:10]}, coletadas da API do GitHub. Cada linha de "
            f"`labs/lab04_ci/data/raw/ci_runs.csv` traz o link da execução, para auditoria.")


def expectativa(a: est.Amostra) -> str:
    return (f"Registrada antes de simular: o **binomial exato** deve controlar melhor o erro tipo I, porque sob H₀ "
            f"esperamos só {br(a.n * est.P0, 1)} falhas em {a.n} execuções, pouco para a aproximação normal do Z.")


def g1(a: est.Amostra) -> str:
    return (
        f"Cada execução é binária: {a.sucessos} sucessos e {a.falhas} falhas nos dados reais, sem outliers "
        f"numéricos, mas com a massa concentrada em zero. A simulação gera {a.n} execuções independentes de "
        f"Bernoulli com semente fixa ({est.SEED}): com p = 0,05, o valor de H₀, e com p = {br(a.proporcao)}, a "
        f"taxa observada, que é o limite superior da faixa de efeitos das próximas simulações. Sob H₀, uma amostra "
        f"de {a.n} execuções tem em média {br(a.n * est.P0, 1)} falhas; as {a.falhas} falhas reais ficam bem acima disso."
    )


def g2(a: est.Amostra) -> str:
    k_z, k_b = est.falhas_criticas_z(a.n), est.falhas_criticas_binomial(a.n)
    alfa_z, alfa_b = est.erro_tipo_i_exato(k_z, a.n), est.erro_tipo_i_exato(k_b, a.n)
    p_z, p_b = est.p_valor_z(a.falhas, a.n), est.p_valor_binomial(a.falhas, a.n)
    return (
        f"O **Z** padroniza a proporção observada e a compara com a normal; o **binomial** usa a distribuição exata "
        f"do número de falhas sob H₀. A região de rejeição fica só à direita porque H₁ é p > 0,05. Como X é discreto, "
        f"o Z rejeita a partir de {k_z} falhas, o que sob H₀ acontece com probabilidade {pct(alfa_z)} (acima de 5%: "
        f"tende a ser **liberal**), e o binomial a partir de {k_b}, com probabilidade {pct(alfa_b)} (**conservador**). "
        f"O p-valor do exemplo é a chance de ver {a.falhas} ou mais falhas em {a.n} execuções **se a taxa fosse 5%**: "
        f"{br(p_b, 4)} pelo binomial e {br(p_z, 4)} pelo Z; não é a probabilidade de H₀ ser verdadeira."
    )


def comparacao(a: est.Amostra) -> list[dict[str, str]]:
    """Linhas da tabela que acompanha o G2, uma por teste."""
    k_z, k_b = est.falhas_criticas_z(a.n), est.falhas_criticas_binomial(a.n)
    return [
        {"Teste": "Z para uma proporção", "O que compara": "proporção padronizada × N(0, 1)",
         "Rejeita H₀ a partir de": f"{k_z} falhas", "Erro tipo I real": pct(est.erro_tipo_i_exato(k_z, a.n)),
         f"p-valor ({a.falhas} falhas)": br(est.p_valor_z(a.falhas, a.n), 4)},
        {"Teste": "Binomial exato", "O que compara": "contagem de falhas × Binomial(n, p₀)",
         "Rejeita H₀ a partir de": f"{k_b} falhas", "Erro tipo I real": pct(est.erro_tipo_i_exato(k_b, a.n)),
         f"p-valor ({a.falhas} falhas)": br(est.p_valor_binomial(a.falhas, a.n), 4)},
    ]


def classificar(taxa: float, margem: float, alpha: float = est.ALPHA) -> str:
    """Liberal/conservador so quando a diferenca para alfa passa da margem de Monte Carlo (ou de 0,5 p.p. no exato)."""
    folga = margem if margem == margem and margem > 0 else 0.005  # margem NaN = valor exato
    if taxa - folga > alpha:
        return "liberal"
    if taxa + folga < alpha:
        return "conservador"
    return "perto de 5%"


def origem(simulados: pd.DataFrame | None) -> str:
    if simulados is None:
        return "valores exatos da binomial, até as simulações de #99/#100 serem gravadas"
    r = int(simulados["repeticoes"].iloc[0])
    return f"{r:,}".replace(",", ".") + f" conjuntos simulados por ponto, semente {int(simulados['seed'].iloc[0])}"


def g3(simulados: pd.DataFrame | None, exatos: pd.DataFrame) -> str:
    df = res.erro_tipo_i(_taxas(simulados, exatos))
    partes, desvios = [], {}
    for situacao, g in df.groupby("situacao", sort=False):
        z, b = (g[g["teste"] == teste].iloc[0] for teste in ("Z", "Binomial"))
        partes.append(f"{situacao}: Z {pct(z['taxa'])} e binomial {pct(b['taxa'])}")
        for t in (z, b):
            tipo = classificar(t["taxa"], t["margem"], t["alpha"])
            if tipo != "perto de 5%":
                desvios.setdefault((t["teste"], tipo), []).append(situacao)
    resumo = "; ".join(f"o {CURTO[teste]} ficou **{tipo}** em {' e '.join(sits)}" for (teste, tipo), sits in desvios.items())
    return (
        f"Cada barra é a fração de conjuntos em que o teste rejeitou H₀ sendo H₀ verdadeira (p = 5%), com "
        f"{origem(simulados)}; o ideal é ficar na linha de 5%. Resultado: {'; '.join(partes)}. "
        + (f"Fora de 5%: {resumo}. " if resumo else "Os dois testes ficaram perto de 5% em todas as situações. ")
        + "Como o número de falhas é inteiro, nenhum teste consegue exatamente 5%: o Z confia numa normal que "
        "subestima a cauda direita quando n·p₀ é pequeno, e o binomial escolhe o corte que nunca passa de 5%."
    )


def _primeiro_80(g: pd.DataFrame) -> str:
    acima = g[g["taxa"] >= 0.8]
    return f"+{br(100 * acima['efeito'].iloc[0], 1)} p.p." if len(acima) else "não chega a 80% na grade"


def g4(simulados: pd.DataFrame | None, exatos: pd.DataFrame, efeito_observado: float) -> str:
    df = res.poder(_taxas(simulados, exatos))
    frases = [f"Cada curva mostra em que fração dos conjuntos o teste rejeita H₀ conforme a taxa verdadeira se afasta "
              f"de 5% ({origem(simulados)}); a curva mais alta tem mais poder"]
    for situacao, g in df.groupby("situacao", sort=False):
        z, b = g[g["teste"] == "Z"], g[g["teste"] == "Binomial"]
        alvo = (z["efeito"] - efeito_observado).abs().idxmin()
        efeito = z.loc[alvo, "efeito"]
        pz, pb = z.loc[alvo, "taxa"], b[b["efeito"] == efeito]["taxa"].iloc[0]
        frases.append(f"{situacao}: com +{br(100 * efeito, 1)} p.p., perto do efeito do Ruff, o Z rejeita em {pct(pz)} "
                      f"e o binomial em {pct(pb)}; 80% de poder vem em {_primeiro_80(z)} no Z e {_primeiro_80(b)} no "
                      f"binomial")
    base = df[df["situacao"] == df["situacao"].iloc[0]]
    gap = (base[base["teste"] == "Z"].set_index("efeito")["taxa"] - base[base["teste"] == "Binomial"].set_index("efeito")["taxa"])
    frases.append(f"A vantagem do Z vem do mesmo corte mais baixo que o deixa liberal no G3: ele detecta mais porque também "
                  f"rejeita mais sem efeito; em {base['situacao'].iloc[0]}, a diferença é maior em +{br(100 * gap.idxmax(), 1)} "
                  f"p.p. ({br(100 * gap.max(), 1)} pontos) e cai para {br(100 * gap.iloc[-1], 1)} pontos em "
                  f"+{br(100 * gap.index[-1], 1)} p.p., quando os dois quase sempre rejeitam")
    return ". ".join(frases[:4]) + "."
