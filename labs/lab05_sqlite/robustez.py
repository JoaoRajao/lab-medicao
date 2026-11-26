"""Analise da replicacao no Linux e da durabilidade medida (issue #137).

Replicacao: as mesmas 5 comparacoes do estudo principal (H-1 a H-3 confirmatorias, E-1 e E-2 exploratorias),
feitas em cada ambiente com Wilcoxon pareado por bloco, Holm nas confirmatorias e razao das medianas com IC 95%
por bootstrap pareado. A pergunta e se a **direcao** e a **conclusao** se mantem; a magnitude pode mudar.

Durabilidade: por tipo de falha e configuracao, quantas rodadas perderam ao menos uma transacao confirmada (IC 95%
exato de Clopper-Pearson, como os intervalos de proporcao do Lab04), quantas transacoes se perderam e se o banco
continuou integro. Duas comparacoes planejadas com o teste exato de Fisher (Holm):
    WAL/NORMAL x WAL/FULL      (o custo de durabilidade do NORMAL, a contrapartida dos 168x de H-3);
    DELETE/FULL x DELETE/EXTRA (se a correcao que a documentacao indica para o modo DELETE funciona).

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
AMBIENTES = {"Windows": "coleta_completa", "Linux": "coleta_linux"}


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


# --------------------------------------------------------------------------------------------- replicacao
def carregar_coletas(pasta: Path = RAW) -> pd.DataFrame:
    partes = [pd.read_csv(pasta / f"{arquivo}.csv").assign(ambiente=nome) for nome, arquivo in AMBIENTES.items()]
    return pd.concat(partes, ignore_index=True)


def holm(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    ordem = np.argsort(p)
    ajustado = np.empty_like(p)
    acumulado = 0.0
    for i, j in enumerate(ordem):
        acumulado = max(acumulado, (len(p) - i) * p[j])
        ajustado[j] = min(1.0, acumulado)
    return ajustado.tolist()


def _pares(df: pd.DataFrame, c: Comparacao) -> tuple[np.ndarray, np.ndarray]:
    d = df[df["carga"] == c.carga].set_index(["journal_mode", "synchronous", "bloco"]).sort_index()["ops_por_s"]
    a, b = d.loc[c.a], d.loc[c.b]
    a, b = a.align(b, join="inner")
    return a.to_numpy(), b.to_numpy()


def razao_bootstrap(a: np.ndarray, b: np.ndarray, reps: int = 5_000, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(reps, len(a)))
    razoes = np.median(a[idx], axis=1) / np.median(b[idx], axis=1)
    return float(np.quantile(razoes, 0.025)), float(np.quantile(razoes, 0.975))


def testar(df: pd.DataFrame, c: Comparacao) -> dict:
    a, b = _pares(df, c)
    teste = stats.wilcoxon(a, b, alternative=c.cauda)
    inf, sup = razao_bootstrap(a, b)
    return {"codigo": c.codigo, "descricao": c.descricao, "confirmatoria": c.confirmatoria, "n": len(a),
            "razao": float(np.median(a) / np.median(b)), "ic_inf": inf, "ic_sup": sup, "p": float(teste.pvalue)}


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


def comparar_ambientes(rep: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por comparacao: razao em cada ambiente, se a direcao e a conclusao se mantem."""
    largo = rep.pivot(index="codigo", columns="ambiente", values=["razao", "rejeita_h0"])
    tabela = pd.DataFrame({
        "razao_windows": largo[("razao", "Windows")].astype(float), "razao_linux": largo[("razao", "Linux")].astype(float),
        "rejeita_windows": largo[("rejeita_h0", "Windows")].astype(bool),
        "rejeita_linux": largo[("rejeita_h0", "Linux")].astype(bool)})
    tabela["mesma_direcao"] = np.sign(np.log(tabela["razao_windows"])) == np.sign(np.log(tabela["razao_linux"]))
    tabela["mesma_conclusao"] = tabela["rejeita_windows"] == tabela["rejeita_linux"]
    return tabela.reindex([c.codigo for c in COMPARACOES]).reset_index()


