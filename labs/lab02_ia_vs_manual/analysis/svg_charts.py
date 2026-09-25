from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd

from labs.lab02_ia_vs_manual.analysis.data import KATA_CODES, KATAS
from labs.lab02_ia_vs_manual.analysis.stats import TREATMENTS

LABELS = {"manual": "Manual", "ai_assisted": "Com IA"}
CLS = {"manual": "s-m", "ai_assisted": "s-a"}
W, H = 560, 320
ML, MR, MT, MB = 54, 16, 14, 46
TIME_TICKS = [10, 30, 60, 180, 600, 2100]


def _time_label(seconds: float) -> str:
    return f"{int(seconds)} s" if seconds < 60 else f"{int(seconds // 60)} min"


def _log_scale(r0: float, r1: float):
    base = _scale(math.log10(TIME_TICKS[0] * 0.8), math.log10(TIME_TICKS[-1] * 1.5), r0, r1)
    return lambda v: base(math.log10(v))


def _ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    span = (hi - lo) or 1.0
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    first = math.floor(lo / step) * step
    ticks = [first]
    while ticks[-1] < hi - step * 1e-9:
        ticks.append(round(ticks[-1] + step, 10))
    return ticks


def _fmt(value: float, digits: int = 1) -> str:
    text = f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return text.rstrip("0").rstrip(",") if "," in text else text


def _svg(inner: str, height: int = H) -> str:
    return f'<svg class="chart" viewBox="0 0 {W} {height}" role="img" preserveAspectRatio="xMidYMid meet">{inner}</svg>'


