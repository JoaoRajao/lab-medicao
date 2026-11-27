"""Pagina da calculadora de configuracao do SQLite (Lab05, #137). Vira uma secao do dashboard final.

    streamlit run labs/lab05_sqlite/app_calculadora.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from labs.lab05_sqlite import calculadora  # noqa: E402

st.set_page_config(page_title="Lab05 · Calculadora SQLite", layout="wide")
st.title("Qual configuração do SQLite usar?")
st.caption("Lab05 · Laboratório de Experimentação de Software · recomendação a partir dos dados medidos")


@st.cache_data
def dados() -> dict:
    return calculadora.carregar()


calculadora.render(st, dados())
