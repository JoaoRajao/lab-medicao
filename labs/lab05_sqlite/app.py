"""Dashboard final do Lab05: SQLite, qual configuracao usar?

Formato explicativo (a resposta primeiro): veredito e 4 numeros no topo; depois as abas com as evidencias, a
calculadora para decidir, o metodo e os limites. Tudo e calculado a partir dos dados versionados.

    streamlit run labs/lab05_sqlite/app.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from labs.lab05_sqlite import calculadora, painel, robustez  # noqa: E402

st.set_page_config(page_title="Lab05 · SQLite", page_icon="🗄️", layout="wide")
st.markdown("""<style>
  .block-container {padding-top: 2rem; max-width: 1250px;}
  [data-testid="stMetricValue"] {font-size: 2rem;}
  [data-testid="stCaptionContainer"] p {font-size: 0.92rem;}
  h5 {margin-top: 1.6rem;}
</style>""", unsafe_allow_html=True)

GRAFICO = {"displayModeBar": False}


@st.cache_data
def dados() -> dict:
    return painel.carregar()


d = dados()
n = painel.numeros(d)
_n, _vezes, _ms = robustez._n, robustez._vezes, robustez._ms

# ------------------------------------------------------------------------------------------ resposta primeiro
st.title("SQLite: qual configuração usar?")
st.markdown("Estudo experimental do **Lab05** (Laboratório de Experimentação de Software) sobre o banco de dados "
            "que roda dentro de celulares, navegadores e sistemas operacionais. "
            f"[Repositório]({painel.REPOSITORIO}) · [GitHub Projects]({painel.PROJECTS})")

r = painel.resposta(n)
with st.container(border=True):
    st.markdown(f"### {r['frase']}")
    for ponto in r["pontos"]:
        st.markdown(f"- {ponto}")
    st.caption(r["replicacao"].replace("**", ""))


def numero(coluna, rotulo: str, valor: str, comparacao: str, ajuda: str) -> None:
    """Numero de manchete com a comparacao em texto (sem a seta do st.metric, que sugeriria 'subiu')."""
    with coluna:
        st.metric(rotulo, valor, help=ajuda)
        st.caption(comparacao)


c1, c2, c3, c4 = st.columns(4)
numero(c1, "Gravação com WAL", f"{_vezes(n['h1'])} mais rápida", "comparado ao padrão DELETE/FULL",
       f"Razão das medianas WAL/FULL ÷ DELETE/FULL (H-1); intervalo de confiança 95%: "
       f"{_n(n['h1_inf'])}–{_n(n['h1_sup'])}")
numero(c2, "Quedas de energia com perda",
       f"{int(n['perda_wal']['rodadas_com_perda'])} de {int(n['perda_wal']['rodadas'])}",
       f"no WAL/FULL · no padrão: {int(n['perda_padrao']['rodadas_com_perda'])} de "
       f"{int(n['perda_padrao']['rodadas'])}",
       "Quedas do sistema simuladas no Linux em que alguma transação já confirmada sumiu")
numero(c3, "Telas lidas enquanto grava", f"{_n(n['telas_wal'], 0)} de 600",
       f"no WAL · no padrão: {_n(n['telas_delete'], 0)} de 600",
       f"Telas de 50 linhas lidas em 3 s com uma gravação em segundo plano ({n['conc_ambiente']})")
numero(c4, "Ambientes testados", f"{n['ambientes']}",
       f"direção repetida em {n['direcao']} de {n['pares']} comparações",
       "Notebook (Windows e Linux), GitHub Actions (Ubuntu, Windows, macOS) e iPhone 11")

with st.expander("📖 Termos usados no dashboard"):
    for termo, explicacao in painel.GLOSSARIO:
        st.markdown(f"- **{termo}:** {explicacao}")

evid, decida, metodo, limites = st.tabs(["📊 Evidências", "🧭 Decida para o seu app", "🔬 Como medimos",
                                         "⚠️ Limites"])

# ------------------------------------------------------------------------------------------------ evidencias
with evid:
    st.markdown("Quatro perguntas, uma por gráfico. Passe o mouse sobre os pontos para ver os valores exatos.")

    st.markdown("##### 1. Quanto mais rápido fica?")
    st.caption("**Como ler:** cada ponto é uma comparação medida em 30 rodadas no notebook com Windows. À direita da "
               "linha pontilhada, a primeira configuração faz mais operações por segundo. A barra é o intervalo de "
               "confiança: se ela cruza a linha, não há diferença detectável.")
    st.plotly_chart(painel.efeitos(d["testes"]), width="stretch", config=GRAFICO)
    st.markdown(f"➜ O WAL grava **{_vezes(n['h1'])}** mais rápido, e o `NORMAL` acelera o WAL em "
                f"**{_vezes(n['h3'])}**, mas esse ganho tem um custo (gráfico 2). Lendo tudo numa só transação "
                "(E-1), a diferença entre WAL e DELETE some: a vantagem do WAL na leitura avulsa vem do custo de "
                "abrir cada transação.")

    st.markdown("##### 2. Quem perde dados numa queda de energia?")
    st.caption("**Como ler:** 20 quedas de energia simuladas para cada configuração. O ponto mostra em quantas "
               "delas alguma transação já confirmada sumiu; a barra é o intervalo de confiança 95%.")
    st.plotly_chart(painel.durabilidade(d["durabilidade"]), width="stretch", config=GRAFICO)
    st.markdown(f"➜ O padrão perdeu a última transação em **{int(n['perda_padrao']['rodadas_com_perda'])} de "
                f"{int(n['perda_padrao']['rodadas'])}** quedas; o `WAL/FULL` não perdeu nenhuma, e o `WAL/NORMAL` "
                f"perdeu até **{int(n['perda_normal']['perdidas_max'])}** de uma vez. Travar o app (sem queda) não "
                f"perdeu nada em nenhuma configuração ({n['processo_perdas']} de {n['processo_rodadas']}), e "
                f"{n['integras']} de {n['falhas']} bancos continuaram íntegros.")

    st.markdown("##### 3. A tela trava enquanto o app grava?")
    st.caption("**Como ler:** uma lista é lida a cada 5 ms (600 telas em 3 s) enquanto uma sincronização grava em "
               "segundo plano. Barra cheia até 600 = a tela não travou.")
    st.plotly_chart(painel.concorrencia(d["concorrencia"]), width="stretch", config=GRAFICO)
    st.markdown(f"➜ No padrão, quem grava bloqueia quem lê: a pior leitura levou **{painel._tempo(n['pior_delete'])}**, "
                f"e um quadro de tela tem 16 ms. No WAL, **{_ms(n['pior_wal'])}**.")

    st.markdown("##### 4. O resultado se repete em outros aparelhos?")
    st.caption("**Como ler:** cada linha é uma comparação do gráfico 1; cada ponto, um ambiente (veja a legenda). "
               "Clique num nome da legenda para esconder ou mostrar aquele ambiente.")
    st.plotly_chart(painel.replicacao(d["replicacao"]), width="stretch", config=GRAFICO)
    st.markdown(f"➜ A direção se repete em **{n['direcao']} de {n['pares']}** comparações. A exceção é E-1, cujo "
                "efeito é praticamente nulo em todos os ambientes. **A magnitude muda bastante**: o tamanho do "
                "ganho depende do aparelho e do sistema.")

# ------------------------------------------------------------------------------------------------- calculadora
with decida:
    calculadora.render(st, d["calculadora"])

# ------------------------------------------------------------------------------------------------------ metodo
with metodo:
    a, b = st.columns([1.1, 1], gap="large")
    with a:
        st.markdown("##### A pergunta")
        st.markdown("Quanto o modo de *journal* (`WAL` × `DELETE`) e a sincronização (`FULL` × `NORMAL`) mudam a "
                    "velocidade de gravação e de leitura do SQLite, e **o que se perde em durabilidade** em troca?")
        st.markdown("##### Por que o SQLite")
        st.markdown("- **Real:** site, documentação e versões mantidos pelo fornecedor.\n"
                    "- **Em operação:** versões novas em 2026; embutido no Android, iOS, Windows, Chrome, Firefox e "
                    "Python.\n"
                    "- **Alto impacto:** mais de 1 trilhão de bancos em uso, segundo o fornecedor "
                    "([sqlite.org/mostdeployed](https://www.sqlite.org/mostdeployed.html)).")
        st.markdown("##### Como foi feito")
        st.markdown(
            "1. **Desempenho:** 4 configurações × 3 cargas, em 30 rodadas com ordem sorteada e banco novo a cada "
            "medição. Teste de Wilcoxon pareado com correção de Holm e razão das medianas com intervalo de "
            "confiança.\n"
            "2. **Durabilidade:** 250 falhas provocadas (app encerrado à força e queda do sistema com `sysrq b`), "
            "contando as transações confirmadas que sumiram.\n"
            "3. **Concorrência:** leitura de uma lista enquanto outra conexão grava, com hipóteses registradas antes "
            "da coleta.\n"
            "4. **Replicação:** a coleta de desempenho repetida em 6 ambientes.\n"
            "5. **Pesquisa documental:** a configuração que Android, Apple, Firefox e Python usam em produção.")
        st.info("**Ética:** tudo roda no ambiente do grupo. Nenhum sistema de terceiros recebe carga e nenhum dado "
                "pessoal é coletado.")
    with b:
        st.markdown("##### As 7 categorias da pesquisa")
        st.markdown(painel.tabela_md(painel.CATEGORIAS))
        st.markdown("##### O que veio dos labs anteriores")
        st.markdown("- **Lab01:** coleta por script e Kanban no GitHub Projects.\n"
                    "- **Lab02:** tratamentos e piloto antes da coleta completa.\n"
                    "- **Lab04:** escolha do teste pela escala, simulação de poder, intervalos de proporção e "
                    "dashboard.")

# ----------------------------------------------------------------------------------------------------- limites
with limites:
    st.markdown("##### Ameaças à validade e como foram tratadas")
    st.markdown(painel.tabela_md(painel.AMEACAS))
    st.markdown("##### O que o estudo não afirma")
    for x in painel.nao_afirma(d):
        st.markdown(f"- {x}")
    st.markdown("##### Para reproduzir")
    st.code(painel.REPRODUZIR, language="bash")
