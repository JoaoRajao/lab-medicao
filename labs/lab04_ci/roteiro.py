"""Roteiro da apresentacao oral: respostas curtas as 15 perguntas da secao 5 do enunciado (issue #104).

As respostas sao montadas a partir dos mesmos dados do dashboard (amostra real, resultados de Q1-Q3 e valores
exatos), para nao ficarem desatualizadas. Gera `docs/lab04/roteiro_apresentacao.md`:

    python -m labs.lab04_ci.roteiro
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from labs.lab04_ci import estatistica as est
from labs.lab04_ci import resultados as res
from labs.lab04_ci.graficos import _taxas, br
from labs.lab04_ci.textos import classificar, pct

ROOT = Path(__file__).resolve().parents[2]
ROTEIRO_PATH = ROOT / "docs" / "lab04" / "roteiro_apresentacao.md"
DASHBOARD = "https://joaorajao-lab-medicao-labslab04-ciapp-jw2ure.streamlit.app/"
# Divisao: cada integrante responde as perguntas da parte que implementou (minimo de 4 por pessoa).
RESPONSAVEL = {1: "João", 2: "Pedro", 3: "João", 4: "João", 5: "Pedro", 6: "Pedro", 7: "Pedro", 8: "Pedro",
               9: "Salomão", 10: "Salomão", 11: "Salomão", 12: "Salomão", 13: "Salomão", 14: "João", 15: "João"}
PERGUNTAS = {
    1: ("Qual é o cenário de vocês e o que H₀ e H₁ afirmam, em palavras simples?", "1. Cenário"),
    2: ("O teste de vocês é unicaudal ou bicaudal? Por quê?", "1. Cenário"),
    3: ("Como os dados reais foram coletados, e o que eles mostraram sobre a forma da distribuição?", "2. Os dados (G1)"),
    4: ("Como os dados reais ajudaram a escolher os parâmetros da simulação?", "2. Os dados (G1)"),
    5: ("O que cada um dos dois testes compara de fato (médias, postos, proporções...)?", "3. Como os testes funcionam (G2)"),
    6: ("No G2: o que é a distribuição da estatística sob H₀, e por que a região de rejeição fica onde fica?",
        "3. Como os testes funcionam (G2)"),
    7: ("O que significa o p-valor do exemplo mostrado no G2? E o que ele não significa?", "3. Como os testes funcionam (G2)"),
    8: ("No cenário de vocês, o que seria um erro tipo I e um erro tipo II? Qual dos dois seria mais grave?", "4. Erro tipo I (G3)"),
    9: ("No G3, algum teste se afastou de 5%? Ele ficou liberal ou conservador, e por quê?", "4. Erro tipo I (G3)"),
    10: ("No G4, qual teste tem mais poder? A diferença entre eles muda conforme o tamanho do efeito?", "5. Poder (G4)"),
    11: ("Que violação de pressuposto vocês simularam, e por que ela afeta mais um teste do que o outro?",
         "4 e 5 (G3 e G4, situação adversa)"),
    12: ("Se vocês usassem α = 0,01 em vez de 0,05, o que mudaria no G3 e no G4?", "4 e 5 (G3 e G4)"),
    13: ("A simulação confirmou o que o grupo esperava antes de simular? Se não, o que explica a diferença?", "1. Cenário → 4 e 5"),
    14: ("Nos dados reais, os dois testes chegaram à mesma conclusão? O tamanho do efeito tem importância prática?",
         "6. Dados reais"),
    15: ("Qual teste vocês recomendam para o cenário, em que situação mudariam a recomendação, e qual é a principal "
         "limitação do estudo?", "7. Conclusão"),
}


def cohen_h(p: float, p0: float = est.P0) -> float:
    """Tamanho do efeito para proporcoes: h = 2*asen(raiz(p)) - 2*asen(raiz(p0))."""
    return 2 * math.asin(math.sqrt(p)) - 2 * math.asin(math.sqrt(p0))


def _linha(df: pd.DataFrame, situacao: str, teste: str, efeito: float = 0.0) -> pd.Series:
    g = df[(df["situacao"] == situacao) & (df["teste"] == teste)]
    return g.loc[(g["efeito"] - efeito).abs().idxmin()]


def respostas(a: est.Amostra, simulados: pd.DataFrame | None, exatos: pd.DataFrame) -> dict[int, str]:
    df = _taxas(simulados, exatos)
    base = df["situacao"].iloc[0]
    adversas = [s for s in dict.fromkeys(df["situacao"]) if s != base]
    efeito_real = a.proporcao - est.P0
    z_obs, p_z, p_b = est.estatistica_z(a.falhas, a.n), est.p_valor_z(a.falhas, a.n), est.p_valor_binomial(a.falhas, a.n)
    k_z, k_b = est.falhas_criticas_z(a.n), est.falhas_criticas_binomial(a.n)
    z0, b0 = _linha(df, base, "Z"), _linha(df, base, "Binomial")
    zr, br_ = _linha(df, base, "Z", efeito_real), _linha(df, base, "Binomial", efeito_real)
    fonte = "simulação com 10.000 repetições" if simulados is not None else "valor exato da binomial (simulação pendente)"
    r = {}
    r[1] = (f"Queremos saber se o CI do `{a.repositorio}` falha mais do que a meta de 5%. H₀ diz que a chance de uma "
            f"execução falhar é no máximo 5%; H₁ diz que é maior que 5%. Coletamos {a.n} execuções reais e comparamos "
            "dois testes que respondem essa mesma pergunta: o Z para uma proporção e o binomial exato.")
    r[2] = ("Unicaudal à direita. A meta só é descumprida se a taxa de falha for **maior** que 5%; uma taxa menor é "
            "boa notícia, não um problema. Por isso H₁ é p > 0,05 e só contagens altas de falhas contam como evidência "
            "contra H₀ — a região de rejeição fica toda na cauda direita.")
    r[3] = (f"Pela API do GitHub, pegamos as {a.n} execuções mais recentes do workflow `CI` disparadas por push em main, "
            f"uma por commit, de {a.inicio[:10]} a {a.fim[:10]}; cada linha do CSV tem o link da execução. Deram "
            f"{a.falhas} falhas e {a.sucessos} sucessos ({pct(a.proporcao)}). Cada observação é 0 ou 1: a distribuição é "
            "fortemente assimétrica, concentrada em zero, sem outliers numéricos.")
    r[4] = (f"O tamanho de cada conjunto simulado é o mesmo da amostra real, n = {a.n}. Como o dado é binário, o modelo "
            "natural é Bernoulli independente; sob H₀ usamos p = 5%, a meta. Para o poder, a grade de taxas vai de 5% a "
            f"30% e cobre a taxa observada, {pct(a.proporcao)}, que mostra o tamanho de efeito realista para o Ruff.")
    r[5] = ("Os dois olham para a **proporção de falhas**, ou seja, para o número de falhas X em n execuções. O Z "
            "padroniza essa proporção, (X − n·p₀)/√(n·p₀(1−p₀)), e compara com uma normal padrão — é uma aproximação. "
            "O binomial compara X diretamente com a distribuição Binomial(n; 0,05), que é a distribuição exata sob H₀.")
    r[6] = (f"É o que a estatística faria se H₀ fosse verdadeira e repetíssemos a coleta muitas vezes: a normal padrão "
            f"no Z e a Binomial({a.n}; 0,05) no binomial. A região de rejeição fica na cauda direita porque H₁ é p > 5%; "
            f"ela vai até onde a probabilidade sob H₀ soma 5%: z > {br(est.z_critico(), 2)}, ou seja, {k_z} falhas ou "
            f"mais, no Z, e {k_b} falhas ou mais no binomial.")
    r[7] = (f"Com {a.falhas} falhas, o p-valor é a chance de ver {a.falhas} ou mais falhas em {a.n} execuções **se a taxa "
            f"verdadeira fosse 5%**: {br(p_b, 4)} pelo binomial e {br(p_z, 4)} pelo Z (z = {br(z_obs, 2)}). Ele **não** é a "
            "probabilidade de H₀ ser verdadeira, nem a chance de o resultado ser acaso, nem mede o tamanho do problema.")
    r[8] = ("Erro tipo I: concluir que o CI passou da meta quando na verdade não passou — o time para para investigar "
            "uma instabilidade que não existe. Erro tipo II: não perceber que a taxa passou de 5% — as falhas continuam "
            "travando merges e tirando a confiança no CI. Para nós o tipo II é mais grave, porque o custo dele se acumula "
            "a cada execução, enquanto um alarme falso custa uma investigação.")
    desvios = [f"o Z deu {pct(_linha(df, s, 'Z')['taxa'])} e o binomial {pct(_linha(df, s, 'Binomial')['taxa'])} em {s}"
               for s in [base] + adversas]
    r[9] = (f"Sim. Pela {fonte}, {'; '.join(desvios)}. O Z ficou **{classificar(z0['taxa'], z0['margem'])}** e o binomial "
            f"**{classificar(b0['taxa'], b0['margem'])}**. Como X é inteiro, os cortes saltam: o Z rejeita a partir de "
            f"{k_z} falhas, o que sob H₀ tem probabilidade {pct(res.taxa_exata('Z', a.n, est.P0))}, porque a normal "
            f"subestima a cauda direita com n·p₀ = {br(a.n * est.P0, 1)}; o binomial só pode cortar em {k_b}, que fica "
            f"abaixo de 5% ({pct(res.taxa_exata('Binomial', a.n, est.P0))}).")
    gap = (df[(df["situacao"] == base) & (df["teste"] == "Z")].set_index("efeito")["taxa"]
           - df[(df["situacao"] == base) & (df["teste"] == "Binomial")].set_index("efeito")["taxa"])
    lider = "O Z tem mais poder em todos os efeitos" if (gap.drop(0.0, errors="ignore") > 0).all() else "O Z tem mais poder na maior parte dos efeitos"
    r[10] = (f"{lider}: com +{br(100 * zr['efeito'], 1)} p.p., o ponto da grade mais perto do efeito do Ruff "
             f"(+{br(100 * efeito_real, 1)} p.p.), rejeita em {pct(zr['taxa'])} contra {pct(br_['taxa'])} do binomial. "
             f"A diferença chega a {br(100 * gap.max(), 1)} pontos em +{br(100 * gap.idxmax(), 1)} p.p. e cai para "
             f"{br(100 * gap.iloc[-1], 1)} em +{br(100 * gap.index[-1], 1)} p.p., quando os dois rejeitam quase sempre. "
             "O poder extra do Z vem do mesmo corte mais baixo que o faz errar mais sob H₀ — não é vantagem gratuita.")
    piora_z = False
    if adversas:
        s = adversas[0]
        za, ba = _linha(df, s, "Z"), _linha(df, s, "Binomial")
        piora_z = za["taxa"] > z0["taxa"]
        numeros = (f"o erro tipo I do Z foi de {pct(z0['taxa'])} na base para {pct(za['taxa'])}, e o binomial ficou em "
                   f"{pct(ba['taxa'])}")
        if (df.loc[df["situacao"] == s, "modelo"] == res.MODELO_EXATO).all() if "modelo" in df else False:
            r[11] = (f"Simulamos {s}. O Z depende da aproximação normal, que piora quando n·p₀ fica pequeno; o binomial é "
                     f"exato para qualquer n, desde que as execuções sejam independentes. Resultado: {numeros}"
                     + (": a violação pesa no teste paramétrico, não no exato." if piora_z and ba["taxa"] <= est.ALPHA else "."))
        else:
            r[11] = (f"Simulamos {s}, em que os dados deixam de ser Bernoulli independentes com a mesma p. Resultado: "
                     f"{numeros}. (Explicar o mecanismo conforme a #100.)")
    else:
        r[11] = "Pendente: a situação adversa é definida e simulada na #100; esta resposta é gerada quando os resultados existirem."
    z01, b01 = res.taxa_exata("Z", a.n, est.P0, alpha=0.01), res.taxa_exata("Binomial", a.n, est.P0, alpha=0.01)
    zp01 = res.taxa_exata("Z", a.n, a.proporcao, alpha=0.01)
    bp01 = res.taxa_exata("Binomial", a.n, a.proporcao, alpha=0.01)
    r[12] = (f"Os cortes sobem: com α = 0,01, o Z passa a rejeitar a partir de {est.falhas_criticas_z(a.n, alpha=0.01)} "
             f"falhas e o binomial a partir de {est.falhas_criticas_binomial(a.n, alpha=0.01)}. No G3 a linha de "
             f"referência desce para 1% e o erro tipo I cai para {pct(z01)} (Z) e {pct(b01)} (binomial). No G4 as curvas "
             f"descem: com a taxa do Ruff, o poder seria {pct(zp01)} (Z) e {pct(bp01)} (binomial). Menos alarmes falsos, "
             "mais erros tipo II.")
    r[13] = (f"Em parte. Esperávamos que o binomial controlasse melhor o erro tipo I, e isso se confirmou: "
             f"{pct(b0['taxa'])} contra {pct(z0['taxa'])} do Z, que passou de 5%. Também esperávamos que o Z parecesse "
             "mais poderoso, e ele foi, mas a simulação mostrou que essa vantagem é justamente o preço do erro tipo I "
             "acima do nominal" + (f", e que o desvio do Z aumenta em {adversas[0]}." if piora_z else "."))
    h = cohen_h(a.proporcao)
    r[14] = (f"Sim: os dois rejeitam H₀ com α = 0,05 — p = {br(p_z, 4)} no Z e {br(p_b, 4)} no binomial. O efeito é a taxa "
             f"observada menos a meta, +{br(100 * efeito_real, 1)} pontos percentuais (h de Cohen = {br(h, 2)}, "
             f"efeito pequeno a médio). Na prática importa: {pct(a.proporcao)} é cerca de uma falha a cada "
             f"{round(1 / a.proporcao)} execuções, {br(a.proporcao / est.P0, 1)} vezes a meta.")
    r[15] = ("Recomendamos o **binomial exato**: ele nunca passa do α declarado, inclusive com amostras pequenas, e "
             "chegou à mesma conclusão nos dados reais. Mudaríamos para o Z com amostras grandes, em que n·p₀ passa de "
             "uns 10 e a normal aproxima bem — aí os dois quase coincidem e o Z é mais simples. A principal limitação: "
             f"{a.n} execuções de poucos dias de um único projeto, e falhas de CI costumam vir em sequência, o que viola "
             "a independência que os dois testes assumem.")
    return r


def markdown(a: est.Amostra, simulados: pd.DataFrame | None, exatos: pd.DataFrame) -> str:
    r = respostas(a, simulados, exatos)
    por_pessoa: dict[str, list[int]] = {}
    for numero, pessoa in RESPONSAVEL.items():
        por_pessoa.setdefault(pessoa, []).append(numero)
    linhas = [
        "# Lab04 — Roteiro da apresentação oral (15 perguntas)",
        "",
        "Gerado por `python -m labs.lab04_ci.roteiro` a partir dos mesmos dados do dashboard (amostra real, "
        "resultados de Q1–Q3 e valores exatos da binomial). Não edite à mão: rode o comando de novo.",
        "",
        f"- Dashboard: <{DASHBOARD}>",
        "- Duração: até 7 minutos, cerca de 25 segundos por resposta. Cada resposta indica a seção do dashboard para "
        "mostrar enquanto fala.",
        "- Resultados de Q1–Q3: " + ("simulação versionada em `labs/lab04_ci/data/simulacao/resultados.csv`."
                                      if simulados is not None else
                                      "**pendentes (#99/#100)**; números de erro tipo I e poder são os valores exatos."),
        "",
        "## Divisão",
        "",
        "| Integrante | Perguntas |",
        "| --- | --- |",
        *[f"| {pessoa} | {', '.join(map(str, nums))} |" for pessoa, nums in por_pessoa.items()],
        "",
        "## Respostas",
        "",
    ]
    for numero, (pergunta, secao) in PERGUNTAS.items():
        linhas += [f"### {numero}. {pergunta}", "", f"**{RESPONSAVEL[numero]}** · mostrar: {secao}", "", r[numero], ""]
    return "\n".join(linhas)


def gerar(path: Path = ROTEIRO_PATH) -> Path:
    simulados = res.carregar()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown(est.carregar_amostra(), simulados, res.exatos(simulados)), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(f"OK: {gerar().relative_to(ROOT)}")
