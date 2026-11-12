"""Textos do dashboard, montados a partir dos dados para nao ficarem desatualizados (issues #98 e #101)."""

from __future__ import annotations

from datetime import datetime

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


def pp(efeito: float) -> str:
    """Efeito em pontos percentuais, sem casa decimal quando e inteiro: +10 p.p., +2,5 p.p."""
    valor = 100 * efeito
    return f"+{br(valor, 0 if abs(valor - round(valor)) < 1e-9 else 1)} p.p."


def _bloco(mostra: str, itens: list[str], conclusao: str, rodape: str) -> str:
    """Formato comum dos textos de leitura: o que mostra, numeros em lista, conclusao e fonte."""
    lista = "\n".join(f"- {item}" for item in itens)
    return f"**O que mostra:** {mostra}\n\n{lista}\n\n**O que concluímos:** {conclusao}\n\n_{rodape}_"


def _todas(situacoes: list[str], total: int) -> str:
    if len(situacoes) == total:
        return {1: "", 2: " nas duas situações"}.get(total, " em todas as situações")
    return " em " + " e ".join(situacoes)


def g3(simulados: pd.DataFrame | None, exatos: pd.DataFrame) -> str:
    df = res.erro_tipo_i(_taxas(simulados, exatos))
    itens, desvios = [], {}
    situacoes = list(dict.fromkeys(df["situacao"]))
    for situacao, g in df.groupby("situacao", sort=False):
        z, b = (g[g["teste"] == teste].iloc[0] for teste in ("Z", "Binomial"))
        itens.append(f"**{situacao}:** Z {pct(z['taxa'])} · binomial {pct(b['taxa'])}")
        for t in (z, b):
            tipo = classificar(t["taxa"], t["margem"], t["alpha"])
            if tipo != "perto de 5%":
                desvios.setdefault((t["teste"], tipo), []).append(situacao)
    sentido = {"liberal": "acima de 5%", "conservador": "abaixo de 5%"}
    partes = [f"o {CURTO[teste]} ficou **{tipo}** ({sentido[tipo]})" for teste, tipo in desvios]
    if len({tuple(sits) for sits in desvios.values()}) == 1:  # mesmo desvio em todas as situacoes: uma frase so
        resumo = " e ".join(partes) + _todas(next(iter(desvios.values())), len(situacoes))
    else:
        resumo = "; ".join(f"{parte}{_todas(sits, len(situacoes))}" for parte, sits in zip(partes, desvios.values()))
    return _bloco(
        "quantas vezes cada teste rejeitou H₀ quando ela era verdadeira (p = 5%). O ideal é ficar na linha de 5%.",
        itens,
        (f"{resumo}. " if resumo else "os dois testes ficaram perto de 5% em todas as situações. ")
        + "Como o número de falhas é inteiro, nenhum teste acerta 5% exatos: a normal do Z subestima a cauda direita "
        "quando n·p₀ é pequeno, e o binomial escolhe o corte que nunca passa de 5%.",
        origem(simulados).capitalize() + ".",
    )


def _primeiro_80(g: pd.DataFrame) -> str | None:
    acima = g[g["taxa"] >= 0.8]
    return pp(acima["efeito"].iloc[0]) if len(acima) else None


def g4(simulados: pd.DataFrame | None, exatos: pd.DataFrame, efeito_observado: float) -> str:
    df = res.poder(_taxas(simulados, exatos))
    itens = []
    for situacao, g in df.groupby("situacao", sort=False):
        z, b = g[g["teste"] == "Z"], g[g["teste"] == "Binomial"]
        alvo = (z["efeito"] - efeito_observado).abs().idxmin()
        efeito = z.loc[alvo, "efeito"]
        pz, pb = z.loc[alvo, "taxa"], b[b["efeito"] == efeito]["taxa"].iloc[0]
        oitenta = [f"{nome} em {v}" if v else f"{nome} não chega" for nome, v in
                   (("Z", _primeiro_80(z)), ("binomial", _primeiro_80(b)))]
        itens.append(f"**{situacao}:** Z {pct(pz)} · binomial {pct(pb)} (80% de poder: {' e '.join(oitenta)})")
    base = df[df["situacao"] == df["situacao"].iloc[0]]
    gap = (base[base["teste"] == "Z"].set_index("efeito")["taxa"] - base[base["teste"] == "Binomial"].set_index("efeito")["taxa"])
    return _bloco(
        f"quantas vezes cada teste rejeita H₀ à medida que a taxa verdadeira se afasta de 5%. Curva mais alta = mais "
        f"poder. Os números abaixo usam {pp(base['efeito'].loc[(base['efeito'] - efeito_observado).abs().idxmin()])}, "
        "o ponto da grade mais perto do efeito do Ruff.",
        itens,
        "o Z detecta mais, mas pelo mesmo motivo que o deixa liberal no G3: ele também rejeita mais quando não há "
        f"efeito. Na base, a diferença chega a {br(100 * gap.max(), 1)} pontos em {pp(gap.idxmax())} e cai para "
        f"{br(100 * gap.iloc[-1], 1)} em {pp(gap.index[-1])}, quando os dois quase sempre rejeitam.",
        origem(simulados).capitalize() + ".",
    )


def tamanho_amostra(a: est.Amostra, n_80: dict[str, int | None]) -> str:
    poder_z, poder_b = (res.taxa_exata(teste, a.n, a.proporcao) for teste in res.TESTES)
    alfa = {(teste, n): res.taxa_exata(teste, n, est.P0) for teste in res.TESTES for n in (100, 200)}
    dias = (datetime.fromisoformat(a.fim.replace("Z", "+00:00"))
            - datetime.fromisoformat(a.inicio.replace("Z", "+00:00"))).total_seconds() / 86400
    dias_80 = max(n_80.values()) * dias / a.n  # no ritmo de execucoes da amostra real
    return _bloco(
        f"o poder de cada teste para a taxa do Ruff ({pct(a.proporcao)}) conforme o número de execuções coletadas.",
        [f"**Com as {a.n} execuções reais:** Z {pct(poder_z)} · binomial {pct(poder_b)}",
         f"**80% de poder garantido:** Z a partir de {n_80['Z']} execuções · binomial a partir de {n_80['Binomial']} "
         f"(cerca de {round(dias_80)} dias de CI do Ruff)",
         f"**Erro tipo I do Z com mais dados:** {pct(alfa['Z', 100])} com 100 execuções · {pct(alfa['Z', 200])} com 200, "
         "quando os cortes dos dois testes coincidem"],
        "coletar mais seria viável e reduziria a diferença entre os testes. Com muitas execuções, porém, até "
        "diferenças pequenas ficam significativas, e o tamanho do efeito passa a importar mais que o p-valor.",
        "Poder exato pela binomial, sem simulação.",
    )
