"""Dados, graficos e textos do dashboard final do Lab05 (formato explicativo: a resposta primeiro).

Tudo sai dos arquivos versionados: a analise principal (data/processed/testes_hipoteses.csv, #122), a
replicacao, a durabilidade e a concorrencia (robustez.py, #137). Nenhum numero e digitado a mao.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from labs.lab05_sqlite import calculadora, cores, robustez

PROCESSADOS = robustez.PROCESSADOS
REPOSITORIO = "https://github.com/JoaoRajao/lab-medicao"
PROJECTS = "https://github.com/users/JoaoRajao/projects/4"

# rotulos em linguagem simples; o codigo da hipotese fica no fim, para quem quiser conferir
ROTULOS = {
    "H-1": "Gravação: WAL × DELETE  (H-1)",
    "H-2": "Leitura avulsa: WAL × DELETE  (H-2)",
    "H-3": "Gravação no WAL: NORMAL × FULL  (H-3)",
    "Exp-1": "Leitura em 1 transação: WAL × DELETE  (E-1)",
    "Exp-2": "Gravação no DELETE: NORMAL × FULL  (E-2)",
}
ROTULOS["E-1"], ROTULOS["E-2"] = ROTULOS["Exp-1"], ROTULOS["Exp-2"]
ORDEM = ["H-1", "H-2", "H-3", "E-1", "E-2"]

GLOSSARIO = [
    ("`DELETE` (padrão)", "antes de alterar o banco, o SQLite copia o conteúdo original para um arquivo à parte (o "
                          "*journal*) e o apaga no fim. Enquanto alguém grava, ninguém lê."),
    ("`WAL`", "as alterações vão para um arquivo de registro (*write-ahead log*) e só depois para o banco. Quem lê "
              "continua lendo enquanto alguém grava."),
    ("`FULL` (padrão)", "a cada transação, espera o disco confirmar que gravou. Mais seguro, mais lento."),
    ("`NORMAL`", "espera o disco menos vezes. Mais rápido, mas pode perder as transações mais recentes numa queda de "
                 "energia."),
    ("`EXTRA`", "como o `FULL`, e ainda confirma no disco que o *journal* foi apagado."),
    ("Razão", "quantas vezes mais operações por segundo uma configuração faz que a outra. 1× = igual."),
]


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
        "integras": int(d["durabilidade"]["integras"].sum()), "falhas": int(d["durabilidade"]["rodadas"].sum()),
        "telas_delete": conc["telas_delete"], "telas_wal": conc["telas_wal"],
        "pior_delete": conc["pior_delete_ms"], "pior_wal": conc["pior_wal_ms"], "conc_ambiente": conc["ambiente"],
        "ambientes": int(comp["ambientes"].max()), "direcao": int(comp["mesma_direcao"].sum()),
        "pares": int(comp["ambientes"].sum()),
        "tem_iphone": bool(d["replicacao"]["ambiente"].str.contains("iPhone").any()),
    }


# ------------------------------------------------------------------------------------------------- graficos
def _layout(fig: go.Figure, titulo: str, altura: int, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        title={"text": f"<b>{titulo}</b>", "x": 0, "xanchor": "left", "y": 0.98, "yanchor": "top",
               "font": {"size": 17}},
        height=altura, margin={"l": 10, "r": 30, "t": 60 if not legenda else 95, "b": 55},
        font={"family": cores.FONTE, "color": cores.TEXTO, "size": 14},
        plot_bgcolor="white", paper_bgcolor="white", showlegend=legenda,
        legend={"orientation": "h", "x": 0, "xanchor": "left", "y": 1.0, "yanchor": "bottom",
                "font": {"size": 13}, "itemclick": "toggle", "itemdoubleclick": "toggleothers"},
        hoverlabel={"font": {"family": cores.FONTE, "size": 13}, "bgcolor": "white"})
    fig.update_xaxes(gridcolor=cores.GRADE, zeroline=False, linecolor=cores.GRADE,
                     title_font={"size": 13, "color": cores.TEXTO_SECUNDARIO})
    fig.update_yaxes(gridcolor=cores.GRADE, zeroline=False, linecolor=cores.GRADE, ticks="")
    return fig


def _eixo_vezes(fig: go.Figure, maximo: float = 500) -> None:
    """Eixo log so com marcas redondas (1x 2x 5x 10x ...), sem as marcas menores que poluem."""
    marcas = [m for m in (0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500) if m <= maximo]
    texto = [f"{robustez._n(m, 0 if m >= 1 else 1)}×" + ("<br>igual" if m == 1 else "") for m in marcas]
    fig.update_xaxes(type="log", tickvals=marcas, ticktext=texto,
                     minor={"showgrid": False, "ticks": ""})


def _linha_de_igualdade(fig: go.Figure) -> None:
    """Linha pontilhada em 1x; o significado ("igual") vai na propria marca do eixo, sem anotacao solta."""
    fig.add_vline(x=1, line={"color": cores.REFERENCIA, "dash": "dot", "width": 1.5})


def efeitos(testes: pd.DataFrame) -> go.Figure:
    """Grafico de floresta: razao das medianas com IC 95%, em escala log; a linha em 1x e "sem diferenca"."""
    t = testes.set_index("codigo").loc[[c if c in testes["codigo"].values else c.replace("E-", "Exp-")
                                        for c in ORDEM]].reset_index().iloc[::-1]
    fig = go.Figure()
    _linha_de_igualdade(fig)
    for significativo, nome, cor in ((True, "diferença significativa (Holm)", cores.SIGNIFICATIVO),
                                     (False, "sem diferença detectável", cores.NAO_SIGNIFICATIVO)):
        g = t[t["rejeita_h0"] == significativo]
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=g["razao_medianas"], y=[ROTULOS[c] for c in g["codigo"]], mode="markers+text", name=nome,
            marker={"size": 15, "color": cor, "line": {"color": "white", "width": 2}},
            error_x={"type": "data", "symmetric": False, "array": g["ic95_razao_sup"] - g["razao_medianas"],
                     "arrayminus": g["razao_medianas"] - g["ic95_razao_inf"], "color": cor, "thickness": 2.5,
                     "width": 6},
            text=[f"<b>{robustez._vezes(x)}</b>" for x in g["razao_medianas"]], textposition="top center",
            textfont={"color": cores.TEXTO, "size": 14},
            customdata=list(zip(g["ic95_razao_inf"], g["ic95_razao_sup"],
                                g["p_holm"].fillna(g["p_wilcoxon"]))),
            hovertemplate="<b>%{y}</b><br>razão %{x:.2f}× (IC 95%: %{customdata[0]:.2f}–%{customdata[1]:.2f})"
                          "<br>p = %{customdata[2]:.2g}<extra></extra>"))
    _eixo_vezes(fig)
    fig.update_xaxes(title="quantas vezes mais operações por segundo (escala log) · barra = intervalo de confiança 95%")
    fig.update_yaxes(categoryorder="array", categoryarray=[ROTULOS[c] for c in reversed(ORDEM)],
                     range=[-0.6, len(ORDEM) - 0.2])
    return _layout(fig, "Quanto cada troca muda o desempenho", 430, legenda=True)


def _rotulo_config(j: str, s: str) -> str:
    return f"{j}/{s}" + ("  (padrão)" if (j, s) == calculadora.PADRAO else "")


def durabilidade(resumo: pd.DataFrame) -> go.Figure:
    """Proporcao de quedas de energia com perda, com IC exato, por configuracao (cada uma com sua cor)."""
    s = resumo[resumo["falha"] == "sistema"]
    ordem = [("DELETE", "FULL"), ("DELETE", "NORMAL"), ("DELETE", "EXTRA"), ("WAL", "FULL"), ("WAL", "NORMAL")]
    s = s.set_index(["journal_mode", "synchronous"]).loc[[o for o in ordem if o in s.set_index(
        ["journal_mode", "synchronous"]).index]].reset_index().iloc[::-1]
    rotulos = [_rotulo_config(j, y) for j, y in zip(s["journal_mode"], s["synchronous"])]
    textos = [f"<b>{k} de {n}</b>" + (f" · até {m} transações por queda" if m > 1 else
                                     " · só a última transação" if k > 0 else " · nenhuma perda")
              for k, n, m in zip(s["rodadas_com_perda"], s["rodadas"], s["perdidas_max"])]
    cor = [cores.config(j, y) for j, y in zip(s["journal_mode"], s["synchronous"])]
    fig = go.Figure(go.Scatter(
        x=100 * s["proporcao"], y=rotulos, mode="markers",
        marker={"size": 16, "color": cor, "line": {"color": "white", "width": 2}},
        error_x={"type": "data", "symmetric": False, "array": 100 * (s["ic_sup"] - s["proporcao"]),
                 "arrayminus": 100 * (s["proporcao"] - s["ic_inf"]), "color": cores.TEXTO_SECUNDARIO,
                 "thickness": 2, "width": 6},
        customdata=textos, hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>"))
    # rotulo depois do fim do intervalo, para nao ficar em cima da linha
    fig.add_trace(go.Scatter(x=100 * s["ic_sup"] + 4, y=rotulos, mode="text", text=textos,
                             textposition="middle right", textfont={"color": cores.TEXTO}, hoverinfo="skip"))
    fig.update_xaxes(range=[-5, 190], tickvals=[0, 25, 50, 75, 100], ticktext=["0%", "25%", "50%", "75%", "100%"],
                     title="quedas de energia em que alguma transação confirmada sumiu · barra = IC 95% exato")
    return _layout(fig, "Quem perde dados numa queda de energia", 380)


def _tempo(ms: float) -> str:
    return f"{robustez._n(ms / 1000, 1)} s" if ms >= 1000 else robustez._ms(ms)


def concorrencia(replica: pd.DataFrame) -> go.Figure:
    """Telas lidas em 3 s com escrita em segundo plano, por ambiente: DELETE/FULL x WAL/FULL."""
    ambientes = [a.replace(" (processos)", "").replace(" (threads)", "") for a in replica["ambiente"]]
    fig = go.Figure()
    for j, coluna, pior in (("DELETE", "telas_delete", "pior_delete_ms"), ("WAL", "telas_wal", "pior_wal_ms")):
        fig.add_trace(go.Bar(
            y=ambientes, x=replica[coluna], name=_rotulo_config(j, "FULL"), orientation="h",
            marker={"color": cores.config(j, "FULL")},
            text=[f"<b>{robustez._n(v, 0)} de 600</b> · pior leitura {_tempo(p)}"
                  for v, p in zip(replica[coluna], replica[pior])],
            textposition="outside", textfont={"color": cores.TEXTO}, cliponaxis=False,
            hovertemplate="<b>%{y}</b> · " + _rotulo_config(j, "FULL") + "<br>%{x:.0f} de 600 telas<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.1)
    fig.update_xaxes(range=[0, 1100], tickvals=[0, 150, 300, 450, 600],
                     title="telas de 50 linhas lidas em 3 s (o máximo é 600: uma a cada 5 ms)")
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, "A tela trava quando o app grava ao mesmo tempo?", 360, legenda=True)


def replicacao(rep: pd.DataFrame) -> go.Figure:
    """Uma linha por comparacao; dentro dela, um ponto por ambiente, cada um com cor e formato proprios."""
    ambientes = list(dict.fromkeys(rep["ambiente"]))
    deslocamento = {a: (i - (len(ambientes) - 1) / 2) * 0.12 for i, a in enumerate(ambientes)}
    posicao = {c: len(ORDEM) - 1 - i for i, c in enumerate(ORDEM)}
    fig = go.Figure()
    _linha_de_igualdade(fig)
    for ambiente in ambientes:
        g = rep[rep["ambiente"] == ambiente]
        fig.add_trace(go.Scatter(
            x=g["razao"], y=[posicao[c] - deslocamento[ambiente] for c in g["codigo"]], mode="markers",
            name=ambiente, marker={"size": 12, "color": cores.AMBIENTE.get(ambiente, cores.TEXTO_SECUNDARIO),
                                   "symbol": cores.simbolo_ambiente(ambiente),
                                   "line": {"color": "white", "width": 1}},
            customdata=[ROTULOS[c] for c in g["codigo"]],
            hovertemplate=f"<b>{ambiente}</b><br>%{{customdata}}: %{{x:.2f}}×<extra></extra>"))
    for i in range(len(ORDEM) - 1):  # faixas para separar as comparacoes
        fig.add_hline(y=i + 0.5, line={"color": cores.GRADE, "width": 1})
    _eixo_vezes(fig)
    fig.update_xaxes(title="quantas vezes mais operações por segundo (escala log)")
    fig.update_yaxes(tickvals=list(posicao.values()), ticktext=[ROTULOS[c] for c in posicao],
                     range=[-0.6, len(ORDEM) - 0.4], showgrid=False)
    fig = _layout(fig, "O resultado se repete em outros ambientes?", 470, legenda=True)
    fig.update_layout(legend={"y": 1.0, "title": {"text": "◆ notebook · ■ GitHub Actions · ● celular   ",
                                                  "font": {"size": 12, "color": cores.TEXTO_SECUNDARIO}}})
    return fig


# --------------------------------------------------------------------------------------------------- textos
def resposta(n: dict) -> dict:
    """A resposta em uma frase e tres pontos, cada um com o numero que o sustenta."""
    pw, pp = n["perda_wal"], n["perda_padrao"]
    tela = (f"leu **{robustez._n(n['telas_wal'], 0)} de 600** telas enquanto gravava, contra "
            f"**{robustez._n(n['telas_delete'], 0)}** do padrão")
    return {
        "frase": "Troque o padrão do SQLite (`DELETE/FULL`) por **`WAL/FULL`**.",
        "pontos": [
            f"⚡ **Mais rápido:** grava **{robustez._vezes(n['h1'])}** mais rápido que o padrão.",
            f"🛡️ **Mais seguro:** perdeu dados em **{int(pw['rodadas_com_perda'])} de {int(pw['rodadas'])}** "
            f"quedas de energia simuladas; o padrão, em **{int(pp['rodadas_com_perda'])} de "
            f"{int(pp['rodadas'])}**.",
            f"📱 **Não trava a tela:** {tela}." if n["telas_wal"] >= 600 > n["telas_delete"]
            else f"📱 **Tela:** {tela}.",
        ],
        "replicacao": f"A direção dos resultados se repetiu em **{n['direcao']} de {n['pares']}** comparações, em "
                      f"**{n['ambientes']} ambientes**" + (", incluindo um iPhone." if n["tem_iphone"] else "."),
    }


def veredito(n: dict) -> str:
    r = resposta(n)
    return " ".join([r["frase"], *r["pontos"], r["replicacao"]])


CATEGORIAS = pd.DataFrame([
    ("Natureza", "**Aplicada**", "Responde a uma decisão prática de configuração de quem desenvolve apps e sistemas."),
    ("Objetivos", "**Explicativa**", "Busca causa e efeito entre configuração e desempenho, manipulando a "
                                     "configuração (com parte descritiva)."),
    ("Abordagem", "**Quantitativa**", "Métricas em escala de razão (vazão, latência) e contagens (transações "
                                      "perdidas)."),
    ("Procedimentos", "**Experimental + documental**", "Experimentos controlados (desempenho, durabilidade, "
                                                      "concorrência) e configurações de produção em fontes oficiais."),
    ("Tempo", "**Transversal**", "Medições em uma janela curta, com as versões atuais de cada ambiente."),
    ("Controle", "**Laboratório**", "Blocos com ordem sorteada, banco novo por medição, falhas provocadas de forma "
                                    "controlada."),
    ("Nível de evidência", "**Alto (interna) · moderado (externa)**", "Causalidade sustentada pelo desenho "
                                                                     "aleatorizado; direção replicada em 6 "
                                                                     "ambientes, magnitude não."),
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
            f"A magnitude muda muito de ambiente para ambiente: o ganho do `NORMAL` vai de "
            f"{robustez._vezes(h3['razao_min'])} a {robustez._vezes(h3['razao_max'])}. Afirmamos a direção, não um "
            "número universal.",
            *NAO_AFIRMA[1:]]


NAO_AFIRMA = [
    "A queda de energia foi simulada só no Linux (`sysrq b`); no iPhone e no GitHub Actions não é possível simular.",
    "Não medimos apps reais em produção, só cargas sintéticas que imitam o padrão de um app.",
    "No iPhone e no macOS, o `FULL` não força a gravação física por padrão (`fullfsync`): o custo do `FULL` ali é "
    "menor, e a durabilidade não foi testada.",
]

REPRODUZIR = """python -m labs.lab05_sqlite.coleta --repeticoes 30 --nome coleta_completa   # desempenho (~4 min)
python -m labs.lab05_sqlite.analise                                          # testes de hipótese (#122)
python -m labs.lab05_sqlite.durabilidade                                     # 250 falhas (~30 min, WSL2)
python -m labs.lab05_sqlite.concorrencia                                     # leitura x escrita (~15 min)
python -m labs.lab05_sqlite.robustez                                         # replicação e relatório
streamlit run labs/lab05_sqlite/app.py                                       # este dashboard"""
