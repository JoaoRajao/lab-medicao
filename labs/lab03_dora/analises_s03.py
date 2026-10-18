"""Analises reexecutaveis da Sprint 3 (issues #75, #76 e #77).

    python -m labs.lab03_dora.analises_s03

Le somente os CSVs versionados. Nao chama a API do GitHub nem altera o dataset de entrada.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu, spearmanr
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.multitest import multipletests

from labs.lab03_dora.metricas.dora import CATEGORIES, classify

LAB_DIR = Path(__file__).resolve().parent
ROOT = LAB_DIR.parents[1]
DEFAULT_DATASET = LAB_DIR / "data" / "dataset.csv"
DEFAULT_CONSENSUS = LAB_DIR / "amostra_ouro" / "consenso_repositorios.csv"
DEFAULT_RELEASES = LAB_DIR / "data" / "cfr_b_releases.csv"
DEFAULT_OUTPUT = LAB_DIR / "data" / "analise_s03"
DEFAULT_FIGURES = ROOT / "docs" / "lab03" / "assets"

METRICS = (
    ("RQ01", "deployment_frequency_per_week", "releases/semana"),
    ("RQ02a", "lead_time_a_hours", "horas"),
    ("RQ02b", "lead_time_b_hours", "horas"),
    ("RQ03a", "cfr_a", "fracao"),
    ("RQ03b", "cfr_b", "fracao"),
    ("RQ04", "recovery_median_hours", "horas"),
)
C1_OUTCOMES = (
    ("deployment_frequency_per_week", "releases/semana"),
    ("lead_time_a_hours", "horas"),
    ("cfr_a", "fracao"),
    ("recovery_median_hours", "horas"),
)
CATEGORY_ORDER = ("Low", "Medium", "High", "Elite")
CATEGORY_POINTS = {name: points for points, name in CATEGORIES.items()}


def _number(value: object) -> float | None:
    return None if pd.isna(value) else float(value)


def _summary(values: pd.Series | np.ndarray) -> dict[str, float | int]:
    clean = pd.to_numeric(pd.Series(values), errors="raise").dropna().to_numpy(dtype=float)
    if not len(clean):
        return {"n": 0, "mediana": np.nan, "q1": np.nan, "q3": np.nan, "iqr": np.nan}
    q1, median, q3 = np.quantile(clean, [0.25, 0.5, 0.75], method="linear")
    return {"n": len(clean), "mediana": median, "q1": q1, "q3": q3, "iqr": q3 - q1}


def load_inputs(dataset_path: Path, consensus_path: Path, releases_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dataset = pd.read_csv(dataset_path)
    consensus = pd.read_csv(consensus_path)
    releases = pd.read_csv(releases_path)
    required = {"repository", "stars", "language", "contributors", "dora_category", "dora_metrics_used",
                "cfr_b_releases_evaluated", "cfr_b_releases_censored", "recovery_episodes", "censored_episodes"}
    required |= {column for _, column, _ in METRICS}
    required |= {"deployment_frequency_with_prereleases_per_week", "deployment_frequency_tags_per_week",
                 "df_points", "lead_time_points", "cfr_points", "recovery_points", "dora_points"}
    missing = required - set(dataset.columns)
    if missing:
        raise ValueError(f"dataset.csv sem colunas: {sorted(missing)}")
    if len(dataset) != 300 or dataset.repository.isna().any() or dataset.repository.duplicated().any():
        raise ValueError("dataset.csv deve conter 300 repositorios unicos e identificados")
    if not {"repositorio", "tipo_projeto"}.issubset(consensus.columns):
        raise ValueError("consenso_repositorios.csv sem repositorio/tipo_projeto")
    if len(consensus) != 60 or consensus.repositorio.isna().any() or consensus.repositorio.duplicated().any():
        raise ValueError("consenso_repositorios.csv deve conter 60 repositorios unicos")
    if not set(consensus.repositorio).issubset(set(dataset.repository)):
        raise ValueError("Consenso contem repositorio fora do dataset")
    if not {"repository", "tag_name", "corrective", "censored", "heuristic_version"}.issubset(releases.columns):
        raise ValueError("cfr_b_releases.csv sem colunas para o rework rate")
    if releases.empty or releases[["repository", "tag_name"]].isna().any().any():
        raise ValueError("cfr_b_releases.csv vazio ou com chaves ausentes")
    if releases.duplicated(["repository", "tag_name"]).any():
        raise ValueError("Release duplicada no cfr_b_releases.csv")
    if not set(releases.repository).issubset(set(dataset.repository)):
        raise ValueError("Releases fora do dataset")
    if set(releases.corrective) - {"sim", "nao"}:
        raise ValueError("Releases sem classificacao corretiva valida")
    if set(releases.censored.astype(str).str.lower()) - {"true", "false"}:
        raise ValueError("Releases sem indicador de censura valido")
    if releases.heuristic_version.nunique() != 1:
        raise ValueError("Releases misturam versoes da heuristica")
    return dataset, consensus, releases


def descriptive(dataset: pd.DataFrame, releases: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries = [{"rq": rq, "metrica": column, "unidade": unit, **_summary(dataset[column])}
                 for rq, column, unit in METRICS]
    classifications = []
    for metric, column in (
        ("deployment_frequency", "df_points"), ("lead_time_a", "lead_time_points"),
        ("cfr_a", "cfr_points"), ("recovery", "recovery_points"), ("geral_C1", "dora_points"),
    ):
        points = pd.to_numeric(dataset[column], errors="coerce")
        for category in CATEGORY_ORDER:
            classifications.append({"metrica": metric, "categoria": category,
                                    "repositorios": int((points == CATEGORY_POINTS[category]).sum())})
        classifications.append({"metrica": metric, "categoria": "indisponivel",
                                "repositorios": int(points.isna().sum())})
    censored = []
    release_censored = releases.censored.astype(str).str.lower().eq("true")
    for rq, numerator, denominator in (
        ("RQ03b", int(release_censored.sum()), len(releases)),
        ("RQ04", int(dataset.censored_episodes.sum()), int(dataset.recovery_episodes.sum())),
    ):
        censored.append({"rq": rq, "censurados": numerator, "casos": denominator,
                         "proporcao": numerator / denominator if denominator else np.nan})
    return pd.DataFrame(summaries), pd.DataFrame(classifications), pd.DataFrame(censored)


def correlations(dataset: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant in ("cfr_a", "cfr_b"):
        pairs = dataset[["deployment_frequency_per_week", variant]].dropna()
        if len(pairs) < 3 or pairs.nunique().min() < 2:
            rho, p = np.nan, np.nan
        else:
            rho, p = spearmanr(pairs.iloc[:, 0], pairs.iloc[:, 1])
        rows.append({"rq": "RQ05", "cfr": variant, "n": len(pairs), "rho": rho, "p_valor": p})
    return pd.DataFrame(rows)


def draw_correlations(dataset: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    for variant in ("cfr_a", "cfr_b"):
        pairs = dataset[["deployment_frequency_per_week", variant]].dropna()
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        ax.scatter(pairs.iloc[:, 0], pairs.iloc[:, 1], alpha=0.55, s=22)
        positive = pairs.iloc[:, 0][pairs.iloc[:, 0] > 0]
        if len(positive) and positive.max() / positive.min() >= 100:
            ax.set_xscale("symlog", linthresh=float(positive.min()))
        ax.set_xlabel("Frequencia de deploy (releases/semana)")
        variant_label = f"CFR ({variant[-1]})"
        ax.set_ylabel(f"{variant_label} (fracao)")
        ax.set_title(f"RQ05: frequencia de deploy e {variant_label} (n={len(pairs)})")
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(figures_dir / f"rq05_frequencia_{variant}.png", dpi=160)
        plt.close(fig)


def _quartiles(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    result = pd.Series(pd.NA, index=series.index, dtype="string")
    valid = numeric.dropna()
    if valid.empty:
        return result
    groups = pd.qcut(valid, 4, labels=False, duplicates="drop")
    result.loc[valid.index] = groups.map(lambda group: f"Q{int(group) + 1}").astype("string")
    return result


def _cliffs_delta(first: np.ndarray, second: np.ndarray) -> float:
    return float(((first[:, None] > second).sum() - (first[:, None] < second).sum()) /
                 (len(first) * len(second)))


def _magnitude(delta: float) -> str:
    size = abs(delta)
    if size < 0.147:
        return "desprezivel"
    if size < 0.33:
        return "pequeno"
    if size < 0.474:
        return "medio"
    return "grande"


def _with_groups(dataset: pd.DataFrame, consensus: pd.DataFrame) -> pd.DataFrame:
    data = dataset.merge(consensus[["repositorio", "tipo_projeto"]], how="left", left_on="repository",
                         right_on="repositorio", validate="one_to_one")
    top_languages = dataset.language.value_counts().head(5).index
    data["grupo_linguagem"] = data.language.where(data.language.isin(top_languages), "Outras")
    data["grupo_estrelas"] = _quartiles(data.stars)
    data["grupo_contribuidores"] = _quartiles(data.contributors)
    return data


def subgroups(dataset: pd.DataFrame, consensus: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = _with_groups(dataset, consensus)
    factors = (("linguagem", "grupo_linguagem"), ("estrelas", "grupo_estrelas"),
               ("contribuidores", "grupo_contribuidores"), ("tipo_projeto", "tipo_projeto"))
    descriptions, tests, pairwise = [], [], []
    for factor, group_column in factors:
        for metric, unit in C1_OUTCOMES:
            samples = {}
            for group, subset in data.dropna(subset=[group_column]).groupby(group_column, sort=True):
                values = pd.to_numeric(subset[metric], errors="raise").dropna().to_numpy(dtype=float)
                descriptions.append({"fator": factor, "grupo": group, "metrica": metric, "unidade": unit,
                                     **_summary(values)})
                if len(values) >= 2:
                    samples[str(group)] = values
            n = sum(map(len, samples.values()))
            if len(samples) < 2:
                h, p = np.nan, np.nan
            else:
                try:
                    h, p = kruskal(*samples.values())
                except ValueError as error:
                    if "All numbers are identical" not in str(error):
                        raise
                    h, p = 0.0, 1.0
            tests.append({"fator": factor, "metrica": metric, "n": n, "grupos": len(samples),
                          "h": h, "p_valor": p, "p_holm": np.nan,
                          "epsilon2": h / (n - 1) if n > 1 and pd.notna(h) else np.nan})
            for (first_name, first), (second_name, second) in combinations(samples.items(), 2):
                _, pair_p = mannwhitneyu(first, second, alternative="two-sided")
                delta = _cliffs_delta(first, second)
                pairwise.append({"fator": factor, "metrica": metric, "grupo_a": first_name,
                                 "grupo_b": second_name, "n_a": len(first), "n_b": len(second),
                                 "p_valor": pair_p, "p_holm": np.nan, "cliffs_delta": delta,
                                 "magnitude_romano": _magnitude(delta), "omnibus_significativo": False})
    tests_frame = pd.DataFrame(tests)
    valid = tests_frame.p_valor.notna()
    tests_frame.loc[valid, "p_holm"] = multipletests(tests_frame.loc[valid, "p_valor"], method="holm")[1]
    pair_frame = pd.DataFrame(pairwise)
    for (factor, metric), group in pair_frame.groupby(["fator", "metrica"]):
        index = group.index
        pair_frame.loc[index, "p_holm"] = multipletests(group.p_valor, method="holm")[1]
        omnibus = tests_frame.loc[(tests_frame.fator == factor) & (tests_frame.metrica == metric), "p_holm"].iloc[0]
        pair_frame.loc[index, "omnibus_significativo"] = bool(pd.notna(omnibus) and omnibus < 0.05)
    return pd.DataFrame(descriptions), tests_frame, pair_frame


def sensitivity(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios = {
        "C1": ("deployment_frequency_per_week", "lead_time_a_hours", "cfr_a"),
        "C2": ("deployment_frequency_with_prereleases_per_week", "lead_time_b_hours", "cfr_b"),
        "C3": ("deployment_frequency_tags_per_week", "lead_time_b_hours", "cfr_a"),
    }
    rows = []
    for record in dataset.itertuples(index=False):
        for scenario, (frequency, lead, failure) in scenarios.items():
            result = classify(_number(getattr(record, frequency)), _number(getattr(record, lead)),
                              _number(getattr(record, failure)), _number(record.recovery_median_hours))
            if scenario == "C1":
                expected = (record.df_points, record.lead_time_points, record.cfr_points,
                            record.recovery_points, record.dora_points, record.dora_category,
                            record.dora_metrics_used)
                actual = (result["frequency"], result["lead_time"], result["failure_rate"],
                          result["recovery"], result["overall"], result["category"],
                          result["metrics_used"])
                if any(not (pd.isna(want) and got is None) and want != got
                       for want, got in zip(expected, actual)):
                    raise ValueError(f"C1 difere do dataset.csv para {record.repository}")
            rows.append({"repository": record.repository, "cenario": scenario,
                         "frequencia_pontos": result["frequency"], "lead_time_pontos": result["lead_time"],
                         "cfr_pontos": result["failure_rate"], "recuperacao_pontos": result["recovery"],
                         "pontos_gerais": result["overall"], "categoria": result["category"],
                         "metricas_usadas": result["metrics_used"]})
    by_repo = pd.DataFrame(rows)
    comparisons = []
    for first, second in combinations(scenarios, 2):
        a = by_repo.loc[by_repo.cenario == first].set_index("repository")
        b = by_repo.loc[by_repo.cenario == second].set_index("repository")
        if set(a.index) != set(b.index):
            raise ValueError("Cenarios com repositorios diferentes")
        b = b.loc[a.index]
        valid = a.categoria.isin(CATEGORY_ORDER) & b.categoria.isin(CATEGORY_ORDER)
        changed = int((a.loc[valid, "categoria"] != b.loc[valid, "categoria"]).sum())
        n = int(valid.sum())
        kappa = cohen_kappa_score(a.loc[valid, "categoria"].map(CATEGORY_POINTS),
                                 b.loc[valid, "categoria"].map(CATEGORY_POINTS),
                                 labels=[1, 2, 3, 4], weights="linear") if n else np.nan
        comparisons.append({"cenario_a": first, "cenario_b": second, "n": n,
                            "mudaram": changed, "percentual_mudou": 100 * changed / n if n else np.nan,
                            "kappa_ponderado_linear": kappa})
    return by_repo, pd.DataFrame(comparisons)


def scenario_components(by_repo: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for first, second in combinations(("C1", "C2", "C3"), 2):
        a = by_repo.loc[by_repo.cenario == first].set_index("repository")
        b = by_repo.loc[by_repo.cenario == second].set_index("repository").loc[a.index]
        for component in ("frequencia_pontos", "lead_time_pontos", "cfr_pontos", "recuperacao_pontos"):
            valid = a[component].notna() & b[component].notna()
            n = int(valid.sum())
            changed = int((a.loc[valid, component] != b.loc[valid, component]).sum())
            rows.append({"cenario_a": first, "cenario_b": second, "metrica": component,
                         "n": n, "mudaram": changed, "percentual_mudou": 100 * changed / n if n else np.nan})
    return pd.DataFrame(rows)


def scenario_subgroups(by_repo: pd.DataFrame, dataset: pd.DataFrame, consensus: pd.DataFrame) -> pd.DataFrame:
    groups = _with_groups(dataset, consensus)[["repository", "grupo_linguagem", "grupo_estrelas",
                                           "grupo_contribuidores", "tipo_projeto"]]
    data = by_repo.merge(groups, on="repository", validate="many_to_one")
    rows = []
    for scenario, frame in data.groupby("cenario", sort=True):
        for factor, column in (("linguagem", "grupo_linguagem"), ("estrelas", "grupo_estrelas"),
                               ("contribuidores", "grupo_contribuidores"), ("tipo_projeto", "tipo_projeto")):
            samples = [pd.to_numeric(part.pontos_gerais, errors="raise").dropna().to_numpy(dtype=float)
                       for _, part in frame.dropna(subset=[column]).groupby(column)]
            samples = [sample for sample in samples if len(sample) >= 2]
            n = sum(map(len, samples))
            if len(samples) < 2:
                h, p = np.nan, np.nan
            else:
                try:
                    h, p = kruskal(*samples)
                except ValueError as error:
                    if "All numbers are identical" not in str(error):
                        raise
                    h, p = 0.0, 1.0
            rows.append({"cenario": scenario, "fator": factor, "n": n, "grupos": len(samples),
                         "h": h, "p_valor": p, "p_holm": np.nan,
                         "epsilon2": h / (n - 1) if n > 1 and pd.notna(h) else np.nan})
    result = pd.DataFrame(rows)
    valid = result.p_valor.notna()
    result.loc[valid, "p_holm"] = multipletests(result.loc[valid, "p_valor"], method="holm")[1]
    return result


def rework(releases: pd.DataFrame, repositories: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = releases.groupby("repository").corrective.agg(
        releases="size", corretivas=lambda values: int((values == "sim").sum()))
    counts = counts.reindex(repositories)
    if counts.isna().any().any():
        raise ValueError("Faltam releases para algum repositorio no calculo de rework")
    result = counts.reset_index().rename(columns={"index": "repository"})
    result["rework_rate"] = result.corretivas / result.releases
    summary = pd.DataFrame([{"metrica": "rework_rate", "unidade": "fracao",
                             **_summary(result.rework_rate), "releases": int(result.releases.sum()),
                             "corretivas": int(result.corretivas.sum())}])
    return result, summary


def run(dataset_path: Path = DEFAULT_DATASET, consensus_path: Path = DEFAULT_CONSENSUS,
        releases_path: Path = DEFAULT_RELEASES, output_dir: Path = DEFAULT_OUTPUT,
        figures_dir: Path = DEFAULT_FIGURES) -> dict[str, Path]:
    dataset, consensus, releases = load_inputs(dataset_path, consensus_path, releases_path)
    scenario_rows, comparisons = sensitivity(dataset)  # valida C1 antes de gravar qualquer saida
    descriptions, categories, censored = descriptive(dataset, releases)
    rho = correlations(dataset)
    subgroup_descriptions, tests, pairs = subgroups(dataset, consensus)
    component_changes = scenario_components(scenario_rows)
    scenario_groups = scenario_subgroups(scenario_rows, dataset, consensus)
    rework_rows, rework_summary = rework(releases, dataset.repository)
    frames = {
        "descritivas": descriptions, "c1_distribuicao": categories, "censura": censored,
        "correlacoes": rho, "subgrupos_descritivas": subgroup_descriptions,
        "subgrupos_testes": tests, "subgrupos_pares": pairs,
        "classificacoes_c1_c2_c3": scenario_rows, "sensibilidade_pares": comparisons,
        "sensibilidade_metricas": component_changes, "sensibilidade_subgrupos": scenario_groups,
        "rework_por_repositorio": rework_rows, "rework_resumo": rework_summary,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, frame in frames.items():
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False, float_format="%.8g")
        outputs[name] = path
    draw_correlations(dataset, figures_dir)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--consenso", type=Path, default=DEFAULT_CONSENSUS)
    parser.add_argument("--releases", type=Path, default=DEFAULT_RELEASES)
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--figuras", type=Path, default=DEFAULT_FIGURES)
    args = parser.parse_args()
    outputs = run(args.dataset, args.consenso, args.releases, args.saida, args.figuras)
    print(f"OK: {len(outputs)} CSVs em {args.saida}; graficos em {args.figuras}")


if __name__ == "__main__":
    main()