def _y_axis(ticks: list[float], ys, ylabel: str, digits: int = 1, height: int = H, fmt=None) -> str:
    out = []
    for tick in ticks:
        y = ys(tick)
        label = fmt(tick) if fmt else _fmt(tick, digits)
        out.append(f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="tx" x="{ML - 8}" y="{y + 4:.1f}" text-anchor="end">{label}</text>')
    mid = (MT + height - MB) / 2
    out.append(f'<text class="tx" transform="rotate(-90 13 {mid:.0f})" x="13" y="{mid:.0f}" text-anchor="middle">{html.escape(ylabel)}</text>')
    return "".join(out)


def _domain(values: list[float], extra: list[float] | None = None) -> list[float]:
    pool = values + (extra or [])
    lo, hi = min(pool), max(pool)
    if lo == hi:
        lo, hi = (lo, hi + 1) if lo >= 0 else (lo - 1, hi)
    pad = (hi - lo) * 0.08
    floor = max(lo - pad, 0.0) if lo >= 0 else lo - pad
    return _ticks(floor, hi + pad)


def _scale(d0: float, d1: float, r0: float, r1: float):
    return lambda v: r0 + (v - d0) / ((d1 - d0) or 1) * (r1 - r0)


def _point(cx: float, cy: float, cls: str, tip: str, censored: bool = False) -> str:
    extra = " cens" if censored else ""
    return f'<circle class="pt {cls}{extra}" cx="{cx:.1f}" cy="{cy:.1f}" r="5"><title>{html.escape(tip)}</title></circle>'


def box_strip(df: pd.DataFrame, column: str, ylabel: str, digits: int = 1, ref: float | None = None,
              ref_label: str = "", mark_censored: bool = False, log: bool = False, unit: str = "") -> str:
    """Boxplot (mediana/IQR, bigodes 1,5xIQR) com todos os trials como pontos."""
    groups = {t: df[df["treatment"] == t] for t in TREATMENTS}
    values = [float(v) for g in groups.values() for v in g[column].dropna()]
    if not values:
        return "<p class='note'>Sem dados.</p>"
    if log:
        ticks, ys = TIME_TICKS, _log_scale(H - MB, MT)
    else:
        ticks = _domain(values, [ref] if ref is not None else None)
        ys = _scale(ticks[0], ticks[-1], H - MB, MT)
    plot_w = W - ML - MR
    out = [_y_axis(ticks, ys, ylabel, digits, fmt=_time_label if log else None)]
    if ref is not None:
        out.append(f'<line class="ref" x1="{ML}" x2="{W - MR}" y1="{ys(ref):.1f}" y2="{ys(ref):.1f}"/>'
                   f'<text class="tx bad" x="{W - MR}" y="{ys(ref) - 5:.1f}" text-anchor="end">{html.escape(ref_label)}</text>')
    for i, treatment in enumerate(TREATMENTS):
        cx = ML + plot_w * (i + 0.5) / len(TREATMENTS)
        rows = groups[treatment].dropna(subset=[column])
        v = rows[column].to_numpy(dtype=float)
        bw = plot_w / len(TREATMENTS) * 0.3
        out.append(f'<text class="tx ink" x="{cx:.1f}" y="{H - 22}" text-anchor="middle">{LABELS[treatment]}</text>'
                   f'<text class="tx" x="{cx:.1f}" y="{H - 8}" text-anchor="middle">n={len(v)}</text>')
        if not v.size:
            continue
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        iqr = q3 - q1
        low, high = v[v >= q1 - 1.5 * iqr].min(), v[v <= q3 + 1.5 * iqr].max()
        out.append(f'<line class="wh" x1="{cx:.1f}" x2="{cx:.1f}" y1="{ys(low):.1f}" y2="{ys(high):.1f}"/>'
                   f'<rect class="bx" x="{cx - bw:.1f}" y="{ys(q3):.1f}" width="{2 * bw:.1f}" height="{max(ys(q1) - ys(q3), 1):.1f}" rx="3">'
                   f'<title>{LABELS[treatment]}: mediana {_fmt(med, digits)} (Q1 {_fmt(q1, digits)} - Q3 {_fmt(q3, digits)})</title></rect>'
                   f'<line class="md" x1="{cx - bw:.1f}" x2="{cx + bw:.1f}" y1="{ys(med):.1f}" y2="{ys(med):.1f}"/>'
                   f'<text class="tx ink" x="{cx + bw + 6:.1f}" y="{ys(med) + 4:.1f}">{_fmt(med, digits)}{unit}</text>')
        for k, row in enumerate(rows.itertuples()):
            dx = ((k * 0.618) % 1 - 0.5) * bw * 1.3
            value = float(getattr(row, column))
            out.append(_point(cx + dx, ys(value), CLS[treatment], f"{row.trial_id}: {_fmt(value, digits)}{unit}", mark_censored and bool(row.censored)))
    return _svg("".join(out))


def kata_dots(df: pd.DataFrame) -> str:
    """Tempo por kata (escala log): comparar dentro do mesmo kata controla a variacao de dificuldade."""
    if df.empty:
        return "<p class='note'>Sem dados.</p>"
    ys = _log_scale(H - MB, MT)
    slot = (W - ML - MR) / len(KATAS)
    out = [_y_axis(TIME_TICKS, ys, "Tempo (escala log)", fmt=_time_label),
           f'<line class="ref" x1="{ML}" x2="{W - MR}" y1="{ys(2100):.1f}" y2="{ys(2100):.1f}"/>']
    for i, kata in enumerate(KATAS):
        cx = ML + slot * (i + 0.5)
        out.append(f'<text class="tx ink" x="{cx:.1f}" y="{H - 24}" text-anchor="middle">{KATA_CODES[kata]}</text>'
                   f'<text class="tx" x="{cx:.1f}" y="{H - 9}" text-anchor="middle">{html.escape(kata.split("_")[0])}</text>')
        for k, row in enumerate(df[df["kata"] == kata].itertuples()):
            dx = (-0.2 if row.treatment == "manual" else 0.2) * slot + ((k * 0.618) % 1 - 0.5) * 14
            out.append(_point(cx + dx, ys(max(row.time_to_green_seconds, 1)), CLS[row.treatment],
                              f"{row.trial_id}: {int(row.time_to_green_seconds)} s", bool(row.censored)))
    return _svg("".join(out))


def check_timeline(summary: pd.DataFrame, checks: pd.DataFrame) -> str:
    """Linha do tempo dos checks por trial (escala log): falhas em vermelho, passou em verde, losango = fim."""
    if summary.empty:
        return "<p class='note'>Sem registro de checks.</p>"
    left = 150
    xs_base = _scale(math.log10(TIME_TICKS[0] * 0.8), math.log10(TIME_TICKS[-1] * 1.5), left, W - MR)
    xs = lambda v: xs_base(math.log10(max(v, 1)))
    step = (H - MT - MB) / len(summary)
    out = []
    for tick in TIME_TICKS:
        out.append(f'<line class="grid" x1="{xs(tick):.1f}" x2="{xs(tick):.1f}" y1="{MT}" y2="{H - MB}"/>'
                   f'<text class="tx" x="{xs(tick):.1f}" y="{H - MB + 16}" text-anchor="middle">{_time_label(tick)}</text>')
    for i, row in enumerate(summary.itertuples()):
        y = MT + step * (i + 0.5)
        out.append(f'<text class="tx ink" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{row.kata_code} {html.escape(row.kata.split("_")[0])}</text>'
                   f'<text class="tx" x="{left - 10}" y="{y + 17:.1f}" text-anchor="end">{row.check_runs} check(s), {row.failed_checks} com falha</text>')
        for ev in checks[checks["trial_id"] == row.trial_id].itertuples():
            cls = "ck ok" if ev.success else "ck bad"
            state = "passou" if ev.success else "falhou"
            out.append(f'<circle class="{cls}" cx="{xs(ev.elapsed_seconds):.1f}" cy="{y:.1f}" r="6"><title>{html.escape(row.trial_id)}: check aos {ev.elapsed_seconds} s ({state}; {ev.tests_passed} passaram, {ev.tests_failed} falharam)</title></circle>')
        out.append(f'<rect class="{CLS[row.treatment]}" x="{xs(row.time_to_green_seconds) - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" transform="rotate(45 {xs(row.time_to_green_seconds):.1f} {y:.1f})"><title>{html.escape(row.trial_id)}: verde aos {int(row.time_to_green_seconds)} s</title></rect>')
    return _svg("".join(out))


def green_bars(df: pd.DataFrame) -> str:
    ys = _scale(0, 1.14, H - MB, MT)
    plot_w = W - ML - MR
    out = [_y_axis([0, 0.25, 0.5, 0.75, 1.0], ys, "Trials verdes", fmt=lambda t: f"{t:.0%}")]
    for i, treatment in enumerate(TREATMENTS):
        rows = df[df["treatment"] == treatment]
        green = int((rows["tests_failed"] == 0).sum())
        rate = green / len(rows) if len(rows) else 0
        cx = ML + plot_w * (i + 0.5) / len(TREATMENTS)
        bw = plot_w / len(TREATMENTS) * 0.28
        out.append(f'<rect class="{CLS[treatment]}" x="{cx - bw:.1f}" y="{ys(rate):.1f}" width="{2 * bw:.1f}" height="{max(ys(0) - ys(rate), 0):.1f}" rx="4">'
                   f'<title>{LABELS[treatment]}: {green} de {len(rows)} trials com todos os testes passando</title></rect>'
                   f'<text class="tx ink big" x="{cx:.1f}" y="{ys(rate) - 8:.1f}" text-anchor="middle">{green}/{len(rows)}</text>'
                   f'<text class="tx ink" x="{cx:.1f}" y="{H - 22}" text-anchor="middle">{LABELS[treatment]}</text>'
                   f'<text class="tx" x="{cx:.1f}" y="{H - 8}" text-anchor="middle">{int(rows["tests_failed"].sum())} testes falhos</text>')
    return _svg("".join(out))


def scatter(df: pd.DataFrame, x: str, y: str, xlabel: str, ylabel: str) -> str:
    if df.empty:
        return "<p class='note'>Sem dados.</p>"
    xt, yt = _domain([float(v) for v in df[x]]), _domain([float(v) for v in df[y]])
    xs, ys = _scale(xt[0], xt[-1], ML, W - MR), _scale(yt[0], yt[-1], H - MB, MT)
    out = [_y_axis(yt, ys, ylabel, 1)]
    for tick in xt:
        out.append(f'<text class="tx" x="{xs(tick):.1f}" y="{H - 26}" text-anchor="middle">{_fmt(tick, 0)}</text>')
    out.append(f'<text class="tx" x="{(ML + W - MR) / 2:.0f}" y="{H - 8}" text-anchor="middle">{html.escape(xlabel)}</text>')
    for row in df.itertuples():
        out.append(_point(xs(getattr(row, x)), ys(getattr(row, y)), CLS[row.treatment],
                          f"{row.trial_id}: {xlabel} {_fmt(getattr(row, x), 0)}, {ylabel} {_fmt(getattr(row, y), 2)}"))
    return _svg("".join(out))


def _heat_color(value: float) -> str:
    """Azul (-1) -> branco (0) -> vermelho (+1)."""
    t = max(-1.0, min(1.0, value))
    base = (192, 57, 43) if t >= 0 else (42, 120, 214)
    mix = abs(t)
    r, g, b = (round(255 - (255 - c) * mix) for c in base)
    return f"rgb({r},{g},{b})"


def heatmap(corr: pd.DataFrame, labels: dict[str, str]) -> str:
    n = len(corr)
    left, top = 96, 20
    cell = min((W - left - 10) / n, 46)
    out = []
    for i, col in enumerate(corr.columns):
        name = html.escape(labels.get(col, col))
        out.append(f'<text class="tx ink" x="{left - 8}" y="{top + cell * (i + 0.5) + 4:.1f}" text-anchor="end">{name}</text>')
        out.append(f'<text class="tx" transform="rotate(-35 {left + cell * (i + 0.5):.1f} {top + cell * n + 14})" '
                   f'x="{left + cell * (i + 0.5):.1f}" y="{top + cell * n + 14}" text-anchor="end">{name}</text>')
        for j, other in enumerate(corr.columns):
            value = float(corr.iloc[i, j])
            out.append(f'<rect x="{left + cell * j:.1f}" y="{top + cell * i:.1f}" width="{cell - 2:.1f}" height="{cell - 2:.1f}" rx="3" '
                       f'fill="{_heat_color(value)}"><title>{html.escape(labels.get(col, col))} x {html.escape(labels.get(other, other))}: {value:.2f}</title></rect>'
                       f'<text class="hv" x="{left + cell * (j + 0.5) - 1:.1f}" y="{top + cell * (i + 0.5) + 4:.1f}" text-anchor="middle">{value:.2f}</text>')
    return _svg("".join(out), height=int(top + cell * n + 92))
