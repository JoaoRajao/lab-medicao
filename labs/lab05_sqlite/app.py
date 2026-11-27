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

st.set_page_config(page_title="Lab05 · SQLite", layout="wide")


@st.cache_data
def dados() -> dict:
    return painel.carregar()


d = dados()
n = painel.numeros(d)
_n, _vezes, _ms = robustez._n, robustez._vezes, robustez._ms

# ------------------------------------------------------------------------------------------ resposta primeiro
st.title("SQLite: qual configuração usar?")
st.caption(f"Lab05 · Laboratório de Experimentação de Software · [repositório]({painel.REPOSITORIO}) · "
           f"[GitHub Projects]({painel.PROJECTS})")
with st.container(border=True):
    st.markdown(f"#### A resposta\n{painel.veredito(n)}")

def numero(coluna, rotulo: str, valor: str, comparacao: str, ajuda: str) -> None:
    """Numero de manchete com a comparacao em texto (sem a seta do st.metric, que sugeriria 'subiu')."""
    with coluna:
        st.metric(rotulo, valor, help=ajuda)
        st.caption(comparacao)


c1, c2, c3, c4 = st.columns(4)
numero(c1, "Gravação com WAL", f"{_vezes(n['h1'])} mais rápida", "que o padrão DELETE/FULL",
       f"H-1, razão das medianas WAL/FULL ÷ DELETE/FULL; IC 95% {_n(n['h1_inf'])}–{_n(n['h1_sup'])}")
numero(c2, "Perdas em queda de energia",
       f"{int(n['perda_wal']['rodadas_com_perda'])} de {int(n['perda_wal']['rodadas'])}",
       f"no WAL/FULL · padrão: {int(n['perda_padrao']['rodadas_com_perda'])} de {int(n['perda_padrao']['rodadas'])}",
       "Quedas do sistema simuladas no Linux em que alguma transação confirmada sumiu")
numero(c3, "Tela lida enquanto grava", f"{_n(n['telas_wal'], 0)} de 600",
       f"no WAL · padrão: {_n(n['telas_delete'], 0)} de 600",
       f"Telas de 50 linhas lidas em 3 s com escrita em segundo plano ({n['conc_ambiente']})")
numero(c4, "Ambientes que repetem a direção", f"{n['ambientes']}",
       f"{n['direcao']} de {n['pares']} comparações",
       "Notebook (Windows e WSL2), GitHub Actions (Ubuntu, Windows, macOS) e iPhone 11")

evid, decida, metodo, limites = st.tabs(["Evidências", "Decida para o seu app", "Como medimos", "Limites"])

# ------------------------------------------------------------------------------------------------ evidencias
with evid:
    st.plotly_chart(painel.efeitos(d["testes"]), width="stretch")
    st.markdown(f"**Leitura:** o WAL grava {_vezes(n['h1'])} mais rápido e o `synchronous = NORMAL` acelera o WAL "
                f"em {_vezes(n['h3'])}, mas esse ganho tem custo (abaixo). Lendo tudo numa transação (E-1), "
                "a diferença entre WAL e DELETE some: a vantagem do WAL na leitura avulsa vem do custo de abrir "
                "cada transação.")
    esq, dir_ = st.columns(2)
    with esq:
        st.plotly_chart(painel.durabilidade(d["durabilidade"]), width="stretch")
        st.markdown(f"Travar o app não perdeu nada em nenhuma configuração ({n['processo_perdas']} de "
                    f"{n['processo_rodadas']}). Na queda de energia, o padrão perdeu a última transação "
                    f"confirmada em {int(n['perda_padrao']['rodadas_com_perda'])} de "
                    f"{int(n['perda_padrao']['rodadas'])} vezes; o `WAL/NORMAL` perdeu até "
                    f"{int(n['perda_normal']['perdidas_max'])} de uma vez. Nenhum banco corrompeu.")
    with dir_:
        st.plotly_chart(painel.concorrencia(d["concorrencia"]), width="stretch")
        st.markdown(f"No DELETE, quem grava bloqueia quem lê: a pior leitura levou {painel._tempo(n['pior_delete'])} "
                    f"(um quadro tem 16 ms). No WAL, {_ms(n['pior_wal'])}.")
    st.plotly_chart(painel.replicacao(d["replicacao"]), width="stretch")
    st.markdown(f"A direção se repete em {n['direcao']} de {n['pares']} comparações. A exceção é E-1, cujo efeito "
                "é praticamente nulo em todos os ambientes. A magnitude muda bastante de um ambiente para outro.")

# ------------------------------------------------------------------------------------------------- calculadora
with decida:
    calculadora.render(st, d["calculadora"])

# ------------------------------------------------------------------------------------------------------ metodo
with metodo:
    a, b = st.columns([3, 2])
    with a:
        st.markdown(
            "#### Pergunta\nQuanto o modo de journal (`WAL` × `DELETE`) e a sincronização (`FULL` × `NORMAL`) mudam "
            "a velocidade de gravação e de leitura do SQLite, e o que se perde em durabilidade em troca?\n\n"
            "#### Por que o SQLite\n- **Real:** site, documentação e código mantidos pelo fornecedor.\n"
            "- **Em operação:** versões novas em 2026; embutido no Android, iOS, Windows, Chrome, Firefox e "
            "Python.\n- **Alto impacto:** mais de 1 trilhão de bancos em uso, segundo o fornecedor "
            "([sqlite.org/mostdeployed](https://www.sqlite.org/mostdeployed.html)).\n\n"
            "#### Como foi feito\n"
            "1. **Desempenho:** fatorial 2 × 2 em 30 blocos com ordem sorteada, banco novo por medição, três "
            "cargas (escrita, leitura avulsa, leitura em uma transação). Wilcoxon pareado com Holm e razão das "
            "medianas com IC por *bootstrap*.\n"
            "2. **Durabilidade:** 250 falhas provocadas, processo encerrado à força e queda do sistema "
            "(`sysrq b`), contando as transações confirmadas que sumiram.\n"
            "3. **Concorrência:** leitura de uma lista enquanto outra conexão grava, com hipóteses registradas "
            "antes da coleta.\n"
            "4. **Replicação:** a coleta completa em 6 ambientes.\n"
            "5. **Pesquisa documental:** a configuração que Android, Apple, Firefox e Python usam em produção.\n\n"
            "**Ética:** tudo roda no ambiente do grupo; nenhum sistema de terceiros recebe carga e nenhum dado "
            "pessoal é coletado.")
    with b:
        st.markdown("#### 7 categorias da pesquisa")
        st.markdown(painel.tabela_md(painel.CATEGORIAS))
        st.markdown("#### Reaproveitado dos labs\n- **Lab01:** coleta por script e Kanban no GitHub Projects.\n"
                    "- **Lab02:** tratamentos, piloto antes da coleta completa.\n"
                    "- **Lab04:** escolha do teste pela escala, simulação de poder, intervalos de proporção e "
                    "dashboard.")

# ----------------------------------------------------------------------------------------------------- limites
with limites:
    st.markdown("#### Ameaças à validade e como foram tratadas")
    st.markdown(painel.tabela_md(painel.AMEACAS))
    st.markdown("#### O que o estudo não afirma")
    for x in painel.nao_afirma(d):
        st.markdown(f"- {x}")
    st.markdown("#### Para reproduzir")
    st.code(painel.REPRODUZIR, language="bash")
