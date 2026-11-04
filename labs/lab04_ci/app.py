"""Dashboard do Lab04: testes de hipotese para a taxa de falha do CI (par P4).

    streamlit run labs/lab04_ci/app.py

S01 (#98): secoes 1 a 3 (Cenario, Os dados com G1, Como os testes funcionam com G2). As secoes 4 a 7
entram nas proximas sprints (#101, #102, #103).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # `streamlit run` executa o arquivo como script
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from labs.lab04_ci import estatistica as est  # noqa: E402
from labs.lab04_ci import graficos, textos  # noqa: E402

REPOSITORIO = "https://github.com/JoaoRajao/lab-medicao"
PROJETO = "https://github.com/users/JoaoRajao/projects/4"
DASHBOARD = "https://joaorajao-lab-medicao-labslab04-ciapp-jw2ure.streamlit.app/"
SECOES = [
    ("cenario", "1. Cenário", True), ("dados", "2. Os dados", True), ("testes", "3. Como os testes funcionam", True),
    ("erro", "4. Erro tipo I", False), ("poder", "5. Poder", False), ("reais", "6. Dados reais", False),
    ("conclusao", "7. Conclusão", False),
]

CSS = f"""
<style>
  .stApp {{ background: #f9f9f7; }}
  .block-container {{ padding-top: 2rem; max-width: 1200px; }}
  h1, h2, h3 {{ color: {graficos.TINTA}; letter-spacing: -0.01em; }}
  .subtitulo {{ color: {graficos.TINTA_SECUNDARIA}; font-size: 1.05rem; margin-top: -0.6rem; }}
  .links a {{ color: {graficos.COR_Z}; text-decoration: none; margin-right: 1.2rem; font-weight: 500; }}
  .hipotese {{ border-left: 3px solid {graficos.EIXO}; padding: 0.35rem 0.8rem; margin: 0.4rem 0;
               background: {graficos.SUPERFICIE}; border-radius: 0 6px 6px 0; }}
  .hipotese b {{ color: {graficos.TINTA}; margin-right: 0.4rem; }}
  .chave {{ display: inline-block; width: 0.75rem; height: 0.75rem; border-radius: 3px; margin-right: 0.35rem;
            vertical-align: -1px; }}
  .leitura-titulo {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em;
                     color: {graficos.COR_H0_EXATA}; margin-bottom: 0.3rem; }}
  [data-testid="stMetricValue"] {{ font-size: 1.7rem; color: {graficos.TINTA}; }}
  [data-testid="stMetricLabel"] p {{ color: {graficos.TINTA_SECUNDARIA}; }}
  .pendente {{ color: {graficos.COR_H0_EXATA}; }}
</style>
"""


def chave(cor: str, rotulo: str) -> str:
    return f'<span class="chave" style="background:{cor}"></span>{rotulo}'


def leitura(texto: str) -> None:
    st.markdown('<div class="leitura-titulo">Como ler e o que concluímos</div>', unsafe_allow_html=True)
    st.markdown(texto)


def barra_lateral() -> None:
    with st.sidebar:
        st.markdown("### Lab04 · Par P4")
        st.caption("Teste Z para uma proporção × binomial exato")
        for ancora, titulo, pronta in SECOES:
            st.markdown(f"[{titulo}](#{ancora})" if pronta else f'<span class="pendente">{titulo} · próximas sprints</span>',
                        unsafe_allow_html=True)
        st.divider()
        st.markdown(chave(graficos.COR_Z, "Teste Z") + "<br>" + chave(graficos.COR_BINOMIAL, "Binomial exato"),
                    unsafe_allow_html=True)
        st.caption(f"α = 0,05 · p₀ = 0,05 · semente {est.SEED}")


def cabecalho(a: est.Amostra) -> None:
    st.title("A taxa de falha do CI passa da meta de 5%?")
    st.markdown(f'<p class="subtitulo">Lab04 — testes de hipótese por dentro, com o CI do <code>{a.repositorio}</code></p>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="links"><a href="{REPOSITORIO}">Repositório no GitHub ↗</a>'
                f'<a href="{PROJETO}">GitHub Projects ↗</a>'
                f'<a href="{DASHBOARD}">Dashboard publicado ↗</a></div>',
                unsafe_allow_html=True)
    colunas = st.columns(5)
    indicadores = [
        ("Execuções observadas", str(a.n), None),
        ("Falhas", str(a.falhas), None),
        ("Taxa (meta 5%)", textos.pct(a.proporcao), br_pp(a.proporcao - est.P0)),
        ("p-valor · Z", graficos.br(est.p_valor_z(a.falhas, a.n), 4), None),
        ("p-valor · binomial", graficos.br(est.p_valor_binomial(a.falhas, a.n), 4), None),
    ]
    for coluna, (rotulo, valor, delta) in zip(colunas, indicadores):
        with coluna.container(border=True):
            st.metric(rotulo, valor, delta, delta_color="inverse" if delta else "normal")


def br_pp(diferenca: float) -> str:
    return f"+{graficos.br(100 * diferenca, 1)} p.p." if diferenca >= 0 else f"{graficos.br(100 * diferenca, 1)} p.p."


def secao_cenario(a: est.Amostra) -> None:
    st.header("1. Cenário", anchor="cenario")
    esquerda, direita = st.columns([1.15, 1], gap="large")
    with esquerda.container(border=True):
        st.markdown("**Pergunta**")
        st.markdown(textos.pergunta(a))
        for rotulo, texto in textos.hipoteses():
            st.markdown(f'<div class="hipotese"><b>{rotulo}</b>{texto}</div>', unsafe_allow_html=True)
        st.markdown(textos.desenho())
    with direita.container(border=True):
        st.markdown("**De onde vêm os dados**")
        st.markdown(textos.fonte(a))
        st.markdown("**Expectativa antes de simular**")
        st.markdown(textos.expectativa(a))


def secao_dados(a: est.Amostra) -> None:
    st.header("2. Os dados", anchor="dados")
    with st.container(border=True):
        grafico, texto = st.columns([2.2, 1], gap="large")
        grafico.plotly_chart(graficos.g1_dados(a), width="stretch", config={"displayModeBar": False})
        with texto:
            leitura(textos.g1(a))


def secao_testes(a: est.Amostra) -> None:
    st.header("3. Como os testes funcionam", anchor="testes")
    with st.container(border=True):
        log = st.toggle("Escala logarítmica no eixo vertical (mostra a cauda e a área do p-valor)", value=False)
        st.plotly_chart(graficos.g2_testes(a, escala_log=log), width="stretch",
                        config={"displayModeBar": False})
        st.dataframe(pd.DataFrame(textos.comparacao(a)), hide_index=True, width="stretch")
        leitura(textos.g2(a))


def main() -> None:
    st.set_page_config(page_title="Lab04 — Taxa de falha do CI", page_icon="📊", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    amostra = est.carregar_amostra()
    barra_lateral()
    cabecalho(amostra)
    secao_cenario(amostra)
    secao_dados(amostra)
    secao_testes(amostra)
    st.divider()
    st.caption("Seções 4 a 7 (erro tipo I, poder, dados reais e conclusão) entram nas próximas sprints.")


if __name__ == "__main__":
    main()
