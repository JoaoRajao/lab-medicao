"""Dashboard dos resultados gold. Execute: streamlit run dashboard/app.py"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.data import available_labs, read_gold, table_path  # noqa: E402

st.set_page_config(page_title="Lab Medição | Explorar dados", page_icon="📊", layout="wide")

st.markdown("""
<style>
  .block-container { max-width: 1320px; padding-top: 2.2rem; }
  h1, h2, h3 { color: #17324d; }
  [data-testid="stMetric"] { background: #eef5fb; border: 1px solid #d7e7f4;
      border-radius: 12px; padding: 14px 18px; }
  [data-testid="stMetric"] * { color: #17324d !important; }
  [data-testid="stSidebar"] { background: #f5f8fb; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load(lab: str, table: str, modified_ns: int) -> pd.DataFrame:
    return read_gold(lab, table)


def gold(lab: str, table: str) -> pd.DataFrame:
    path = table_path(lab, table)
    return load(lab, table, path.stat().st_mtime_ns)


LAB03_DATASET = PROJECT_ROOT / "labs" / "lab03_dora" / "data" / "dataset.csv"


@st.cache_data(show_spinner=False)
def load_lab03(modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(LAB03_DATASET)


def csv_button(frame: pd.DataFrame, filename: str) -> None:
    st.download_button("Baixar dados desta visão (CSV)", frame.to_csv(index=False).encode("utf-8-sig"),
                       file_name=filename, mime="text/csv")


def lab01() -> None:
    st.header("Lab 01 · Repositórios populares")
    age = gold("lab01", "gold_lab01_rq01_age").iloc[0]
    prs = gold("lab01", "gold_lab01_rq02_pull_requests").iloc[0]
    releases = gold("lab01", "gold_lab01_rq03_releases").iloc[0]
    updates = gold("lab01", "gold_lab01_rq04_updates").iloc[0]
    a, b, c, d = st.columns(4)
    a.metric("Repositórios", f"{int(age['total_repositories']):,}")
    b.metric("Idade mediana", f"{age['median_age_days']:,.0f} dias")
    c.metric("PRs aceitos · mediana", f"{prs['median_accepted_pull_requests']:,.0f}")
    d.metric("Releases · mediana", f"{releases['median_releases_count']:,.0f}")
    st.caption(f"Última atualização dos repos · mediana: {updates['median_days_since_last_update']:,.0f} dias")

    languages = gold("lab01", "gold_lab01_rq05_popular_languages")
    issues = gold("lab01", "gold_lab01_rq06_closed_issues")
    comparison = gold("lab01", "gold_lab01_rq07_popular_language_comparison")
    tab1, tab2, tab3 = st.tabs(["Linguagens", "Issues fechadas", "Comparação"])
    with tab1:
        top = st.slider("Mostrar as N linguagens mais frequentes", 5, min(30, len(languages)),
                        min(10, len(languages))) if len(languages) >= 5 else len(languages)
        subset = languages.nlargest(top, "repositories_count")
        st.bar_chart(subset.set_index("primary_language")["repositories_count"],
                     x_label="Linguagem", y_label="Repositórios")
        st.dataframe(subset, width="stretch", hide_index=True)
        csv_button(subset, "lab01_linguagens.csv")
    with tab2:
        st.bar_chart(issues.set_index("closed_issues_band")["repositories_count"],
                     x_label="Faixa de issues fechadas", y_label="Repositórios")
        st.dataframe(issues, width="stretch", hide_index=True)
        csv_button(issues, "lab01_issues.csv")
    with tab3:
        st.bar_chart(comparison.set_index("language_group")[["avg_accepted_pull_requests", "avg_releases_count"]],
                     x_label="Grupo", y_label="Média")
        st.dataframe(comparison, width="stretch", hide_index=True)
        csv_button(comparison, "lab01_comparacao.csv")


def lab02() -> None:
    st.header("Lab 02 · IA versus programação manual")
    st.caption("Resultados agregados dos modelos dbt gold. Os filtros atuam nas linhas de tratamento publicadas.")
    time = gold("lab02", "gold_lab02_rq01_time")
    defects = gold("lab02", "gold_lab02_rq02_defects")
    quality = gold("lab02", "gold_lab02_rq03_static_metrics")
    choices = sorted(time["treatment"].dropna().tolist())
    selected = st.multiselect("Tratamentos", choices, default=choices)
    if not selected:
        st.info("Selecione pelo menos um tratamento.")
        return
    time = time[time["treatment"].isin(selected)]
    defects = defects[defects["treatment"].isin(selected)]
    quality = quality[quality["treatment"].isin(selected)]
    a, b, c = st.columns(3)
    a.metric("Trials", f"{int(time['trials_count'].sum())}")
    b.metric("Trials censurados", f"{int(time['censored_trials'].sum())}")
    c.metric("Sucesso médio de aceitação", f"{defects['avg_acceptance_success_rate'].mean():.1%}")

    tab1, tab2, tab3 = st.tabs(["RQ1 · Tempo", "RQ2 · Defeitos", "RQ3 · Qualidade"])
    with tab1:
        st.bar_chart(time.set_index("treatment")[["median_time_to_green_seconds", "avg_time_to_green_seconds"]],
                     x_label="Tratamento", y_label="Segundos")
        st.dataframe(time, width="stretch", hide_index=True)
        csv_button(time, "lab02_tempo.csv")
    with tab2:
        st.bar_chart(defects.set_index("treatment")[["avg_acceptance_success_rate", "green_trial_rate"]],
                     x_label="Tratamento", y_label="Proporção")
        st.dataframe(defects, width="stretch", hide_index=True)
        csv_button(defects, "lab02_defeitos.csv")
    with tab3:
        metric = st.selectbox("Métrica", ["avg_cyclomatic_complexity", "avg_maintainability_index",
                                          "avg_loc", "avg_duplication_pct"],
                              format_func=lambda x: {
                                  "avg_cyclomatic_complexity": "Complexidade ciclomatica média",
                                  "avg_maintainability_index": "Índice de manutenibilidade médio",
                                  "avg_loc": "Linhas de código médias",
                                  "avg_duplication_pct": "Duplicação média (%)",
                              }[x])
        st.bar_chart(quality.set_index("treatment")[metric], x_label="Tratamento", y_label=metric)
        st.dataframe(quality, width="stretch", hide_index=True)
        csv_button(quality, "lab02_qualidade.csv")


def lab03() -> None:
    st.header("Lab 03 · Métricas DORA")
    st.caption("Amostra de repositórios open source · janela de 01/10/2025 a 30/09/2026 · fonte: dataset.csv")
    data = load_lab03(LAB03_DATASET.stat().st_mtime_ns)
    required = {"repository", "language", "stars", "dora_category",
                "deployment_frequency_per_week", "lead_time_a_hours", "cfr_a",
                "recovery_median_hours", "cfr_b"}
    missing = required - set(data.columns)
    if missing:
        st.error(f"O dataset do Lab03 nao tem as colunas: {', '.join(sorted(missing))}")
        return

    a, b, c = st.columns(3)
    language = a.selectbox("Linguagem", ["Todas", *sorted(data["language"].dropna().unique())])
    category = b.selectbox("Categoria DORA", ["Todas", "Elite", "High", "Medium", "Low"])
    min_stars = c.number_input("Estrelas mínimas", min_value=0, value=0, step=100)
    filtered = data[data["stars"] >= min_stars].copy()
    if language != "Todas":
        filtered = filtered[filtered["language"] == language]
    if category != "Todas":
        filtered = filtered[filtered["dora_category"] == category]
    if filtered.empty:
        st.info("Nenhum repositório atende aos filtros.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Repositórios", f"{len(filtered):,}")
    m2.metric("Deploys/semana", f"{filtered['deployment_frequency_per_week'].median():.2f}")
    m3.metric("Lead time (h)", f"{filtered['lead_time_a_hours'].median():.1f}")
    st.caption(f"Medianas na seleção: CFR de CI {filtered['cfr_a'].median():.1%} · "
               f"recuperação {filtered['recovery_median_hours'].median():.2f} h. "
               "Valores ausentes não entram na mediana.")

    overview, relationship, rows = st.tabs(["Classificação", "Velocidade × falhas", "Repositórios"])
    with overview:
        counts = filtered["dora_category"].value_counts().reindex(["Low", "Medium", "High", "Elite"], fill_value=0)
        st.bar_chart(counts.rename("Repositórios"), x_label="Categoria DORA C1", y_label="Repositórios")
        st.caption("C1 usa releases como deploy, lead time por release e CFR de CI.")
        st.dataframe(counts.rename_axis("Categoria").reset_index(), width="stretch", hide_index=True)
    with relationship:
        plot = filtered[["repository", "deployment_frequency_per_week", "cfr_a"]].dropna()
        st.scatter_chart(plot, x="deployment_frequency_per_week", y="cfr_a",
                         x_label="Deploys por semana", y_label="CFR de CI")
        st.caption("CFR (a) é um proxy de falhas em CI. CFR (b) usa uma heurística de releases "
                   "corretivas e ainda requer validação; os dois não medem o mesmo fenômeno.")
    with rows:
        columns = ["repository", "language", "stars", "dora_category",
                   "deployment_frequency_per_week", "lead_time_a_hours", "cfr_a",
                   "cfr_b", "recovery_median_hours"]
        st.dataframe(filtered[columns], width="stretch", hide_index=True)
    csv_button(filtered, "lab03_dora_filtrado.csv")


st.title("Laboratório de Medição")
st.write("Explore os resultados dos laboratórios e filtre os dados usados nas análises.")
labs = (["lab03"] if LAB03_DATASET.is_file() else []) + available_labs()
if not labs:
    st.warning("Ainda não há dados disponíveis para o dashboard.")
    st.code("python -m labs.lab03_dora.consolidacao --config labs/lab03_dora/config.yaml", language="bash")
    st.stop()

labels = {"lab01": "Lab 01 · GitHub", "lab02": "Lab 02 · IA vs manual", "lab03": "Lab 03 · DORA"}
with st.sidebar:
    st.header("Explorar")
    lab = st.radio("Laboratório", labs, format_func=lambda name: labels[name])
    if lab == "lab03":
        st.caption("Fonte: labs/lab03_dora/data/dataset.csv. Recarregue a página após a consolidação.")
    else:
        st.caption("Fonte: tabelas gold publicadas em data/published/. Atualize a página após uma nova publicação.")

if lab == "lab03":
    lab03()
elif lab == "lab01":
    lab01()
else:
    lab02()
