"""Analise da replicacao, da durabilidade medida e da concorrencia (issue #137).

Replicacao: as mesmas 5 comparacoes do estudo principal (H-1 a H-3 confirmatorias, E-1 e E-2 exploratorias),
feitas em cada ambiente com Wilcoxon pareado por bloco, Holm nas confirmatorias e razao das medianas com IC 95%
por bootstrap pareado. A pergunta e se a **direcao** e a **conclusao** se mantem; a magnitude pode mudar.
Ambientes: o notebook do grupo (Windows e Ubuntu no WSL2) e os runners do GitHub Actions (Ubuntu, Windows, macOS).

Durabilidade: por tipo de falha e configuracao, quantas rodadas perderam ao menos uma transacao confirmada (IC 95%
exato de Clopper-Pearson, como os intervalos de proporcao do Lab04), quantas transacoes se perderam e se o banco
continuou integro. Duas comparacoes planejadas com o teste exato de Fisher (Holm):
    WAL/NORMAL x WAL/FULL      (o custo de durabilidade do NORMAL, a contrapartida de H-3);
    DELETE/FULL x DELETE/EXTRA (se a correcao que a documentacao indica para o modo DELETE funciona).

Concorrencia: C-1 (latencia p99 da leitura com escrita em andamento, WAL < DELETE) e C-2 (vazao do escritor com
leituras em andamento, WAL > DELETE), registradas em concorrencia.py antes da coleta; Wilcoxon pareado, Holm.

    python -m labs.lab05_sqlite.robustez   # gera data/processed/robustez_*.csv e docs/lab05/robustez.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from labs.lab05_sqlite import coleta

SEED = 42
ALFA = 0.05
RAW = coleta.DADOS
PROCESSADOS = RAW.parent / "processed"
DOC = Path(__file__).resolve().parents[2] / "docs" / "lab05" / "robustez.md"
# rotulo -> arquivo em data/raw; o primeiro e a referencia. Os que nao existirem sao ignorados.
AMBIENTES = {"Notebook · Windows": "coleta_completa", "Notebook · Linux (WSL2)": "coleta_linux",
             "Actions · Ubuntu": "coleta_actions_Linux", "Actions · Windows": "coleta_actions_Windows",
             "Actions · macOS": "coleta_actions_macOS"}
REFERENCIA = next(iter(AMBIENTES))
LINUX = "Notebook · Linux (WSL2)"  # onde a queda do sistema foi simulada


@dataclass(frozen=True)
class Comparacao:
    codigo: str
    descricao: str
    carga: str
    a: tuple[str, str]
    b: tuple[str, str]
    cauda: str
    confirmatoria: bool


COMPARACOES = (
    Comparacao("H-1", "Escrita: WAL > DELETE (FULL)", "escrita", ("WAL", "FULL"), ("DELETE", "FULL"), "greater",
               True),
    Comparacao("H-2", "Leitura avulsa: WAL ≠ DELETE (FULL)", "leitura", ("WAL", "FULL"), ("DELETE", "FULL"),
               "two-sided", True),
    Comparacao("H-3", "Escrita: NORMAL > FULL (WAL)", "escrita", ("WAL", "NORMAL"), ("WAL", "FULL"), "greater",
               True),
    Comparacao("E-1", "Leitura em 1 transação: WAL ≠ DELETE (FULL)", "leitura_transacao", ("WAL", "FULL"),
               ("DELETE", "FULL"), "two-sided", False),
    Comparacao("E-2", "Escrita: NORMAL > FULL (DELETE)", "escrita", ("DELETE", "NORMAL"), ("DELETE", "FULL"),
               "greater", False),
)


# ---------------------------------------------------------------------------------------------- estatistica
def holm(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    ordem = np.argsort(p)
    ajustado = np.empty_like(p)
    acumulado = 0.0
    for i, j in enumerate(ordem):
        acumulado = max(acumulado, (len(p) - i) * p[j])
        ajustado[j] = min(1.0, acumulado)
    return ajustado.tolist()


def razao_bootstrap(a: np.ndarray, b: np.ndarray, reps: int = 5_000, seed: int = SEED) -> tuple[float, float]:
    """IC 95% da razao das medianas por bootstrap pareado (os blocos sao reamostrados juntos)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(reps, len(a)))
    razoes = np.median(a[idx], axis=1) / np.median(b[idx], axis=1)
    return float(np.quantile(razoes, 0.025)), float(np.quantile(razoes, 0.975))


