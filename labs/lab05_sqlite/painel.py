"""Dados, graficos e textos do dashboard final do Lab05 (formato explicativo: a resposta primeiro).

Tudo sai dos arquivos versionados: a analise principal (data/processed/testes_hipoteses.csv, #122), a
replicacao, a durabilidade e a concorrencia (robustez.py, #137). Nenhum numero e digitado a mao.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from labs.lab05_sqlite import calculadora, robustez

PROCESSADOS = robustez.PROCESSADOS
REPOSITORIO = "https://github.com/JoaoRajao/lab-medicao"
PROJECTS = "https://github.com/users/JoaoRajao/projects/4"

# Paleta do grupo (Lab04): azul e laranja sao o par seguro para daltonismo; a identidade nunca depende so da cor
COR = {"WAL": "#2a78d6", "DELETE": "#eb6834"}
COR_NEUTRA = "#898781"
COR_TEXTO = "#3d3c38"
COR_GRADE = "#e6e4df"
FONTE = "Source Sans Pro, Arial, sans-serif"

ROTULOS = {
    "H-1": "H-1 · Escrita: WAL ÷ DELETE",
    "H-2": "H-2 · Leitura avulsa: WAL ÷ DELETE",
    "H-3": "H-3 · Escrita no WAL: NORMAL ÷ FULL",
    "Exp-1": "E-1 · Leitura em 1 transação: WAL ÷ DELETE",
    "Exp-2": "E-2 · Escrita no DELETE: NORMAL ÷ FULL",
    "E-1": "E-1 · Leitura em 1 transação: WAL ÷ DELETE",
    "E-2": "E-2 · Escrita no DELETE: NORMAL ÷ FULL",
}


# ---------------------------------------------------------------------------------------------------- dados
def carregar() -> dict:
    testes = pd.read_csv(PROCESSADOS / "testes_hipoteses.csv")
    rep = robustez.replicacao(robustez.carregar_coletas())
    dur = robustez.resumo_durabilidade(robustez.carregar_durabilidade())
    return {"testes": testes, "replicacao": rep, "comparacao": robustez.comparar_ambientes(rep),
            "durabilidade": dur, "concorrencia": robustez.replica_concorrencia(),
            "calculadora": calculadora.carregar()}


def numeros(d: dict) -> dict:
    """Os numeros das manchetes, todos tirados dos dados."""
    t = d["testes"].set_index("codigo")
    sist = d["durabilidade"][d["durabilidade"]["falha"] == "sistema"].set_index(["journal_mode", "synchronous"])
    proc = d["durabilidade"][d["durabilidade"]["falha"] == "processo"]
    conc = d["concorrencia"].iloc[0]
    comp = d["comparacao"]
    return {
        "h1": t.loc["H-1", "razao_medianas"], "h1_inf": t.loc["H-1", "ic95_razao_inf"],
        "h1_sup": t.loc["H-1", "ic95_razao_sup"], "h3": t.loc["H-3", "razao_medianas"],
        "perda_padrao": sist.loc[("DELETE", "FULL")], "perda_wal": sist.loc[("WAL", "FULL")],
        "perda_normal": sist.loc[("WAL", "NORMAL")], "processo_perdas": int(proc["rodadas_com_perda"].sum()),
        "processo_rodadas": int(proc["rodadas"].sum()),
        "telas_delete": conc["telas_delete"], "telas_wal": conc["telas_wal"],
        "pior_delete": conc["pior_delete_ms"], "pior_wal": conc["pior_wal_ms"], "conc_ambiente": conc["ambiente"],
        "ambientes": int(comp["ambientes"].max()), "direcao": int(comp["mesma_direcao"].sum()),
        "pares": int(comp["ambientes"].sum()),
        "tem_iphone": d["replicacao"]["ambiente"].str.contains("iPhone").any(),
    }


# ------------------------------------------------------------------------------------------------- graficos
def _layout(fig: go.Figure, titulo: str, subtitulo: str, altura: int) -> go.Figure:
    fig.update_layout(
        title={"text": f"<b>{titulo}</b><br><span style='font-size:13px;color:{COR_NEUTRA}'>{subtitulo}</span>",
               "x": 0, "xanchor": "left", "y": 0.97, "yanchor": "top"},
        height=altura, margin={"l": 10, "r": 30, "t": 80, "b": 50}, font={"family": FONTE, "color": COR_TEXTO,
                                                                            "size": 13},
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False, hoverlabel={"font": {"family": FONTE}})
    fig.update_xaxes(gridcolor=COR_GRADE, zeroline=False, linecolor=COR_GRADE)
    fig.update_yaxes(gridcolor=COR_GRADE, zeroline=False, linecolor=COR_GRADE)
    return fig


def _eixo_vezes(fig: go.Figure) -> None:
    """Eixo log so com marcas redondas (0,5x 1x 2x 5x 10x ...), sem as marcas menores que poluem."""
    marcas = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
    fig.update_xaxes(type="log", tickvals=marcas, ticktext=[f"{robustez._n(m, 0 if m >= 1 else 1)}×" for m in marcas],
                     minor={"showgrid": False, "ticks": ""})


def efeitos(testes: pd.DataFrame) -> go.Figure:
    """Grafico de floresta: razao das medianas com IC 95%, em escala log; a linha em 1x e "sem diferenca"."""
    t = testes.iloc[::-1]
    rotulos = [ROTULOS.get(c, c) for c in t["codigo"]]
    cor = [COR["WAL"] if r else COR_NEUTRA for r in t["rejeita_h0"]]
    fig = go.Figure()
    fig.add_vline(x=1, line={"color": COR_NEUTRA, "dash": "dot", "width": 1})
    fig.add_trace(go.Scatter(
        x=t["razao_medianas"], y=rotulos, mode="markers+text",
        marker={"size": 13, "color": cor, "line": {"color": "white", "width": 2}},
        error_x={"type": "data", "symmetric": False, "array": t["ic95_razao_sup"] - t["razao_medianas"],
                 "arrayminus": t["razao_medianas"] - t["ic95_razao_inf"], "color": COR_TEXTO, "thickness": 2,
                 "width": 0},
        text=[robustez._vezes(x) for x in t["razao_medianas"]], textposition="top center",
        textfont={"color": COR_TEXTO, "size": 13},
        customdata=list(zip(t["ic95_razao_inf"], t["ic95_razao_sup"], t["p_holm"].fillna(t["p_wilcoxon"]))),
        hovertemplate="%{y}<br>razão %{x:.3f}× · IC 95% %{customdata[0]:.3f}–%{customdata[1]:.3f}"
                      "<br>p %{customdata[2]:.2g}<extra></extra>"))
    _eixo_vezes(fig)
    fig.update_xaxes(title="razão das medianas de operações por segundo (escala log; 1× = sem diferença)")
    fig.update_yaxes(range=[-0.6, len(t) - 0.3])
    return _layout(fig, "Quanto cada troca muda o desempenho",
                   "Notebook com Windows · 30 blocos pareados · ponto azul = diferença significativa (Holm), "
                   "cinza = não", 400)


def durabilidade(resumo: pd.DataFrame) -> go.Figure:
    """Proporcao de quedas de energia com perda, com IC exato, por configuracao."""
    s = resumo[resumo["falha"] == "sistema"].iloc[::-1]
    rotulos = [f"{j}/{y}" + (" (padrão)" if (j, y) == calculadora.PADRAO else "")
               for j, y in zip(s["journal_mode"], s["synchronous"])]
    textos = [f"{k} de {n}" + (f" · até {m} transações" if m > 1 else "")
              for k, n, m in zip(s["rodadas_com_perda"], s["rodadas"], s["perdidas_max"])]
    fig = go.Figure(go.Scatter(
        x=100 * s["proporcao"], y=rotulos, mode="markers",
        marker={"size": 14, "color": [COR[j] for j in s["journal_mode"]], "line": {"color": "white", "width": 2}},
        error_x={"type": "data", "symmetric": False, "array": 100 * (s["ic_sup"] - s["proporcao"]),
                 "arrayminus": 100 * (s["proporcao"] - s["ic_inf"]), "color": COR_TEXTO, "thickness": 2, "width": 0},
        customdata=textos, hovertemplate="%{y}: %{customdata}<extra></extra>"))
    # rotulo depois do fim do intervalo, para nao ficar em cima da linha
    fig.add_trace(go.Scatter(x=100 * s["ic_sup"] + 4, y=rotulos, mode="text", text=textos,
                             textposition="middle right", textfont={"color": COR_TEXTO}, hoverinfo="skip"))
    fig.update_xaxes(range=[-5, 175], title="quedas com perda de transação confirmada (%) · IC 95% exato",
                     tickvals=[0, 25, 50, 75, 100])
    return _layout(fig, "Quem perde dados numa queda de energia",
                   "Linux · 20 quedas simuladas por configuração · laranja = DELETE, azul = WAL", 360)


def _tempo(ms: float) -> str:
    return f"{robustez._n(ms / 1000, 1)} s" if ms >= 1000 else robustez._ms(ms)


def concorrencia(replica: pd.DataFrame) -> go.Figure:
    """Telas lidas em 3 s com escrita em segundo plano, por ambiente: DELETE x WAL."""
    ambientes = [a.replace(" (processos)", "").replace(" (threads)", "") for a in replica["ambiente"]]
    fig = go.Figure()
    for modo, coluna, pior in (("DELETE", "telas_delete", "pior_delete_ms"), ("WAL", "telas_wal", "pior_wal_ms")):
        fig.add_trace(go.Bar(
            y=ambientes, x=replica[coluna], name=modo, orientation="h", marker={"color": COR[modo]},
            text=[f"{modo}: {robustez._n(v, 0)} de 600 · pior {_tempo(p)}"
                  for v, p in zip(replica[coluna], replica[pior])],
            textposition="outside", textfont={"color": COR_TEXTO}, cliponaxis=False,
            hovertemplate="%{y} · " + modo + ": %{x:.0f} de 600 telas<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.12)
    fig.update_xaxes(range=[0, 1050], tickvals=[0, 150, 300, 450, 600],
                     title="telas lidas em 3 s, de 600 possíveis (synchronous = FULL)")
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, "A tela trava quando o app grava ao mesmo tempo?",
                   "Leitura de uma lista a cada 5 ms com uma sincronização gravando em segundo plano", 330)


def replicacao(rep: pd.DataFrame) -> go.Figure:
    """Cada ponto e um ambiente; a referencia (notebook com Windows) aparece destacada."""
    fig = go.Figure()
    fig.add_vline(x=1, line={"color": COR_NEUTRA, "dash": "dot", "width": 1})
    for ambiente, g in rep.groupby("ambiente", sort=False):
        ref = ambiente == robustez.REFERENCIA
        fig.add_trace(go.Scatter(
            x=g["razao"], y=[ROTULOS.get(c, c) for c in g["codigo"]], mode="markers", name=ambiente,
            marker={"size": 13 if ref else 10, "symbol": "diamond" if ref else "circle",
                    "color": COR_TEXTO if ref else COR_NEUTRA, "opacity": 1 if ref else 0.7,
                    "line": {"color": "white", "width": 1.5}},
            hovertemplate=f"{ambiente}<br>%{{y}}: %{{x:.2f}}×<extra></extra>"))
    _eixo_vezes(fig)
    fig.update_xaxes(title="razão das medianas (escala log; 1× = sem diferença)")
    fig.update_yaxes(categoryorder="array", categoryarray=[ROTULOS[c] for c in ("E-2", "E-1", "H-3", "H-2", "H-1")])
    return _layout(fig, "O resultado se repete em outros ambientes?",
                   "◆ notebook com Windows (referência) · ● WSL2, GitHub Actions (Ubuntu, Windows, macOS) e "
                   "iPhone 11", 380)


# --------------------------------------------------------------------------------------------------- textos
def veredito(n: dict) -> str:
    perda_padrao, perda_wal = n["perda_padrao"], n["perda_wal"]
    return (f"Trocar o padrão do SQLite (`DELETE/FULL`) por **`WAL/FULL`** deixa a gravação "
            f"**{robustez._vezes(n['h1'])} mais rápida**, não perdeu nenhuma transação confirmada nas quedas de "
            f"energia simuladas ({int(perda_wal['rodadas_com_perda'])} de {int(perda_wal['rodadas'])}, contra "
            f"{int(perda_padrao['rodadas_com_perda'])} de {int(perda_padrao['rodadas'])} do padrão) e "
            + ("**não trava a tela** enquanto grava" if n["telas_wal"] >= 600 > n["telas_delete"]
               else f"leu {robustez._n(n['telas_wal'], 0)} de 600 telas enquanto gravava")
            + f". A direção se repetiu em {n['direcao']} de {n['pares']} comparações em {n['ambientes']} ambientes"
            + (", incluindo um iPhone." if n["tem_iphone"] else "."))


CATEGORIAS = pd.DataFrame([
    ("Natureza", "Aplicada", "Responde a uma decisão prática de configuração de quem desenvolve apps e sistemas."),
    ("Objetivos", "Explicativa (com parte descritiva)", "Busca causa e efeito entre configuração e desempenho, "
                                                        "manipulando a configuração."),
    ("Abordagem", "Quantitativa", "Métricas em escala de razão (vazão, latência) e contagens (transações perdidas)."),
    ("Procedimentos", "Experimental + pesquisa documental", "Experimentos controlados (desempenho, durabilidade, "
                                                           "concorrência) e configurações de produção em fontes "
                                                           "oficiais."),
    ("Tempo", "Transversal", "Medições em uma janela curta, com as versões atuais de cada ambiente."),
    ("Controle", "Experimento controlado em laboratório", "Blocos com ordem sorteada, banco novo por medição, "
                                                          "falhas provocadas de forma controlada."),
    ("Nível de evidência", "Alto (interna) · moderado (externa)", "Causalidade sustentada pelo desenho aleatorizado; "
                                                                  "direção replicada em 6 ambientes, magnitude não."),
], columns=["Categoria", "Classificação", "Por quê"])

AMEACAS = pd.DataFrame([
    ("Conclusão", "Muitas comparações e efeitos pequenos", "Holm nas confirmatórias, tamanho do efeito com IC, "
                                                           "Wilcoxon pareado (robusto a atípicos)."),
    ("Interna", "Ordem, aquecimento e processos em segundo plano", "Blocos com ordem sorteada, banco novo por "
                                                                   "medição, coleta repetida com a máquina ociosa."),
    ("Construto", "Leitura avulsa mede o custo de abrir transação, não só a leitura", "Carga extra de leitura em "
                                                                                      "uma transação (E-1)."),
    ("Construto", "Durabilidade só pela documentação", "Medida: 250 falhas provocadas (processo e queda do sistema)."),
    ("Externa", "Uma máquina, um sistema", "Replicação em 6 ambientes, incluindo GitHub Actions e um iPhone 11."),
    ("Externa", "Carga sintética", "Escopo declarado: transações pequenas, um escritor; não vale para cargas "
                                   "analíticas nem alta concorrência."),
], columns=["Tipo", "Ameaça", "Como foi tratada"])

def tabela_md(df: pd.DataFrame) -> str:
    """Tabela em Markdown: o texto quebra linha, ao contrario do st.dataframe, que corta colunas longas."""
    linhas = ["| " + " | ".join(df.columns) + " |", "| " + " | ".join("---" for _ in df.columns) + " |"]
    linhas += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(linhas)


def nao_afirma(d: dict) -> list[str]:
    h3 = d["comparacao"].set_index("codigo").loc["H-3"]
    return [NAO_AFIRMA[0],
            f"A magnitude muda muito de ambiente para ambiente (o ganho do NORMAL vai de "
            f"{robustez._vezes(h3['razao_min'])} a {robustez._vezes(h3['razao_max'])}): afirmamos a direção.",
            *NAO_AFIRMA[1:]]


NAO_AFIRMA = [
    "A queda de energia foi simulada no Linux (`sysrq b`); no iPhone e no Actions não é possível simular.",
    "Não medimos apps reais em produção, só cargas sintéticas que imitam o padrão de um app.",
    "No iPhone e no macOS, o FULL não força a gravação física por padrão (`fullfsync`), então o custo do FULL ali é "
    "menor e a durabilidade não foi testada.",
]

REPRODUZIR = """python -m labs.lab05_sqlite.coleta --repeticoes 30 --nome coleta_completa   # desempenho (~4 min)
python -m labs.lab05_sqlite.analise                                          # testes de hipótese (#122)
python -m labs.lab05_sqlite.durabilidade                                     # 250 falhas (~30 min, WSL2)
python -m labs.lab05_sqlite.concorrencia                                     # leitura x escrita (~15 min)
python -m labs.lab05_sqlite.robustez                                         # replicação e relatório
streamlit run labs/lab05_sqlite/app.py                                       # este dashboard"""

