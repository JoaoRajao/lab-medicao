from __future__ import annotations

import base64
import html
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from labs.lab02_ia_vs_manual.analysis.data import KATA_CODES, KATAS, TRIAL_FILES
from labs.lab02_ia_vs_manual.analysis.stats import TREATMENTS, effect_size, iqr_outliers, summarize

LABELS = {"manual": "Manual", "ai_assisted": "Com IA"}
STATIC_METRICS = {
    "cyclomatic_complexity_avg": "Complexidade ciclomatica (media)",
    "maintainability_index": "Indice de manutenibilidade",
    "loc": "LOC",
    "duplication_pct": "Duplicacao (%)",
}
STATUS = {
    "SINTETICO": ("Dados sinteticos", "syn"),
    "PRELIMINAR": ("Preliminar", "warn"),
    None: ("Validado", "ok"),
}

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14171f;--muted:#5d6675;--line:#e3e6ec;--blue:#2a78d6;--orange:#e8833a;
--ok:#1f8a4c;--warn:#b7791f;--bad:#c0392b;--syn:#6b4fbb}
@media (prefers-color-scheme:dark){:root{--bg:#0f1218;--card:#181c25;--ink:#eceff5;--muted:#9aa3b2;--line:#2a303c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:28px clamp(16px,4vw,48px) 8px}h1{margin:0 0 4px;font-size:24px}h2{margin:0 0 4px;font-size:18px}
.sub{color:var(--muted)}main{padding:8px clamp(16px,4vw,48px) 48px;max-width:1240px;margin:0 auto}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:600;color:#fff;vertical-align:middle;margin-left:8px}
.pill.ok{background:var(--ok)}.pill.warn{background:var(--warn)}.pill.syn{background:var(--syn)}
.grid{display:grid;gap:14px}.kpis{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.kpi .v{font-size:26px;font-weight:700;line-height:1.2}.kpi .l{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.kpi .n{color:var(--muted);font-size:12px;margin-top:2px}
section{margin-top:28px}.two{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
img{max-width:100%;height:auto;border-radius:8px;display:block}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child,td.l,th.l{text-align:left}th{color:var(--muted);font-weight:600;cursor:default}
table.sortable th{cursor:pointer}table.sortable th:hover{color:var(--ink)}.scroll{overflow-x:auto}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;font-weight:600;background:var(--line)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.m{background:var(--blue)}.a{background:var(--orange)}.banner{border-left:4px solid var(--warn);background:var(--card);padding:12px 16px;border-radius:8px;margin:14px 0}
.banner.syn{border-color:var(--syn)}details summary{cursor:pointer;font-weight:600}ul{margin:8px 0 0;padding-left:18px}
.note{color:var(--muted);font-size:12px;margin-top:8px}.filters{margin:0 0 10px;display:flex;gap:8px;flex-wrap:wrap}
.filters button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:4px 12px;cursor:pointer}
.filters button.on{background:var(--ink);color:var(--bg)}footer{color:var(--muted);font-size:12px;margin-top:32px}
"""

JS = """
const rows=()=>[...document.querySelectorAll('#trials tbody tr')];
document.querySelectorAll('#trials th').forEach((th,i)=>th.addEventListener('click',()=>{
 const asc=th.dataset.asc!=='1';document.querySelectorAll('#trials th').forEach(t=>t.dataset.asc='');th.dataset.asc=asc?'1':'';
 const key=r=>{const c=r.children[i];const v=c.dataset.v??c.textContent;const n=parseFloat(v);return isNaN(n)?v:n};
 const body=document.querySelector('#trials tbody');
 rows().sort((a,b)=>{const x=key(a),y=key(b);return (x>y?1:x<y?-1:0)*(asc?1:-1)}).forEach(r=>body.appendChild(r));}));
document.querySelectorAll('.filters button').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.filters button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
 rows().forEach(r=>r.style.display=(b.dataset.f==='all'||r.dataset.t===b.dataset.f)?'':'none');}));
"""


def _num(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _img(path: Path, alt: str) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{data}">'


def _median(df: pd.DataFrame, treatment: str, column: str) -> float:
    return df.loc[df["treatment"] == treatment, column].median()


def _kpi(label: str, value: str, note: str = "") -> str:
    return f'<div class="card kpi"><div class="l">{label}</div><div class="v">{value}</div><div class="n">{note}</div></div>'


def _kpis(df: pd.DataFrame) -> str:
    med_manual, med_ai = _median(df, "manual", "time_to_green_min"), _median(df, "ai_assisted", "time_to_green_min")
    change = (med_ai - med_manual) / med_manual * 100 if med_manual else float("nan")
    green = {t: int(((df["treatment"] == t) & (df["tests_failed"] == 0)).sum()) for t in TREATMENTS}
    total = {t: int((df["treatment"] == t).sum()) for t in TREATMENTS}
    participants = df["participant"].nunique()
    return "".join([
        _kpi("Trials coletados", f"{len(df)}/{len(TRIAL_FILES) * len(KATAS)}", f"{participants} de {len(TRIAL_FILES)} participantes"),
        _kpi("Mediana de tempo - Manual", f"{_num(med_manual)} min", f"n={total['manual']}"),
        _kpi("Mediana de tempo - Com IA", f"{_num(med_ai)} min", f"n={total['ai_assisted']}"),
        _kpi("Variacao da mediana (IA vs manual)", "-" if pd.isna(change) else f"{change:+.0f}%".replace(".", ","), "descritivo, sem teste"),
        _kpi("Trials verdes - Manual", f"{green['manual']}/{total['manual']}", "todos os testes passando"),
        _kpi("Trials verdes - Com IA", f"{green['ai_assisted']}/{total['ai_assisted']}", "todos os testes passando"),
        _kpi("Censurados", str(int(df["censored"].sum())), "estouraram 35 min"),
    ])


def _summary_table(df: pd.DataFrame, rows: dict[str, str], digits: int = 1) -> str:
    body = []
    for column, label in rows.items():
        summary = summarize(df, column).set_index("treatment")
        delta, magnitude = effect_size(df, column)
        cells = [f'<td class="l">{label}</td>']
        for treatment in TREATMENTS:
            if treatment in summary.index:
                s = summary.loc[treatment]
                cells.append(f"<td>{_num(s['median'], digits)} <span class='sub'>[{_num(s['q1'], digits)}-{_num(s['q3'], digits)}]</span></td>")
            else:
                cells.append("<td>-</td>")
        cells.append(f"<td>{_num(delta, 2)} <span class='chip'>{magnitude}</span></td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    head = "<th class='l'>Metrica</th><th>Manual: mediana [Q1-Q3]</th><th>Com IA: mediana [Q1-Q3]</th><th>Cliff's delta (IA vs manual)</th>"
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _trials_table(df: pd.DataFrame) -> str:
    order = {kata: i for i, kata in enumerate(KATAS)}
    ordered = df.assign(_k=df["kata"].map(order)).sort_values(["participant", "_k"])
    body = []
    for row in ordered.itertuples():
        dot = "m" if row.treatment == "manual" else "a"
        status = "censurado" if row.censored else ("verde" if row.tests_failed == 0 else "falhou")
        body.append(
            f'<tr data-t="{row.treatment}"><td class="l">{row.participant}</td>'
            f'<td class="l">{KATA_CODES.get(row.kata, "")} {html.escape(row.kata)}</td>'
            f'<td class="l"><span class="dot {dot}"></span>{LABELS[row.treatment]}</td>'
            f'<td data-v="{row.time_to_green_seconds}">{_num(row.time_to_green_min)}</td>'
            f"<td>{row.tests_passed}/{row.tests_passed + row.tests_failed}</td><td class='l'>{status}</td>"
            f"<td>{_num(row.cyclomatic_complexity_avg, 2)}</td><td>{_num(row.maintainability_index)}</td>"
            f"<td>{int(row.loc)}</td><td>{_num(row.duplication_pct)}</td></tr>"
        )
    heads = ["Part.", "Kata", "Tratamento", "Tempo (min)", "Testes", "Status", "CC media", "MI", "LOC", "Dup. %"]
    ths = "".join(f"<th class='{'l' if i < 3 or i == 5 else ''}'>{h}</th>" for i, h in enumerate(heads))
    filters = '<div class="filters"><button class="on" data-f="all">Todos</button><button data-f="manual">Manual</button><button data-f="ai_assisted">Com IA</button></div>'
    return f'{filters}<div class="scroll"><table id="trials" class="sortable"><thead><tr>{ths}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _quality(problems: list[str], warning: str | None) -> str:
    if not problems:
        return '<div class="banner" style="border-color:var(--ok)"><b>Integridade:</b> nenhum aviso de validacao.</div>'
    css = "banner syn" if warning == "SINTETICO" else "banner"
    items = "".join(f"<li>{html.escape(p)}</li>" for p in problems)
    return (f'<div class="{css}"><details open><summary>Qualidade dos dados: {len(problems)} aviso(s)</summary>'
            f"<ul>{items}</ul><div class='note'>Enquanto houver avisos, os resultados sao preliminares.</div></details></div>")


def _outliers(df: pd.DataFrame) -> str:
    flagged = iqr_outliers(df, "time_to_green_seconds")
    if flagged.empty:
        return "<p class='note'>Nenhum outlier de tempo pela regra 1,5xIQR dentro de cada tratamento.</p>"
    items = "".join(f"<li>{html.escape(r.trial_id)}: {_num(r.time_to_green_min)} min</li>" for r in flagged.itertuples())
    return f"<p class='note'>Outliers de tempo (regra 1,5xIQR por tratamento):</p><ul>{items}</ul>"


def write_dashboard_html(df: pd.DataFrame, figures: dict[str, Path], problems: list[str],
                         warning: str | None, output_path: Path) -> Path:
    label, css = STATUS[warning]
    sections = f"""
<section><h2>Visao geral</h2><div class="grid kpis">{_kpis(df)}</div></section>
{_quality(problems, warning)}
<section><h2>RQ1 - Tempo ate passar nos testes</h2>
<div class="grid two"><div class="card">{_img(figures['rq1_tempo_boxplot'], 'Boxplot do tempo por tratamento')}</div>
<div class="card">{_img(figures['rq1_tempo_por_kata'], 'Tempo por kata e tratamento')}</div></div>
<div class="card" style="margin-top:14px">{_summary_table(df, {'time_to_green_seconds': 'Tempo ate verde (s)'}, 0)}
{_outliers(df)}<div class="note">Teste de Wilcoxon: pendente (issue de analise estatistica).</div></div></section>
<section><h2>RQ2 - Taxa de sucesso e defeitos</h2>
<div class="card">{_img(figures['rq2_sucesso'], 'Trials verdes por tratamento')}</div>
<div class="card" style="margin-top:14px">{_summary_table(df, {'acceptance_success_rate': 'Taxa de sucesso nos testes', 'tests_failed': 'Testes falhos por trial'}, 2)}
<div class="note">Com a maioria dos trials verdes, a taxa e quase constante; a comparacao real depende de N maior.</div></div></section>
<section><h2>RQ3 - Metricas estaticas</h2>
<div class="grid two"><div class="card">{_img(figures['rq3_metricas_boxplot'], 'Metricas estaticas por tratamento')}</div>
<div class="card">{_img(figures['rq3_loc_vs_complexidade'], 'LOC contra complexidade')}<div style="height:12px"></div>
{_img(figures['correlacao_metricas'], 'Correlacao entre metricas')}</div></div>
<div class="card" style="margin-top:14px">{_summary_table(df, STATIC_METRICS, 2)}
<div class="note">LOC e o controle de verbosidade: diferenca de complexidade que acompanha o LOC indica verbosidade, nao complexidade real.</div></div></section>
<section><h2>Trials</h2><div class="card">{_trials_table(df)}</div></section>
"""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sources = ", ".join(p.name for p in TRIAL_FILES.values() if p.exists()) or "trials_sample.jsonl"
    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Dashboard Lab02</title><style>{CSS}</style></head><body>
<header><h1>Lab02 - Assistentes de IA vs codificacao manual<span class="pill {css}">{label}</span></h1>
<div class="sub">Dashboard de resultados por questao de pesquisa. Mediana e IQR; cada ponto dos graficos e um trial.</div></header>
<main>{sections}<footer>Gerado em {generated}. Fontes: {html.escape(sources)}. Legenda:
<span class="dot m"></span>Manual <span class="dot a"></span>Com IA.</footer></main><script>{JS}</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    return output_path
