"""Textos do dashboard, montados a partir dos dados para nao ficarem desatualizados (issue #98)."""

from __future__ import annotations

from labs.lab04_ci import estatistica as est
from labs.lab04_ci.graficos import br


def _pct(valor: float, casas: int = 1) -> str:
    return br(100 * valor, casas) + "%"


def cenario(a: est.Amostra) -> str:
    return (
        f"**Pergunta:** a taxa de falha do workflow de CI do `{a.repositorio}` passa da meta de 5%?\n\n"
        f"- **H₀:** a probabilidade de uma execução falhar é no máximo 5% (p ≤ 0,05).\n"
        f"- **H₁:** a probabilidade de falha é maior que 5% (p > 0,05). Os dois testes são **unicaudais à direita**, "
        f"com α = 0,05, porque só interessa saber se a meta foi **ultrapassada**.\n"
        f"- **Testes comparados (par P4):** Z para uma proporção × binomial exato.\n"
        f"- **Dados reais:** {a.n} execuções do workflow `CI` disparadas por `push` em `main`, uma por commit, "
        f"entre {a.inicio[:10]} e {a.fim[:10]}, coletadas da API do GitHub "
        f"(`labs/lab04_ci/data/raw/ci_runs.csv`, com o link de cada execução). Houve **{a.falhas} falhas** "
        f"({_pct(a.proporcao)}).\n"
        f"- **Expectativa antes de simular:** o binomial exato deve controlar melhor o erro tipo I, porque sob H₀ "
        f"esperamos só {br(a.n * est.P0, 1)} falhas em {a.n} execuções, pouco para a aproximação normal do Z."
    )


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
        f"o Z rejeita a partir de {k_z} falhas, o que sob H₀ acontece com probabilidade {_pct(alfa_z)} (acima de 5%: "
        f"tende a ser **liberal**), e o binomial a partir de {k_b}, com probabilidade {_pct(alfa_b)} (**conservador**). "
        f"O p-valor do exemplo é a chance de ver {a.falhas} ou mais falhas em {a.n} execuções **se a taxa fosse 5%**: "
        f"{br(p_b, 4)} pelo binomial e {br(p_z, 4)} pelo Z; não é a probabilidade de H₀ ser verdadeira."
    )
