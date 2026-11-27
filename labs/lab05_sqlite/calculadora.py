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

from labs.lab05_sqlite import robustez

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


def render(st, dados: dict) -> None:
    """Secao da calculadora; recebe o modulo streamlit para poder entrar no dashboard final."""
    st.markdown("Informe o perfil do app. A recomendação usa só valores medidos no estudo, e o porquê aparece "
                "embaixo, com os números.")
    c1, c2 = st.columns(2)
    with c1:
        escritas = st.select_slider("Gravações por minuto (no pico de uso)",
                                    options=[1, 5, 10, 30, 60, 120, 300, 600, 1_200, 3_000, 6_000, 12_000], value=60)
        le = st.toggle("O app lê do banco enquanto grava (ex.: lista na tela durante uma sincronização)", value=True)
    with c2:
        perda = st.radio("Perder a última gravação numa queda de energia é…", list(PERDAS),
                         format_func=PERDAS.get, index=0)
        ambiente = st.selectbox("Ambiente de referência para o custo", dados["ambientes"],
                                index=dados["ambientes"].index("iPhone 11 · iOS")
                                if "iPhone 11 · iOS" in dados["ambientes"] else 0)
    r = recomendar(Perfil(escritas, le, perda, ambiente), dados)
    with st.container(border=True):
        st.markdown(f"### Recomendação: `{r['nome']}`")
        st.code(f"PRAGMA journal_mode = {r['escolha'][0]};\nPRAGMA synchronous = {r['escolha'][1]};", language="sql")
        for m in r["motivos"]:
            st.markdown(f"- {m}")
    for a in r["alertas"]:
        st.warning(a)
    t = r["tabela"]
    vista = pd.DataFrame({
        "Configuração": t["Configuração"],
        "ms por gravação": t["ms por gravação"].map(lambda x: robustez._n(x, 3)),
        "Gravando por minuto": t["ms gravando por minuto"].map(_por_minuto),
        "% do tempo": t["fração do tempo gravando"].map(_pct_fino),
        "Quedas com perda (Linux)": t["quedas com perda"],
        "Perda máxima por queda": t["perda máxima"],
        "Bloqueia leitura ao gravar": t["bloqueia leitura"].map({True: "Sim", False: "Não"}),
    })
    st.dataframe(vista, hide_index=True, width="stretch")
    with st.expander("O que a calculadora não afirma"):
        for x in r["ressalvas"]:
            st.markdown(f"- {x}")
