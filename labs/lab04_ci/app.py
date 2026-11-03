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

import streamlit as st  # noqa: E402

from labs.lab04_ci import estatistica as est  # noqa: E402
from labs.lab04_ci import textos  # noqa: E402
from labs.lab04_ci.graficos import g1_dados, g2_testes  # noqa: E402

REPOSITORIO = "https://github.com/JoaoRajao/lab-medicao"
PROJETO = "https://github.com/users/JoaoRajao/projects/4"


def main() -> None:
    st.set_page_config(page_title="Lab04 — Taxa de falha do CI", layout="wide")
    amostra = est.carregar_amostra()

    st.title("Lab04 — A taxa de falha do CI passa da meta de 5%?")
    st.markdown(f"**Repositório:** [{REPOSITORIO}]({REPOSITORIO}) · **GitHub Projects:** [{PROJETO}]({PROJETO}) · "
                "**Dashboard:** execute `streamlit run labs/lab04_ci/app.py` na raiz do repositório")

    st.header("1. Cenário")
    st.markdown(textos.cenario(amostra))

    st.header("2. Os dados")
    st.pyplot(g1_dados(amostra))
    st.markdown(textos.g1(amostra))

    st.header("3. Como os testes funcionam")
    st.pyplot(g2_testes(amostra))
    st.markdown(textos.g2(amostra))

    st.info("Seções 4 a 7 (erro tipo I, poder, dados reais e conclusão) entram nas próximas sprints.")


if __name__ == "__main__":
    main()