# ----------------------------------------------------------------------------------------------- replicacao
def carregar_coletas(pasta: Path = RAW) -> pd.DataFrame:
    partes = [pd.read_csv(pasta / f"{arquivo}.csv").assign(ambiente=nome) for nome, arquivo in AMBIENTES.items()
              if (pasta / f"{arquivo}.csv").exists()]
    return pd.concat(partes, ignore_index=True)


def _pares(df: pd.DataFrame, c: Comparacao) -> tuple[np.ndarray, np.ndarray]:
    d = df[df["carga"] == c.carga].set_index(["journal_mode", "synchronous", "bloco"]).sort_index()["ops_por_s"]
    a, b = d.loc[c.a].align(d.loc[c.b], join="inner")
    return a.to_numpy(), b.to_numpy()


def testar(df: pd.DataFrame, c: Comparacao) -> dict:
    a, b = _pares(df, c)
    inf, sup = razao_bootstrap(a, b)
    return {"codigo": c.codigo, "descricao": c.descricao, "confirmatoria": c.confirmatoria, "n": len(a),
            "razao": float(np.median(a) / np.median(b)), "ic_inf": inf, "ic_sup": sup,
            "p": float(stats.wilcoxon(a, b, alternative=c.cauda).pvalue)}


def replicacao(coletas: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for ambiente, df in coletas.groupby("ambiente", sort=False):
        resultados = [testar(df, c) | {"ambiente": ambiente, "sqlite": df["sqlite_version"].iloc[0]}
                      for c in COMPARACOES]
        confirmatorias = [r for r in resultados if r["confirmatoria"]]
        for r, p in zip(confirmatorias, holm([r["p"] for r in confirmatorias])):
            r["p_holm"] = p
        for r in resultados:
            r["rejeita_h0"] = r.get("p_holm", r["p"]) < ALFA
        linhas += resultados
    return pd.DataFrame(linhas)


def comparar_ambientes(rep: pd.DataFrame, referencia: str = REFERENCIA) -> pd.DataFrame:
    """Uma linha por comparacao: em quantos ambientes a direcao e a conclusao sao as mesmas da referencia."""
    linhas = []
    for c in COMPARACOES:
        g = rep[rep["codigo"] == c.codigo].set_index("ambiente")
        ref = g.loc[referencia]
        direcao = np.sign(np.log(g["razao"].astype(float))) == np.sign(np.log(float(ref["razao"])))
        conclusao = g["rejeita_h0"].astype(bool) == bool(ref["rejeita_h0"])
        linhas.append({"codigo": c.codigo, "ambientes": len(g), "mesma_direcao": int(direcao.sum()),
                       "mesma_conclusao": int(conclusao.sum()), "razao_min": float(g["razao"].min()),
                       "razao_max": float(g["razao"].max())})
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------------------------- durabilidade
def carregar_durabilidade(pasta: Path = RAW) -> pd.DataFrame:
    return pd.read_csv(pasta / "durabilidade.csv")


ORDEM_DURABILIDADE = [("DELETE", "FULL"), ("DELETE", "EXTRA"), ("DELETE", "NORMAL"), ("WAL", "FULL"),
                      ("WAL", "NORMAL")]


def resumo_durabilidade(dur: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for (falha, journal, sync), g in dur.groupby(["falha", "journal_mode", "synchronous"], sort=False):
        k, n = int((g["perdidas"] > 0).sum()), len(g)
        ic = stats.binomtest(k, n).proportion_ci(method="exact")
        linhas.append({"falha": falha, "journal_mode": journal, "synchronous": sync, "rodadas": n,
                       "rodadas_com_perda": k, "proporcao": k / n, "ic_inf": ic.low, "ic_sup": ic.high,
                       "perdidas_mediana": float(g["perdidas"].median()), "perdidas_max": int(g["perdidas"].max()),
                       "perdidas_total": int(g["perdidas"].sum()), "confirmadas_total": int(g["confirmadas"].sum()),
                       "integras": int((g["integridade"] == "ok").sum())})
    ordem = {f"{j}/{s}": i for i, (j, s) in enumerate(ORDEM_DURABILIDADE)}
    tabela = pd.DataFrame(linhas)
    chave = tabela["falha"].map({"processo": 0, "sistema": 1}) * 10 + (
        tabela["journal_mode"] + "/" + tabela["synchronous"]).map(ordem)
    return tabela.assign(_k=chave).sort_values("_k").drop(columns="_k").reset_index(drop=True)


COMPARACOES_DURABILIDADE = (("WAL", "NORMAL", "WAL", "FULL"), ("DELETE", "FULL", "DELETE", "EXTRA"))


def testes_durabilidade(dur: pd.DataFrame, falha: str = "sistema") -> pd.DataFrame:
    g = dur[dur["falha"] == falha]
    linhas = []
    for ja, sa, jb, sb in COMPARACOES_DURABILIDADE:
        a = g[(g["journal_mode"] == ja) & (g["synchronous"] == sa)]["perdidas"] > 0
        b = g[(g["journal_mode"] == jb) & (g["synchronous"] == sb)]["perdidas"] > 0
        tabela = [[int(a.sum()), int((~a).sum())], [int(b.sum()), int((~b).sum())]]
        linhas.append({"comparacao": f"{ja}/{sa} perde mais que {jb}/{sb}", "com_perda_a": tabela[0][0],
                       "n_a": len(a), "com_perda_b": tabela[1][0], "n_b": len(b),
                       "p": float(stats.fisher_exact(tabela, alternative="greater").pvalue)})
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = holm(tabela["p"].tolist())
    tabela["rejeita_h0"] = tabela["p_holm"] < ALFA
    return tabela


# --------------------------------------------------------------------------------------------- concorrencia
@dataclass(frozen=True)
class HipoteseConcorrencia:
    codigo: str
    descricao: str
    metrica: str
    maior: str  # configuracao em que a metrica deve ser maior


HIPOTESES_CONCORRENCIA = (
    HipoteseConcorrencia("C-1", "Com escrita em andamento, a leitura p99 é menor no WAL", "latencia_p99_ms",
                         "DELETE"),
    HipoteseConcorrencia("C-2", "Com leituras em andamento, o escritor faz mais transações/s no WAL",
                         "escritas_por_s", "WAL"),
)


def carregar_concorrencia(pasta: Path = RAW) -> pd.DataFrame | None:
    caminho = pasta / "concorrencia.csv"
    return pd.read_csv(caminho) if caminho.exists() else None


def resumo_concorrencia(conc: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for (journal, sync, escritor), g in conc.groupby(["journal_mode", "synchronous", "escritor"]):
        linhas.append({"journal_mode": journal, "synchronous": sync, "escritor": escritor, "blocos": len(g),
                       "leituras_mediana": float(g["leituras"].median()),
                       "latencia_mediana_ms": float(g["latencia_mediana_ms"].median()),
                       "latencia_p99_ms": float(g["latencia_p99_ms"].median()),
                       "latencia_max_ms": float(g["latencia_max_ms"].max()),
                       "acima_quadro": int(g["acima_quadro"].sum()), "leituras_total": int(g["leituras"].sum()),
                       # mediana por bloco: somar todas as leituras daria mais peso aos blocos com muitas leituras
                       # rapidas e esconderia os blocos em que a leitura quase nao andou
                       "fracao_acima_quadro": float((g["acima_quadro"] / g["leituras"]).median()),
                       "escritas_por_s": float(g["escritas_por_s"].median()),
                       "erros": int(g["erros_leitura"].sum() + g["erros_escrita"].sum())})
    return pd.DataFrame(linhas).sort_values(["escritor", "journal_mode", "synchronous"],
                                            ascending=[False, True, True]).reset_index(drop=True)


def testes_concorrencia(conc: pd.DataFrame) -> pd.DataFrame:
    g = conc[(conc["escritor"] == "sim") & (conc["synchronous"] == "FULL")].set_index(["journal_mode", "bloco"])
    linhas = []
    for h in HIPOTESES_CONCORRENCIA:
        outro = "WAL" if h.maior == "DELETE" else "DELETE"
        a, b = g.loc[h.maior, h.metrica].sort_index().align(g.loc[outro, h.metrica].sort_index(), join="inner")
        a, b = a.to_numpy(dtype=float), b.to_numpy(dtype=float)
        inf, sup = razao_bootstrap(a, b)
        linhas.append({"codigo": h.codigo, "descricao": h.descricao, "metrica": h.metrica,
                       "comparacao": f"{h.maior}/FULL ÷ {outro}/FULL", "n": len(a),
                       "razao": float(np.median(a) / np.median(b)), "ic_inf": inf, "ic_sup": sup,
                       "p": float(stats.wilcoxon(a, b, alternative="greater").pvalue)})
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = holm(tabela["p"].tolist())
    tabela["rejeita_h0"] = tabela["p_holm"] < ALFA
    return tabela


# ------------------------------------------------------------------------------------------------ relatorio
def _n(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _vezes(x: float) -> str:
    return f"{_n(x, 0 if x >= 100 else 2)}×"


def _ic(inf: float, sup: float) -> str:
    casas = 0 if inf >= 100 else 2
    return f"[{_n(inf, casas)}; {_n(sup, casas)}]"


def _ms(x: float) -> str:
    return f"{_n(x, 0 if x >= 10 else 1)} ms"


def _p(p: float) -> str:
    return "< 0,001" if p < 0.001 else _n(p, 3)


def _pct(x: float) -> str:
    return f"{_n(100 * x, 0)}%"


def _celula(r: pd.Series) -> str:
    p = r["p_holm"] if pd.notna(r.get("p_holm")) else r["p"]
    return f"{_vezes(r['razao'])} · p {_p(p)}"


def secao_replicacao(rep: pd.DataFrame, comp: pd.DataFrame) -> list[str]:
    ambientes = list(dict.fromkeys(rep["ambiente"]))
    versoes = rep.groupby("ambiente", sort=False)["sqlite"].first()
    linhas = [
        "## 1. Replicação em outros ambientes",
        "",
        "A coleta completa (30 blocos × 3 cargas × 4 configurações, o mesmo script e a mesma semente) foi repetida "
        "em outros ambientes, e cada um foi analisado com os mesmos testes do estudo principal:",
        "",
        "- **Notebook · Linux (WSL2):** Ubuntu 26.04 no mesmo notebook, bancos no ext4 (o `/tmp` do WSL fica em "
        "memória e foi evitado). Mudam o sistema, o sistema de arquivos e a versão do SQLite; o hardware é o mesmo.",
        "- **Actions:** máquinas virtuais do GitHub Actions com Ubuntu, Windows e macOS "
        "(`.github/workflows/lab05-replicacao.yml`). Hardware diferente do nosso, mas compartilhado e com ruído: "
        "servem para conferir a direção, não a magnitude.",
        "",
        "| Ambiente | SQLite |",
        "| --- | --- |",
        *[f"| {a} | {versoes[a]} |" for a in ambientes],
        "",
        "| Comparação | " + " | ".join(ambientes) + " | Mesma direção | Mesma conclusão |",
        "| --- | " + " | ".join("---:" for _ in ambientes) + " | :---: | :---: |",
    ]
    for c in COMPARACOES:
        g = rep[rep["codigo"] == c.codigo].set_index("ambiente")
        k = comp[comp["codigo"] == c.codigo].iloc[0]
        linhas.append(f"| **{c.codigo}** {c.descricao} | " + " | ".join(_celula(g.loc[a]) for a in ambientes)
                      + f" | {k['mesma_direcao']}/{k['ambientes']} | {k['mesma_conclusao']}/{k['ambientes']} |")
    total = int(comp["ambientes"].sum())
    linhas += [
        "",
        "Razão das medianas; p de Holm nas confirmatórias (H) e p bruto nas exploratórias (E). Os intervalos de "
        "confiança estão em `data/processed/robustez_replicacao.csv`.",
        "",
        f"**Leitura:** a direção se repete em {int(comp['mesma_direcao'].sum())} de {total} pares "
        f"(comparação × ambiente) e a conclusão do teste em {int(comp['mesma_conclusao'].sum())} de {total}. A "
        "**magnitude** varia bastante entre ambientes, porque o custo de sincronizar o disco e de travar arquivos "
        "depende do sistema e do hardware. Por isso o estudo afirma efeitos relativos (direção e ordem de grandeza) "
        "e não um número universal.",
        "",
    ]
    e1 = comp[comp["codigo"] == "E-1"]
    if not e1.empty:
        e1 = e1.iloc[0]
        linhas += [
            f"Em **E-1** o efeito é praticamente nulo em todos os ambientes (razões entre {_n(e1['razao_min'], 3)} e "
            f"{_n(e1['razao_max'], 3)}), então \"mesma direção\" não tem significado ali: o sinal de uma diferença "
            "de menos de 2% oscila com o ruído, e com 30 blocos uma diferença tão pequena às vezes fica "
            "significativa. A conclusão que se repete é a de E-1 ser desprezível perto de H-2.",
            "",
        ]
    return linhas


def secao_durabilidade(dur: pd.DataFrame, resumo: pd.DataFrame, testes: pd.DataFrame) -> list[str]:
    rodadas = dur.groupby("falha")["rodada"].max()
    linhas = [
        "## 2. Durabilidade medida (M6)",
        "",
        "Um processo grava transações de 1 `INSERT` e, a cada `COMMIT` confirmado, avisa quem controla o teste e "
        "espera a resposta antes da próxima (como um app que grava a cada ação do usuário). Depois de 1 a 8 s "
        "sorteados, provocamos a falha e contamos quantas transações **já confirmadas** sumiram.",
        "",
        f"- **Falha de processo** ({rodadas.get('processo', 0)} rodadas por configuração, Windows): o processo é "
        "encerrado à força, como um app que trava. O sistema operacional continua de pé.",
        f"- **Queda do sistema** ({rodadas.get('sistema', 0)} rodadas por configuração, Linux): reinício imediato "
        "com `echo b > /proc/sysrq-trigger`, sem gravar o cache nem desmontar o disco, o método usual para simular "
        "queda de energia. Antes, testamos que `wsl --terminate` e `wsl --shutdown` gravam o cache e não servem. "
        "Cada rodada confere que o Linux de fato reiniciou (o `boot_id` muda).",
        "- **DELETE/EXTRA** entra só aqui: é a correção que a documentação indica para o modo DELETE, porque com "
        "FULL o SQLite não sincroniza a pasta depois de apagar o journal, e esse apagamento é o que confirma a "
        "transação.",
        "",
        "| Falha | Configuração | Rodadas com perda (IC 95%) | Transações perdidas por rodada (mediana · máx.) | "
        "Banco íntegro |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for _, r in resumo.iterrows():
        linhas.append(
            f"| {r['falha'].capitalize()} | `{r['journal_mode']}/{r['synchronous']}` | "
            f"{r['rodadas_com_perda']} de {r['rodadas']} ({_pct(r['proporcao'])}; {_pct(r['ic_inf'])}–"
            f"{_pct(r['ic_sup'])}) | {_n(r['perdidas_mediana'], 0)} · {r['perdidas_max']} | "
            f"{r['integras']} de {r['rodadas']} |")
    linhas += ["", "**Comparações planejadas** (queda do sistema, teste exato de Fisher unilateral, Holm):", "",
               "| Comparação | Com perda | p (Holm) | Rejeita H₀? |", "| --- | ---: | ---: | :---: |"]
    for _, t in testes.iterrows():
        linhas.append(f"| {t['comparacao']} | {t['com_perda_a']}/{t['n_a']} × {t['com_perda_b']}/{t['n_b']} | "
                      f"{_p(t['p_holm'])} | {'Sim' if t['rejeita_h0'] else 'Não'} |")
    return [*linhas, ""]


def secao_concorrencia(conc: pd.DataFrame, resumo: pd.DataFrame, testes: pd.DataFrame) -> list[str]:
    linhas = [
        "## 3. Leitura e escrita ao mesmo tempo",
        "",
        "A principal promessa do WAL é que leitores e escritor não se bloqueiam. Um processo grava sem parar "
        "(1 `INSERT` por transação, como uma sincronização em segundo plano) enquanto outro lê uma tela de 50 linhas "
        "a cada 5 ms, durante 3 s. As duas conexões usam o *timeout* padrão do Python (5 s): quem encontra o banco "
        f"travado espera, como em um app real. {conc['bloco'].nunique()} blocos; em cada um, as 4 configurações com "
        "e sem escritor, em ordem sorteada. O limite de 16 ms é o orçamento de um quadro a 60 Hz.",
        "",
        "Cada linha resume os blocos pela mediana (o pior caso é o máximo entre todos). Sem bloqueio, a leitura "
        "completa as 600 telas previstas em 3 s.",
        "",
        "| Escritor | Configuração | Telas lidas em 3 s (de 600) | Latência mediana | p99 | Pior leitura | "
        "Leituras > 16 ms | Escritor (transações/s) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in resumo.iterrows():
        escritor = _n(r["escritas_por_s"], 0) if r["escritor"] == "sim" else "—"
        linhas.append(
            f"| {'Com' if r['escritor'] == 'sim' else 'Sem'} | `{r['journal_mode']}/{r['synchronous']}` | "
            f"{_n(r['leituras_mediana'], 0)} | {_n(r['latencia_mediana_ms'], 2)} ms | "
            f"{_n(r['latencia_p99_ms'], 2)} ms | {_ms(r['latencia_max_ms'])} | "
            f"{_pct(r['fracao_acima_quadro'])} | {escritor} |")
    linhas += ["", "**Hipóteses registradas antes da coleta** (synchronous = FULL, pareadas por bloco, Wilcoxon "
               "unilateral, Holm):", "",
               "| Hipótese | Comparação | Razão das medianas (IC 95%) | p (Holm) | Rejeita H₀? |",
               "| --- | --- | ---: | ---: | :---: |"]
    for _, t in testes.iterrows():
        linhas.append(f"| **{t['codigo']}** {t['descricao']} | {t['comparacao']} (`{t['metrica']}`) | "
                      f"{_vezes(t['razao'])} {_ic(t['ic_inf'], t['ic_sup'])} | {_p(t['p_holm'])} | "
                      f"{'Sim' if t['rejeita_h0'] else 'Não'} |")
    return [*linhas, ""]


def markdown(d: dict) -> str:
    fontes = ["`coleta_*.csv`", "`durabilidade.csv`"]
    if d.get("conc") is not None:
        fontes.append("`concorrencia.csv`")
    linhas = ["# Lab05 — Robustez: replicação, durabilidade medida e concorrência (#137)", "",
              f"> Gerado por `python -m labs.lab05_sqlite.robustez` a partir de {', '.join(fontes)} em "
              "`labs/lab05_sqlite/data/raw`.", "",
              *secao_replicacao(d["replicacao"], d["comparacao"]),
              *secao_durabilidade(d["dur"], d["durabilidade"], d["testes"])]
    if d.get("conc") is not None:
        linhas += secao_concorrencia(d["conc"], d["concorrencia"], d["testes_concorrencia"])
    linhas += ["## 4. O que isso muda nas conclusões", "", *conclusoes(d), ""]
    return "\n".join(linhas)


def conclusoes(d: dict) -> list[str]:
    """Cada frase depende dos dados; nada e afirmado sem o numero que o sustenta."""
    resumo, testes, comp, rep = d["durabilidade"], d["testes"], d["comparacao"], d["replicacao"]

    def linha(falha: str, j: str, s: str) -> pd.Series:
        sel = resumo[(resumo["falha"] == falha) & (resumo["journal_mode"] == j) & (resumo["synchronous"] == s)]
        return sel.iloc[0]

    def razao(codigo: str, ambiente: str = REFERENCIA) -> float | None:
        sel = rep[(rep["ambiente"] == ambiente) & (rep["codigo"] == codigo)]["razao"]
        return float(sel.iloc[0]) if len(sel) else None

    def ganho(codigo: str) -> str:
        """A queda do sistema foi simulada no Linux: cita o ganho medido la, ao lado do Windows."""
        linux = razao(codigo, LINUX)
        texto = f"{_vezes(razao(codigo))} no Windows"
        return texto + (f" e {_vezes(linux)} no Linux, onde a queda foi simulada" if linux else "")

    def teste(texto: str) -> pd.Series:
        return testes[testes["comparacao"].str.startswith(texto)].iloc[0]

    itens = []
    proc = resumo[resumo["falha"] == "processo"]
    if not proc.empty:
        k, n = int(proc["rodadas_com_perda"].sum()), int(proc["rodadas"].sum())
        itens.append(f"**Travar o app {'não perdeu dados em nenhuma configuração' if k == 0 else 'também perdeu dados'}"
                     f"** ({k} rodadas com perda em {n})."
                     + (" O risco do `synchronous` aparece só na queda do sistema ou de energia." if k == 0 else ""))
    if (resumo["falha"] == "sistema").any():
        wn, wf = linha("sistema", "WAL", "NORMAL"), linha("sistema", "WAL", "FULL")
        t = teste("WAL/NORMAL")
        itens.append(
            f"**Custo medido do NORMAL:** na queda do sistema, `WAL/NORMAL` perdeu transações confirmadas em "
            f"{wn['rodadas_com_perda']} de {wn['rodadas']} rodadas (até {wn['perdidas_max']} por queda), contra "
            f"{wf['rodadas_com_perda']} de {wf['rodadas']} no `WAL/FULL` (Fisher, p Holm {_p(t['p_holm'])}). "
            f"É a contrapartida do ganho de H-3 ({ganho('H-3')})"
            + (", e a durabilidade deixa de ser só uma citação da documentação." if t["rejeita_h0"] else
               "; com essas rodadas, a diferença não foi estatisticamente significativa."))
        df_, dx = linha("sistema", "DELETE", "FULL"), linha("sistema", "DELETE", "EXTRA")
        t = teste("DELETE/FULL")
        frase = (f"**`DELETE/FULL` (o padrão do Python e do SQLite):** perdeu transação confirmada em "
                 f"{df_['rodadas_com_perda']} de {df_['rodadas']} quedas (até {df_['perdidas_max']} por queda); "
                 f"com `DELETE/EXTRA`, {dx['rodadas_com_perda']} de {dx['rodadas']} (Fisher, p Holm "
                 f"{_p(t['p_holm'])}).")
        if df_["rodadas_com_perda"] > 0 and dx["rodadas_com_perda"] == 0:
            frase += " É o que a documentação descreve para o EXTRA: sincronizar a pasta depois de apagar o journal."
        if wf["rodadas_com_perda"] == 0:
            frase += f" O `WAL/FULL` não perdeu nada e grava mais rápido que o `DELETE/FULL` (H-1: {ganho('H-1')})."
        itens.append(frase)
    total, integras = int(resumo["rodadas"].sum()), int(resumo["integras"].sum())
    itens.append(f"**Integridade:** {integras} de {total} bancos passaram no `PRAGMA integrity_check` depois da falha"
                 + (": as perdas são de transações recentes, não corrupção." if integras == total else "."))
    rc = d.get("concorrencia")
    if rc is not None:
        def r(j: str) -> pd.Series:
            sel = rc[(rc["journal_mode"] == j) & (rc["synchronous"] == "FULL") & (rc["escritor"] == "sim")]
            return sel.iloc[0]

        dc, wc, tc = r("DELETE"), r("WAL"), d["testes_concorrencia"].set_index("codigo")
        itens.append(
            f"**Concorrência:** com escrita em segundo plano, o leitor do `DELETE/FULL` completou só "
            f"{_n(dc['leituras_mediana'], 0)} das 600 telas em 3 s (latência mediana {_n(dc['latencia_mediana_ms'], 0)} ms, "
            f"pior caso {_n(dc['latencia_max_ms'], 0)} ms: a tela congelaria), enquanto no `WAL/FULL` completou "
            f"{_n(wc['leituras_mediana'], 0)} (pior caso {_n(wc['latencia_max_ms'], 1)} ms, dentro de um quadro). "
            f"C-1 {'confirmada' if tc.loc['C-1', 'rejeita_h0'] else 'não confirmada'} (p Holm "
            f"{_p(tc.loc['C-1', 'p_holm'])}); C-2 {'confirmada' if tc.loc['C-2', 'rejeita_h0'] else 'não confirmada'}"
            f" (escritor {_vezes(tc.loc['C-2', 'razao'])} no WAL, p Holm {_p(tc.loc['C-2', 'p_holm'])}).")
    pares = int(comp["ambientes"].sum())
    itens.append(f"**Validade externa:** em {int(comp['ambientes'].max())} ambientes, a direção dos efeitos se repete "
                 f"em {int(comp['mesma_direcao'].sum())} de {pares} pares e a conclusão em "
                 f"{int(comp['mesma_conclusao'].sum())} de {pares}; a magnitude muda de ambiente para ambiente.")
    return [f"{i}. {texto}" for i, texto in enumerate(itens, start=1)]


def gerar(destino_doc: Path = DOC) -> dict:
    d = {"replicacao": replicacao(carregar_coletas()), "dur": carregar_durabilidade()}
    d["comparacao"] = comparar_ambientes(d["replicacao"])
    d["durabilidade"], d["testes"] = resumo_durabilidade(d["dur"]), testes_durabilidade(d["dur"])
    d["conc"] = carregar_concorrencia()
    if d["conc"] is not None:
        d["concorrencia"], d["testes_concorrencia"] = resumo_concorrencia(d["conc"]), testes_concorrencia(d["conc"])
    PROCESSADOS.mkdir(parents=True, exist_ok=True)
    saidas = {"replicacao": "robustez_replicacao", "durabilidade": "robustez_durabilidade",
              "testes": "robustez_durabilidade_testes", "concorrencia": "robustez_concorrencia",
              "testes_concorrencia": "robustez_concorrencia_testes"}
    for chave, nome in saidas.items():
        if d.get(chave) is not None:
            d[chave].to_csv(PROCESSADOS / f"{nome}.csv", index=False, lineterminator="\n")
    destino_doc.write_text(markdown(d), encoding="utf-8")
    return d


if __name__ == "__main__":
    d = gerar()
    for chave in ("comparacao", "durabilidade", "testes", "concorrencia", "testes_concorrencia"):
        if d.get(chave) is not None:
            print(d[chave].to_string(index=False), "\n")
    print(f"relatorio em {DOC}")
