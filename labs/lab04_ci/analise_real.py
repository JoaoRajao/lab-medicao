"""Aplicação dos testes à amostra real e conclusão do Lab04 (issue #102)."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from labs.lab04_ci import estatistica as est
from labs.lab04_ci import resultados as res
from labs.lab04_ci import simulacao

N_GRANDE = 200  # tamanho em que os cortes do Z e do binomial passam a coincidir
RESULTADOS = Path(__file__).resolve().parent / "data" / "simulacao" / "resultados.csv"


def tamanho_efeito(a: est.Amostra, p0: float = est.P0) -> tuple[float, float]:
    """Diferença absoluta em pontos percentuais e h de Cohen para uma proporção."""
    diferenca_pp = 100 * (a.proporcao - p0)
    h = 2 * (math.asin(math.sqrt(a.proporcao)) - math.asin(math.sqrt(p0)))
    return diferenca_pp, h


def _decimal(valor: float, casas: int) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def tabela(a: est.Amostra) -> pd.DataFrame:
    resultado = simulacao.comparar_testes(a.falhas, n=a.n, p0=est.P0, alpha=est.ALPHA)
    delta, h = tamanho_efeito(a)
    linhas = []
    for nome, teste, estatistica in (
        ("Z para uma proporção", resultado.teste_z, "z"),
        ("Binomial exato", resultado.binomial, "k"),
    ):
        linhas.append({
            "Teste": nome,
            "Estatística": f"z = {_decimal(teste.estatistica, 3)}" if estatistica == "z" else f"k = {a.falhas}",
            "p-valor": _decimal(teste.p_valor, 4),
            "Tamanho do efeito": f"Δp = {f'{delta:+.2f}'.replace('.', ',')} p.p.; h = {_decimal(h, 3)}",
            "Conclusão (α = 0,05)": teste.decisao,
        })
    return pd.DataFrame(linhas)


def _resumo_base(path: Path) -> tuple[dict[str, float], dict[str, float], tuple[str, dict[str, float]] | None]:
    if not path.is_file():
        return {}, {}, None
    dados = pd.read_csv(path)
    base = dados[(dados["situacao"] == "Base (n = 30)") & (dados["efeito"].abs() < 1e-12)]
    taxas = {str(linha.teste): float(linha.taxa_rejeicao) for linha in base.itertuples()}
    poder = dados[(dados["situacao"] == "Base (n = 30)") & ((dados["p_verdadeiro"] - 0.20).abs() < 1e-12)]
    poder_taxas = {str(linha.teste): float(linha.taxa_rejeicao) for linha in poder.itertuples()}
    adversas = [s for s in dados["situacao"].unique() if s != "Base (n = 30)"]
    if not adversas:
        return taxas, poder_taxas, None
    nome = str(adversas[0])
    q3 = dados[(dados["situacao"] == nome) & (dados["efeito"].abs() < 1e-12)]
    return taxas, poder_taxas, (nome, {str(linha.teste): float(linha.taxa_rejeicao) for linha in q3.itertuples()})


def texto_dados_reais(a: est.Amostra) -> str:
    delta, h = tamanho_efeito(a)
    resultado = simulacao.comparar_testes(a.falhas, n=a.n, p0=est.P0, alpha=est.ALPHA)
    if resultado.teste_z.rejeita_h0 and resultado.binomial.rejeita_h0:
        decisao = "Os dois testes rejeitam H₀"
    elif resultado.teste_z.rejeita_h0 or resultado.binomial.rejeita_h0:
        decisao = "Os testes chegam a decisões diferentes sobre H₀"
    else:
        decisao = "Nenhum dos testes rejeita H₀"
    return (
        f"Na amostra de {a.n} execuções, {a.falhas} falharam: {_decimal(100 * a.proporcao, 1)}% "
        f"ante a meta de {_decimal(100 * est.P0, 0)}%, uma diferença de {_decimal(delta, 2)} "
        f"pontos percentuais (h de Cohen = {_decimal(h, 3)}). "
        f"{decisao} para α = {_decimal(est.ALPHA, 2)}; essa diferença pode ser relevante para a operação do CI, "
        "mas a amostra curta não mede a taxa histórica do projeto."
    )


def blocos_conclusao(a: est.Amostra, resultados_path: Path = RESULTADOS) -> list[tuple[str, str]]:
    """Conclusao em quatro partes: expectativa x resultado, recomendacao, quando muda e limitacao."""
    taxas, poder_taxas, q3_resultado = _resumo_base(resultados_path)
    if {"Z", "Binomial"} <= taxas.keys():
        simulacao_texto = (
            f"Na simulação sob H₀, o Z rejeitou em {_decimal(100 * taxas['Z'], 2)}% dos conjuntos e o binomial em "
            f"{_decimal(100 * taxas['Binomial'], 2)}%, frente ao alvo de 5%. "
        )
    else:
        simulacao_texto = "As taxas simuladas de erro tipo I ainda não estão disponíveis. "
    if {"Z", "Binomial"} <= poder_taxas.keys():
        poder_texto = (f"Com taxa verdadeira de 20%, o poder foi {_decimal(100 * poder_taxas['Z'], 2)}% para Z e "
                       f"{_decimal(100 * poder_taxas['Binomial'], 2)}% para o binomial; a vantagem do Z "
                       "vem acompanhada de mais falsos positivos sob H₀. ")
    else:
        poder_texto = "As curvas de poder Q2 ainda não estão disponíveis. "
    if q3_resultado and {"Z", "Binomial"} <= q3_resultado[1].keys():
        nome, q3_taxas = q3_resultado
        q3 = (f"Na situação {nome}, Q3 mediu erro tipo I de {_decimal(100 * q3_taxas['Z'], 1)}% para Z e "
              f"{_decimal(100 * q3_taxas['Binomial'], 1)}% para o binomial; a interpretação depende do pressuposto violado.")
    else:
        q3 = "A situação adversa Q3 (#100) ainda não está disponível; a recomendação se limita ao cenário base."
    return [
        ("Esperávamos × encontramos",
         "A expectativa registrada antes da simulação era que o binomial exato controlaria melhor o erro tipo I "
         f"com {a.n} execuções. {simulacao_texto}{poder_texto}".strip()),
        ("Recomendação",
         f"Na amostra real, ambos rejeitam H₀, com {a.falhas}/{a.n} falhas ({_decimal(100 * a.proporcao, 1)}%), mas "
         "recomendamos o binomial exato para amostras pequenas de execuções independentes: o Z usa uma aproximação "
         "normal liberal neste tamanho."),
        ("Quando a escolha muda",
         "Com amostras maiores, a escolha pelo Z exigiria verificar que seu erro tipo I se aproxima de 5%: com "
         f"{N_GRANDE} execuções, os cortes dos dois testes coincidem e o erro tipo I fica em "
         f"{_decimal(100 * res.taxa_exata('Z', N_GRANDE, est.P0), 1)}% para ambos (ver “E o tamanho da amostra?”)."),
        ("Situação adversa e limitação",
         f"{q3} A principal limitação é a amostra: {a.n} execuções de poucos dias de um único projeto; se falhas "
         "próximas compartilham a mesma causa, a independência de ambos os testes precisa ser revista."),
    ]


def texto_conclusao(a: est.Amostra, resultados_path: Path = RESULTADOS) -> str:
    return " ".join(texto for _, texto in blocos_conclusao(a, resultados_path))
