"""Calculadora de configuracao do SQLite, a partir dos dados medidos no Lab05 (issue #137).

Quem vai decidir (o "CTO" da apresentacao) informa o perfil do app: quantas gravacoes por minuto, se le enquanto
grava e quanto custa perder a ultima gravacao numa queda de energia. A calculadora mostra o custo e o risco de cada
configuracao no ambiente escolhido e recomenda uma, explicando o porque com os numeros medidos.

Regras (todas transparentes e com os numeros na tela):
    - perda inaceitavel  -> so configuracoes que nao perderam nada na queda do sistema (WAL/FULL; DELETE/EXTRA tambem
                            nao perdeu, mas a velocidade dela nao foi medida na coleta principal);
    - perda toleravel    -> WAL/NORMAL so quando o custo do WAL/FULL pesa (mais de 1% do tempo gravando ou mais de
                            meio quadro por gravacao); senao WAL/FULL, porque a durabilidade sai quase de graca;
    - perda indiferente  -> WAL/NORMAL (cache, dados que podem ser baixados de novo).
Nenhum numero e extrapolado: a perda na queda vem da durabilidade medida no Linux, o bloqueio da leitura vem do
experimento de concorrencia, e o custo por gravacao vem da coleta completa do ambiente escolhido.

    streamlit run labs/lab05_sqlite/app_calculadora.py
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from labs.lab05_sqlite import cores, robustez

QUADRO_MS = 16.0
LIMITE_TEMPO = 0.01        # 1% do tempo gravando
LIMITE_QUADRO = 0.5        # meio quadro por gravacao
PERDAS = {"inaceitavel": "Inaceitável (pagamento, saúde, registro legal)",
          "toleravel": "Ruim, mas tolerável (mensagem, rascunho, preferência)",
          "indiferente": "Indiferente (cache, dado que pode ser baixado de novo)"}
CONFIGS = [("DELETE", "FULL"), ("DELETE", "NORMAL"), ("WAL", "FULL"), ("WAL", "NORMAL")]
PADRAO = ("DELETE", "FULL")  # padrao do SQLite e do modulo sqlite3 do Python


@dataclass(frozen=True)
class Perfil:
    escritas_por_minuto: float
    le_enquanto_grava: bool
    perda: str
    ambiente: str = robustez.REFERENCIA


def carregar() -> dict:
    coletas = robustez.carregar_coletas()
    escrita = coletas[coletas["carga"] == "escrita"]
    latencia = (1000 / escrita.groupby(["ambiente", "journal_mode", "synchronous"])["ops_por_s"].median())
    dur = robustez.resumo_durabilidade(robustez.carregar_durabilidade())
    return {"latencia_ms": latencia, "ambientes": list(dict.fromkeys(coletas["ambiente"])),
            "durabilidade": dur[dur["falha"] == "sistema"].set_index(["journal_mode", "synchronous"]),
            "processo": dur[dur["falha"] == "processo"],
            "concorrencia": robustez.replica_concorrencia()}


def _pct_fino(x: float) -> str:
    """Porcentagem com casas suficientes para nao virar 0% em apps que gravam pouco."""
    casas = 0 if x >= 0.1 else 1 if x >= 0.01 else 2 if x >= 0.001 else 3
    return f"{robustez._n(100 * x, casas)}%"


def _por_minuto(ms: float) -> str:
    return f"{robustez._n(ms / 1000, 1)} s" if ms >= 1000 else f"{robustez._n(ms, 0 if ms >= 10 else 1)} ms"


def _nome(j: str, s: str) -> str:
    return f"{j}/{s}"


def tabela(perfil: Perfil, dados: dict) -> pd.DataFrame:
    """Custo e risco de cada configuracao para o perfil, so com valores medidos."""
    linhas = []
    for j, s in CONFIGS:
        ms = float(dados["latencia_ms"].loc[(perfil.ambiente, j, s)])
        d = dados["durabilidade"].loc[(j, s)]
        linhas.append({
            "Configuração": _nome(j, s) + (" (padrão)" if (j, s) == PADRAO else ""),
            "journal_mode": j, "synchronous": s,
            "ms por gravação": ms,
            "ms gravando por minuto": perfil.escritas_por_minuto * ms,
            "fração do tempo gravando": perfil.escritas_por_minuto * ms / 60_000,
            "fração de um quadro": ms / QUADRO_MS,
            "quedas com perda": f"{int(d['rodadas_com_perda'])} de {int(d['rodadas'])}",
            "perdeu na queda": int(d["rodadas_com_perda"]) > 0,
            "perda máxima": int(d["perdidas_max"]),
            "bloqueia leitura": j == "DELETE",
        })
    return pd.DataFrame(linhas)


def _concorrencia(perfil: Perfil, dados: dict) -> pd.Series | None:
    """Usa a concorrencia medida no mesmo tipo de aparelho; senao, a do notebook."""
    conc = dados.get("concorrencia")
    if conc is None or conc.empty:
        return None
    celular = "iPhone" in perfil.ambiente or "Android" in perfil.ambiente
    for _, linha in conc.iterrows():
        if celular and perfil.ambiente.split(" ")[0] in linha["ambiente"]:
            return linha
    return conc.iloc[0]


def recomendar(perfil: Perfil, dados: dict) -> dict:
    t = tabela(perfil, dados).set_index(["journal_mode", "synchronous"])
    wf, wn, df_ = t.loc[("WAL", "FULL")], t.loc[("WAL", "NORMAL")], t.loc[PADRAO]
    pesa = wf["fração do tempo gravando"] > LIMITE_TEMPO or wf["fração de um quadro"] > LIMITE_QUADRO
    if perfil.perda == "inaceitavel" or (perfil.perda == "toleravel" and not pesa):
        escolha = ("WAL", "FULL")
    else:
        escolha = ("WAL", "NORMAL")
    e = t.loc[escolha]
    ambiente = perfil.ambiente
    motivos = []
    if escolha == ("WAL", "FULL"):
        motivos.append(f"**Não perdeu nenhuma transação confirmada** nas quedas de sistema simuladas "
                       f"({wf['quedas com perda']}).")
        motivos.append(f"Grava **{robustez._vezes(df_['ms por gravação'] / wf['ms por gravação'])} mais rápido** que o "
                       f"padrão `DELETE/FULL` em {ambiente} ({robustez._n(wf['ms por gravação'], 3)} ms contra "
                       f"{robustez._n(df_['ms por gravação'], 3)} ms por gravação).")
        motivos.append(f"Com {robustez._n(perfil.escritas_por_minuto, 0)} gravações por minuto, gasta "
                       f"{_por_minuto(wf['ms gravando por minuto'])} por minuto gravando "
                       f"({_pct_fino(wf['fração do tempo gravando'])} do tempo)"
                       + (", então a durabilidade sai quase de graça." if not pesa else "."))
        if perfil.perda == "toleravel" and not pesa:
            motivos.append(f"O `WAL/NORMAL` seria mais rápido, mas perdeu transações em {wn['quedas com perda']} quedas "
                           "e aqui o ganho não compensa.")
    else:
        motivos.append(f"Grava **{robustez._vezes(wf['ms por gravação'] / wn['ms por gravação'])} mais rápido** que o "
                       f"`WAL/FULL` em {ambiente} ({robustez._n(wn['ms por gravação'], 3)} ms por gravação).")
        if pesa:
            motivos.append(f"Com {robustez._n(perfil.escritas_por_minuto, 0)} gravações por minuto, o `WAL/FULL` passaria "
                           f"{_por_minuto(wf['ms gravando por minuto'])} por minuto gravando "
                           f"({_pct_fino(wf['fração do tempo gravando'])} do tempo) e "
                           f"{robustez._pct(wf['fração de um quadro'])} de um quadro por gravação.")
        motivos.append(f"**O custo:** numa queda de energia perdeu transações confirmadas em {wn['quedas com perda']} "
                       f"quedas (até {wn['perda máxima']} de uma vez, das mais recentes). Aceitável só porque a perda "
                       "foi marcada como tolerável ou indiferente.")
    conc = _concorrencia(perfil, dados)
    if perfil.le_enquanto_grava and conc is not None:
        motivos.append(f"O app lê enquanto grava: com escrita em segundo plano, o leitor do `DELETE/FULL` completou só "
                       f"{robustez._n(conc['telas_delete'], 0)} de 600 telas em 3 s (pior leitura "
                       f"{robustez._ms(conc['pior_delete_ms'])}), contra {robustez._n(conc['telas_wal'], 0)} no WAL "
                       f"(pior {robustez._ms(conc['pior_wal_ms'])}) — medido em {conc['ambiente']}.")
    alertas = []
    if df_["perdeu na queda"]:
        alertas.append(f"O padrão do SQLite e do Python (`DELETE/FULL`) perdeu a última transação confirmada em "
                       f"{df_['quedas com perda']} quedas simuladas. Quem não muda a configuração fica com esse risco.")
    ressalvas = [
        "A perda em queda de energia foi medida no Linux (WSL2) com `sysrq b`; no iPhone e no Actions não dá para "
        "simular queda. O custo por gravação é do ambiente escolhido.",
        "A magnitude muda muito entre ambientes (o ganho do NORMAL vai de 7× a 442×); a direção se repete.",
        "`DELETE/EXTRA` também não perdeu nada nas quedas, mas a velocidade dele não foi medida na coleta principal; "
        "por isso não entra na comparação de custo.",
        "Travar o app (sem queda do sistema) não perdeu dados em nenhuma configuração "
        f"({int(dados['processo']['rodadas_com_perda'].sum())} de {int(dados['processo']['rodadas'].sum())} rodadas).",
    ]
    return {"escolha": escolha, "nome": _nome(*escolha), "linha": e, "motivos": motivos, "alertas": alertas,
            "ressalvas": ressalvas, "tabela": t.reset_index()}


RITMOS = [1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1_200, 3_000, 6_000, 12_000, 30_000, 60_000]
COR_NEUTRA, COR_TEXTO, COR_GRADE = cores.TEXTO_SECUNDARIO, cores.TEXTO, cores.GRADE


def escolher(perfil: Perfil, dados: dict) -> tuple[str, str]:
    return recomendar(perfil, dados)["escolha"]


def _motivo(escolha: tuple[str, str], perda: str, t: pd.DataFrame) -> str:
    wf = t.loc[("WAL", "FULL")]
    custo = _pct_fino(wf["fração do tempo gravando"])
    if escolha == ("WAL", "FULL"):
        if perda == "inaceitavel":
            return f"não perdeu nenhuma transação nas quedas simuladas e ocupa {custo} do tempo neste ritmo"
        return f"neste ritmo o FULL ocupa só {custo} do tempo: não compensa arriscar a perda do NORMAL"
    if perda == "toleravel":
        return f"neste ritmo o FULL ocuparia {custo} do tempo; o NORMAL perde as transações recentes numa queda"
    return "a mais rápida; numa queda de energia perde as transações mais recentes"


def _rotulo(ms_min: float, frac: float) -> str:
    if frac > 1:
        return f"não dá conta: precisaria de {_pct_fino(frac)} do tempo"
    return f"{_por_minuto(ms_min)} por minuto · {_pct_fino(frac)} do tempo"


def grafico(le: bool, perda: str, ambiente: str, dados: dict, inicial: int = 60) -> go.Figure:
    """Figura com controle deslizante proprio (roda no navegador): cada posicao recalcula o custo e a
    recomendacao para aquele ritmo, sem voltar ao servidor, entao o grafico muda enquanto se arrasta."""
    nomes = [_nome(j, s) + (" (padrão)" if (j, s) == PADRAO else "") for j, s in CONFIGS]
    paleta = [cores.config(j, s) for j, s in CONFIGS]
    ms = {c: float(dados["latencia_ms"].loc[(ambiente, *c)]) for c in CONFIGS}
    pct = {c: [100 * r * ms[c] / 60_000 for r in RITMOS] for c in CONFIGS}

    def estado(r: float) -> dict:
        perfil = Perfil(r, le, perda, ambiente)
        t = tabela(perfil, dados).set_index(["journal_mode", "synchronous"])
        escolha = escolher(perfil, dados)
        fr = [float(t.loc[c, "fração do tempo gravando"]) for c in CONFIGS]
        topo = go.Scatter(
            x=[max(100 * f, 1e-6) for f in fr], y=nomes, mode="markers+text",
            marker={"color": paleta, "size": [24 if c == escolha else 13 for c in CONFIGS],
                    "symbol": ["star" if c == escolha else "circle" for c in CONFIGS],
                    "line": {"color": "white", "width": 1.5}},
            text=[("★ recomendada · " if c == escolha else "") + _rotulo(t.loc[c, "ms gravando por minuto"], f)
                  for c, f in zip(CONFIGS, fr)],
            textposition="middle right", textfont={"color": COR_TEXTO, "size": 13}, hoverinfo="skip",
            showlegend=False, xaxis="x", yaxis="y")
        pontos = go.Scatter(
            x=[r] * len(CONFIGS), y=[100 * f for f in fr], mode="markers", hoverinfo="skip",
            marker={"color": paleta, "size": [18 if c == escolha else 11 for c in CONFIGS],
                    "symbol": ["star" if c == escolha else "circle" for c in CONFIGS],
                    "line": {"color": "white", "width": 1.5}}, showlegend=False, xaxis="x2", yaxis="y2")
        titulo = (f"<b>{robustez._n(r, 0)} gravações por minuto → use "
                  f"{_nome(*escolha)}</b><br><span style='font-size:13px;color:{COR_NEUTRA}'>"
                  f"{_motivo(escolha, perda, t)} · PRAGMA journal_mode={escolha[0]}; synchronous={escolha[1]};</span>")
        layout = {"title": {"text": titulo, "x": 0, "xanchor": "left", "y": 0.98, "yanchor": "top"},
                  "shapes": [{"type": "line", "xref": "x2", "yref": "y2 domain", "x0": r, "x1": r, "y0": 0, "y1": 1,
                              "line": {"color": COR_TEXTO, "width": 1.5, "dash": "dot"}}]}
        return {"dados": [topo, pontos], "layout": layout}

    fig = make_subplots(rows=2, cols=1, row_heights=[0.42, 0.58], vertical_spacing=0.2,
                        subplot_titles=("Custo no ritmo escolhido (escala log)",
                                        "Como o custo cresce com o ritmo · linha cheia = FULL, tracejada = NORMAL"))
    e0 = estado(inicial)
    fig.add_trace(e0["dados"][0], row=1, col=1)
    for c, nome, cor in zip(CONFIGS, nomes, paleta):
        fig.add_trace(go.Scatter(x=RITMOS, y=pct[c], mode="lines", name=nome,
                                 line={"color": cor, "width": 3, "dash": "solid" if c[1] == "FULL" else "dash"},
                                 hovertemplate=nome + ": %{x:,.0f} gravações/min → %{y:.3g}% do tempo<extra></extra>"),
                      row=2, col=1)
    fig.add_trace(e0["dados"][1], row=2, col=1)
    fig.add_hline(y=100, line={"color": COR_NEUTRA, "dash": "dot", "width": 1}, row=2, col=1,
                  annotation_text="100%: gravando o minuto inteiro", annotation_position="top left",
                  annotation_font={"color": COR_NEUTRA, "size": 12})
    fig.update_layout(**e0["layout"])
    pontas = len(fig.data) - 1
    fig.frames = [go.Frame(name=str(r), data=estado(r)["dados"], traces=[0, pontas], layout=estado(r)["layout"])
                  for r in RITMOS]
    marcas = [1e-4, 1e-3, 1e-2, 0.1, 1, 10, 100, 1000]
    texto_marcas = ["0,0001%", "0,001%", "0,01%", "0,1%", "1%", "10%", "100%", "1000%"]
    fig.update_xaxes(type="log", range=[-5.3, 4.6], tickvals=marcas, ticktext=texto_marcas, row=1, col=1,
                     gridcolor=COR_GRADE, title="parte do tempo que o app passa gravando")
    fig.update_yaxes(autorange="reversed", row=1, col=1, gridcolor=COR_GRADE)
    fig.update_xaxes(type="log", row=2, col=1, gridcolor=COR_GRADE, title="gravações por minuto",
                     tickvals=[1, 10, 100, 1_000, 10_000, 60_000], ticktext=["1", "10", "100", "1.000", "10.000",
                                                                             "60.000"])
    fig.update_yaxes(type="log", row=2, col=1, gridcolor=COR_GRADE, title="% do tempo gravando",
                     tickvals=marcas, ticktext=texto_marcas, range=[-5.3, 3.6])
    fig.update_layout(
        height=760, margin={"l": 10, "r": 20, "t": 90, "b": 40}, plot_bgcolor="white", paper_bgcolor="white",
        font={"family": "Source Sans Pro, Arial, sans-serif", "color": COR_TEXTO, "size": 13},
        legend={"orientation": "v", "x": 0.01, "xanchor": "left", "y": 0.45, "yanchor": "top",
                "font": {"size": 12}, "bgcolor": "rgba(255,255,255,0.8)"},
        sliders=[{"active": RITMOS.index(inicial), "y": -0.06, "len": 1, "pad": {"t": 10},
                  "currentvalue": {"prefix": "Gravações por minuto: ", "font": {"size": 15}},
                  "steps": [{"label": robustez._n(r, 0), "method": "animate",
                             "args": [[str(r)], {"mode": "immediate", "frame": {"duration": 0, "redraw": True},
                                                 "transition": {"duration": 0}}]} for r in RITMOS]}])
    for anotacao in fig.layout.annotations[:2]:  # titulos dos dois paineis
        anotacao.update(x=0, xanchor="left", font={"size": 14, "color": COR_TEXTO})
    return fig


def render(st, dados: dict) -> None:
    """Secao da calculadora; recebe o modulo streamlit para poder entrar no dashboard final."""
    from labs.lab05_sqlite import painel  # aqui para evitar import circular (painel usa a calculadora)

    st.markdown("Escolha o cenário do app e **arraste o controle embaixo do gráfico**: o custo de cada "
                "configuração e a recomendação mudam enquanto você arrasta. Tudo vem dos valores medidos.")
    c1, c2, c3 = st.columns([2, 1.3, 1.3])
    perda = c1.radio("Perder a última gravação numa queda de energia é…", list(PERDAS), format_func=PERDAS.get,
                     index=0, horizontal=False)
    ambiente = c2.selectbox("Aparelho de referência", dados["ambientes"],
                            index=dados["ambientes"].index("iPhone 11 · iOS")
                            if "iPhone 11 · iOS" in dados["ambientes"] else 0)
    le = c3.toggle("O app lê enquanto grava", value=True,
                   help="Ex.: uma lista na tela durante uma sincronização em segundo plano")
    st.plotly_chart(grafico(le, perda, ambiente, dados), width="stretch",
                    config={"displayModeBar": False}, key="calculadora_ritmo")
    alerta = recomendar(Perfil(60, le, perda, ambiente), dados)["alertas"]
    for a in alerta:
        st.warning(a)
    esq, dir_ = st.columns(2)
    with esq:
        st.plotly_chart(painel.durabilidade(painel_durabilidade(dados)), width="stretch",
                        config={"displayModeBar": False}, key="calculadora_durabilidade")
    with dir_:
        if le and dados.get("concorrencia") is not None:
            st.plotly_chart(painel.concorrencia(dados["concorrencia"]), width="stretch",
                            config={"displayModeBar": False}, key="calculadora_concorrencia")
        else:
            st.info("Com o app só gravando (sem ler ao mesmo tempo), o bloqueio da leitura no DELETE não pesa na "
                    "decisão. Ligue a opção acima para ver o efeito na tela.")
    with st.expander("Como a recomendação é feita e o que ela não afirma"):
        st.markdown(
            f"- **Perda inaceitável:** `WAL/FULL`, a única medida que não perdeu nada nas quedas e é rápida.\n"
            f"- **Perda indiferente:** `WAL/NORMAL`, a mais rápida.\n"
            f"- **Perda tolerável:** `WAL/NORMAL` só quando o `WAL/FULL` passa de {_pct_fino(LIMITE_TEMPO)} do tempo "
            f"gravando ou de meio quadro ({robustez._n(QUADRO_MS / 2, 0)} ms) por gravação; senão `WAL/FULL`.")
        for x in recomendar(Perfil(60, le, perda, ambiente), dados)["ressalvas"]:
            st.markdown(f"- {x}")


def painel_durabilidade(dados: dict) -> pd.DataFrame:
    """Resumo da durabilidade no formato que painel.durabilidade espera (as duas falhas)."""
    return pd.concat([dados["durabilidade"].reset_index().assign(falha="sistema"), dados["processo"]],
                     ignore_index=True)