# -------------------------------------------------------------------------------------------- durabilidade
def carregar_durabilidade(pasta: Path = RAW) -> pd.DataFrame:
    return pd.read_csv(pasta / "durabilidade.csv")


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
    ordem = {f"{j}/{s}": i for i, (j, s) in enumerate(
        [("DELETE", "FULL"), ("DELETE", "EXTRA"), ("DELETE", "NORMAL"), ("WAL", "FULL"), ("WAL", "NORMAL")])}
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
        p = stats.fisher_exact(tabela, alternative="greater").pvalue
        linhas.append({"comparacao": f"{ja}/{sa} perde mais que {jb}/{sb}", "com_perda_a": tabela[0][0],
                       "n_a": len(a), "com_perda_b": tabela[1][0], "n_b": len(b), "p": float(p)})
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = holm(tabela["p"].tolist())
    tabela["rejeita_h0"] = tabela["p_holm"] < ALFA
    return tabela


# ------------------------------------------------------------------------------------------------ relatorio
def _n(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _vezes(x: float) -> str:
    return f"{_n(x, 0 if x >= 100 else 2)}×"


def _p(p: float) -> str:
    return "< 0,001" if p < 0.001 else _n(p, 3)


def _pct(x: float) -> str:
    return f"{_n(100 * x, 0)}%"


def markdown(rep: pd.DataFrame, comp: pd.DataFrame, dur: pd.DataFrame, resumo: pd.DataFrame,
             testes: pd.DataFrame) -> str:
    ver = rep.groupby("ambiente")["sqlite"].first()
    rodadas = dur.groupby("falha")["rodada"].max()
    linhas = [
        "# Lab05 — Replicação no Linux e durabilidade medida (#137)",
        "",
        f"> Gerado por `python -m labs.lab05_sqlite.robustez` a partir de `data/raw/coleta_completa.csv`, "
        f"`coleta_linux.csv` e `durabilidade.csv`. Tudo rodou na mesma máquina: Windows 11 (SQLite {ver['Windows']}) "
        f"e Ubuntu 26.04 no WSL2 com ext4 (SQLite {ver['Linux']}).",
        "",
        "## 1. Replicação no Linux",
        "",
        "A coleta completa (30 blocos × 3 cargas × 4 configurações) foi repetida no Ubuntu, com os bancos no ext4 "
        "(o `/tmp` do WSL fica em memória e foi evitado). Mudam o sistema operacional, o sistema de arquivos e a "
        "versão do SQLite; o hardware é o mesmo. Cada ambiente foi analisado com os mesmos testes do estudo "
        "principal.",
        "",
        "| Comparação | Windows | Linux | Mesma direção? | Mesma conclusão? |",
        "| --- | ---: | ---: | :---: | :---: |",
    ]
    for _, c in comp.iterrows():
        desc = next(x.descricao for x in COMPARACOES if x.codigo == c["codigo"])
        w = rep[(rep["ambiente"] == "Windows") & (rep["codigo"] == c["codigo"])].iloc[0]
        lx = rep[(rep["ambiente"] == "Linux") & (rep["codigo"] == c["codigo"])].iloc[0]
        cel = lambda r: (f"{_vezes(r['razao'])} [{_n(r['ic_inf'])}; {_n(r['ic_sup'])}] · "
                         f"p {_p(r.get('p_holm') if pd.notna(r.get('p_holm')) else r['p'])}")
        linhas.append(f"| **{c['codigo']}** {desc} | {cel(w)} | {cel(lx)} | "
                      f"{'Sim' if c['mesma_direcao'] else 'Não'} | {'Sim' if c['mesma_conclusao'] else 'Não'} |")
    mesmas = int(comp["mesma_conclusao"].sum())
    linhas += [
        "",
        "Razão das medianas (IC 95% por *bootstrap*); p de Holm nas confirmatórias e p bruto nas exploratórias.",
        "",
        f"**Leitura:** {mesmas} de {len(comp)} conclusões se repetem no Linux. A **direção** dos efeitos se "
        "generaliza, mas a **magnitude** depende do ambiente: o custo de sincronizar o disco e de travar arquivos "
        "muda de um sistema para outro. Por isso o estudo afirma efeitos relativos e não um número universal. "
        "Como sistema, sistema de arquivos e versão mudam juntos, não dá para atribuir a diferença de magnitude a "
        "um deles isoladamente.",
        "",
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
    linhas += ["", "## 3. O que isso muda nas conclusões", "", *conclusoes(resumo, testes, comp, rep), ""]
    return "\n".join(linhas)


def conclusoes(resumo: pd.DataFrame, testes: pd.DataFrame, comp: pd.DataFrame, rep: pd.DataFrame) -> list[str]:
    """Cada frase depende dos dados; nada e afirmado sem o numero que o sustenta."""
    def linha(falha: str, j: str, s: str) -> pd.Series:
        sel = resumo[(resumo["falha"] == falha) & (resumo["journal_mode"] == j) & (resumo["synchronous"] == s)]
        return sel.iloc[0]

    def razao(codigo: str) -> float:
        return float(rep[(rep["ambiente"] == "Windows") & (rep["codigo"] == codigo)]["razao"].iloc[0])

    def teste(texto: str) -> pd.Series:
        return testes[testes["comparacao"].str.startswith(texto)].iloc[0]

    itens = []
    proc = resumo[resumo["falha"] == "processo"]
    if not proc.empty:
        k, n = int(proc["rodadas_com_perda"].sum()), int(proc["rodadas"].sum())
        itens.append(f"**Travar o app {'não perdeu dados em nenhuma configuração' if k == 0 else 'também perdeu dados'}"
                     f"** ({k} rodadas com perda em {n}). "
                     + ("O risco do `synchronous` aparece só na queda do sistema ou de energia." if k == 0 else ""))
    if (resumo["falha"] == "sistema").any():
        wn, wf = linha("sistema", "WAL", "NORMAL"), linha("sistema", "WAL", "FULL")
        t = teste("WAL/NORMAL")
        itens.append(
            f"**Custo medido do NORMAL:** na queda do sistema, `WAL/NORMAL` perdeu transações confirmadas em "
            f"{wn['rodadas_com_perda']} de {wn['rodadas']} rodadas (até {wn['perdidas_max']} por queda), contra "
            f"{wf['rodadas_com_perda']} de {wf['rodadas']} no `WAL/FULL` (Fisher, p Holm {_p(t['p_holm'])}). "
            f"É a contrapartida dos {_vezes(razao('H-3'))} de H-3"
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
            frase += (f" O `WAL/FULL` não perdeu nada e grava {_vezes(razao('H-1'))} mais rápido que o "
                      "`DELETE/FULL` (H-1).")
        itens.append(frase)
    total, integras = int(resumo["rodadas"].sum()), int(resumo["integras"].sum())
    itens.append(f"**Integridade:** {integras} de {total} bancos passaram no `PRAGMA integrity_check` depois da falha"
                 + (": as perdas são de transações recentes, não corrupção." if integras == total else "."))
    itens.append(f"**Validade externa:** {int(comp['mesma_conclusao'].sum())} de {len(comp)} conclusões se repetem "
                 "no Linux, com magnitudes diferentes.")
    return [f"{i}. {texto}" for i, texto in enumerate(itens, start=1)]


def gerar(destino_doc: Path = DOC) -> dict:
    coletas = carregar_coletas()
    rep = replicacao(coletas)
    comp = comparar_ambientes(rep)
    dur = carregar_durabilidade()
    resumo = resumo_durabilidade(dur)
    testes = testes_durabilidade(dur)
    PROCESSADOS.mkdir(parents=True, exist_ok=True)
    rep.to_csv(PROCESSADOS / "robustez_replicacao.csv", index=False, lineterminator="\n")
    resumo.to_csv(PROCESSADOS / "robustez_durabilidade.csv", index=False, lineterminator="\n")
    testes.to_csv(PROCESSADOS / "robustez_durabilidade_testes.csv", index=False, lineterminator="\n")
    destino_doc.write_text(markdown(rep, comp, dur, resumo, testes), encoding="utf-8")
    return {"replicacao": rep, "comparacao": comp, "durabilidade": resumo, "testes": testes}


if __name__ == "__main__":
    r = gerar()
    print(r["comparacao"].to_string(index=False))
    print(r["durabilidade"].to_string(index=False))
    print(r["testes"].to_string(index=False))
    print(f"relatorio em {DOC}")
