#!/usr/bin/env python3
"""
Generate publication-quality figures from results/metrics_summary.csv.
All figures follow IEEE Transactions/Conference style (see analysis/ieee_style.py).

Figures produced in results/figures/:
  fig1_asr_forest.png     — ASR per scenario, 95% Wilson CI, one panel per model
                            (double-column)
  fig2_attack_layer.png   — Execution / intent / none stacked bar per scenario
                            (double-column)
  fig3_fidelity.png       — Tool-call fidelity rate per scenario × model
                            (double-column)
  fig4_asr_heatmap.png    — ASR heatmap, scenario × model, annotated with CI
                            (single-column)
  fig5_breach_rates.png   — FS + net breach rates with 95% CI (llama3.2)
                            (double-column)
  fig6_leakage.png        — Sensitive data leakage rate per scenario × model
                            (double-column)

Usage:
    python analysis/generate_figures.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# IEEE style
sys.path.insert(0, str(Path(__file__).parent))
from ieee_style import apply_ieee_style, SINGLE_COL, DOUBLE_COL, DOUBLE_COL_H

apply_ieee_style()

PROJECT_ROOT = Path(__file__).parent.parent
METRICS_CSV = PROJECT_ROOT / "results" / "metrics_summary.csv"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"

# ── Colour palette (accessible, print-friendly) ──────────────────────────────
MODEL_COLORS = {
    "llama3.2":  "#1f77b4",   # muted blue  (Meta)
    "mistral":   "#d62728",   # muted red   (Mistral AI)
    "qwen2.5":   "#2ca02c",   # muted green (Alibaba)
    "qwen3":     "#17becf",   # cyan        (Alibaba)
    "phi4-mini": "#9467bd",   # purple      (Microsoft)
    "unknown":   "#7f7f7f",   # grey
}
LAYER_COLORS = {
    "execution": "#d62728",  # red
    "intent":    "#ff7f0e",  # orange
    "none":      "#2ca02c",  # green
}
HATCH = {
    "llama3.2":  "",
    "mistral":   "///",
    "qwen2.5":   "...",
    "qwen3":     "xxx",
    "phi4-mini": "+++",
}


# ── Statistical helpers ──────────────────────────────────────────────────────

def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval. Returns (lower, upper) in [0, 1]."""
    if n == 0:
        return 0.0, 0.0
    z = scipy_stats.norm.ppf(1 - (1 - confidence) / 2)
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def proportion_stats(series: pd.Series) -> tuple[float, float, float]:
    """Returns (mean_pct, ci_lo_pct, ci_hi_pct) for a binary 0/1 series."""
    n = len(series)
    k = int(round(series.sum()))
    mean = k / n if n > 0 else 0.0
    lo, hi = wilson_ci(k, n)
    mean_pct = mean * 100
    # Clamp: CI must contain the point estimate (float-safety)
    return mean_pct, min(mean_pct, lo * 100), max(mean_pct, hi * 100)


def err_bars(mean: float, lo: float, hi: float) -> tuple[float, float]:
    """Convert (mean, ci_lo, ci_hi) to (lower_err, upper_err) ≥ 0."""
    return max(0.0, mean - lo), max(0.0, hi - mean)


# ── Shared axis helpers ───────────────────────────────────────────────────────

def label_axes(ax, xlabel: str = "", ylabel: str = "") -> None:
    """Apply axis labels; titles are placed in the figure caption, not on axes."""
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def percent_yticks(ax) -> None:
    ax.set_ylim(0, 108)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])


def percent_xticks(ax) -> None:
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])


# ── Figure 1: ASR forest plot ─────────────────────────────────────────────────

def fig1_asr_forest(df: pd.DataFrame) -> None:
    """Horizontal forest plot — ASR per scenario with 95% Wilson CI."""
    models = sorted(df["model"].unique())
    scenarios = sorted(df["scenario_id"].unique())
    n_sc = len(scenarios)

    # One panel per model, side-by-side — double column total
    panel_w = DOUBLE_COL / len(models)
    fig_h = max(2.5, n_sc * 0.38 + 0.6)
    fig, axes = plt.subplots(1, len(models), figsize=(DOUBLE_COL, fig_h),
                             sharey=True, constrained_layout=True)
    if len(models) == 1:
        axes = [axes]

    y = np.arange(n_sc)
    height = 0.5

    for ax, model in zip(axes, models):
        sub = df[df["model"] == model]
        color = MODEL_COLORS.get(model, "#7f7f7f")
        hatch = HATCH.get(model, "")

        asr_col = "asr_execution" if "asr_execution" in sub.columns else "asr_intent"
        means, lo_errs, hi_errs, ns = [], [], [], []
        for sid in scenarios:
            s = sub[sub["scenario_id"] == sid][asr_col]
            mean, lo, hi = proportion_stats(s)
            le, he = err_bars(mean, lo, hi)
            means.append(mean)
            lo_errs.append(le)
            hi_errs.append(he)
            ns.append(len(s))

        ax.barh(y, means, xerr=[lo_errs, hi_errs], height=height,
                color=color, hatch=hatch, alpha=0.80,
                error_kw={"elinewidth": 0.8, "ecolor": "black"})
        ax.axvline(50, color="grey", linestyle=":", linewidth=0.7)

        percent_xticks(ax)
        label_axes(ax, xlabel="ASR — execution level (%)")
        ax.set_title(model, pad=4)

        # N annotation
        for i, (m, he, n) in enumerate(zip(means, hi_errs, ns)):
            ax.text(min(m + he + 2, 104), i, f"n={n}",
                    va="center", fontsize=7, color="#444444")

        if ax is axes[0]:
            ax.set_yticks(y)
            ax.set_yticklabels(scenarios)
        else:
            ax.tick_params(labelleft=False)

    _save(fig, "fig1_asr_forest.png")


# ── Figure 2: Attack layer stacked bar ───────────────────────────────────────

def fig2_attack_layer(df: pd.DataFrame) -> None:
    """Stacked bar: execution / intent / none breakdown per scenario × model."""
    models = sorted(df["model"].unique())
    scenarios = sorted(df["scenario_id"].unique())
    layers = ["execution", "intent", "none"]

    fig, axes = plt.subplots(1, len(models), figsize=(DOUBLE_COL, DOUBLE_COL_H),
                             sharey=True, constrained_layout=True)
    if len(models) == 1:
        axes = [axes]

    for ax, model in zip(axes, models):
        sub = df[df["model"] == model]
        bottoms = np.zeros(len(scenarios))
        x = np.arange(len(scenarios))

        for layer in layers:
            vals = np.array([
                (sub[sub["scenario_id"] == sid]["attack_layer"] == layer).mean() * 100
                for sid in scenarios
            ])
            ax.bar(x, vals, bottom=bottoms, color=LAYER_COLORS[layer],
                   label=layer, width=0.6, alpha=0.88)
            bottoms += vals

        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=45, ha="right")
        percent_yticks(ax)
        label_axes(ax, ylabel="% of runs" if ax is axes[0] else "")
        ax.set_title(model, pad=4)

    # Shared legend on last panel
    patches = [mpatches.Patch(color=LAYER_COLORS[l], label=l) for l in layers]
    axes[-1].legend(handles=patches, loc="upper right",
                    framealpha=0.9, edgecolor="none")
    _save(fig, "fig2_attack_layer.png")


# ── Figure 3: Tool-call fidelity ─────────────────────────────────────────────

def fig3_fidelity(df: pd.DataFrame) -> None:
    """Grouped bar: tool-call fidelity rate per scenario × model with 95% CI."""
    models = sorted(df["model"].unique())
    scenarios = sorted(df["scenario_id"].unique())
    x = np.arange(len(scenarios))
    n_m = len(models)
    width = 0.7 / n_m

    fig, ax = plt.subplots(figsize=(DOUBLE_COL, DOUBLE_COL_H), constrained_layout=True)

    for i, model in enumerate(models):
        sub = df[df["model"] == model]
        means, lo_errs, hi_errs = [], [], []
        for sid in scenarios:
            s = sub[sub["scenario_id"] == sid]["tool_call_fidelity"]
            mean, lo, hi = proportion_stats(s)
            le, he = err_bars(mean, lo, hi)
            means.append(mean)
            lo_errs.append(le)
            hi_errs.append(he)

        offset = (i - (n_m - 1) / 2) * width
        ax.bar(x + offset, means, width * 0.92,
               yerr=[lo_errs, hi_errs],
               color=MODEL_COLORS.get(model, "#7f7f7f"),
               hatch=HATCH.get(model, ""),
               label=model, alpha=0.82,
               error_kw={"elinewidth": 0.8, "ecolor": "black"})

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    percent_yticks(ax)
    label_axes(ax, ylabel="Fidelity (% runs with ≥1 tool call)")
    ax.legend(framealpha=0.9, edgecolor="none")
    _save(fig, "fig3_fidelity.png")


# ── Figure 4: ASR heatmap ─────────────────────────────────────────────────────

def fig4_asr_heatmap(df: pd.DataFrame) -> None:
    """Heatmap — scenario × model, annotated with mean and ±half-CI width."""
    models = sorted(df["model"].unique())
    scenarios = sorted(df["scenario_id"].unique())

    matrix = np.zeros((len(scenarios), len(models)))
    ci_half = np.zeros_like(matrix)

    asr_col = "asr_execution" if "asr_execution" in df.columns else "asr_intent"
    for j, model in enumerate(models):
        sub = df[df["model"] == model]
        for i, sid in enumerate(scenarios):
            mean, lo, hi = proportion_stats(sub[sub["scenario_id"] == sid][asr_col])
            matrix[i, j] = mean
            ci_half[i, j] = (hi - lo) / 2

    # Single column — tall enough for all rows
    fig_h = max(2.5, len(scenarios) * 0.42 + 0.6)
    fig, ax = plt.subplots(figsize=(SINGLE_COL, fig_h), constrained_layout=True)

    im = ax.imshow(matrix, cmap="RdYlGn_r", vmin=0, vmax=100, aspect="auto")

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models)
    ax.set_yticks(range(len(scenarios)))
    ax.set_yticklabels(scenarios)

    for i in range(len(scenarios)):
        for j in range(len(models)):
            val, ci = matrix[i, j], ci_half[i, j]
            txt = f"{val:.0f}%\n$\\pm${ci:.0f}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7,
                    color="white" if val > 55 else "black")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("ASR (%)", fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    _save(fig, "fig4_asr_heatmap.png")


# ── Figure 5: Breach rates (llama3.2 baseline, none mode only) ───────────────

def fig5_breach_rates(df_baseline: pd.DataFrame) -> None:
    """Grouped bar — FS and net breach rates, llama3.2 baseline (none mode only)."""
    model = "llama3.2"
    sub = df_baseline[(df_baseline["model"] == model) &
                      (df_baseline["isolation_mode"] == "none")]
    if sub.empty:
        print(f"WARNING: no baseline none data for model={model}, skipping fig5",
              file=sys.stderr)
        return

    scenarios = sorted(sub["scenario_id"].unique())
    x = np.arange(len(scenarios))
    width = 0.35

    def _stat(col: str) -> tuple[list, list, list]:
        means, lo_errs, hi_errs = [], [], []
        for sid in scenarios:
            mean, lo, hi = proportion_stats(sub[sub["scenario_id"] == sid][col])
            le, he = err_bars(mean, lo, hi)
            means.append(mean)
            lo_errs.append(le)
            hi_errs.append(he)
        return means, lo_errs, hi_errs

    fs_m, fs_lo, fs_hi    = _stat("fs_breach")
    net_m, net_lo, net_hi = _stat("net_breach")

    fig, ax = plt.subplots(figsize=(DOUBLE_COL, DOUBLE_COL_H), constrained_layout=True)

    ax.bar(x - width / 2, fs_m,  width, yerr=[fs_lo, fs_hi],
           color="#1f77b4", hatch="",    label="FS breach",  alpha=0.82,
           error_kw={"elinewidth": 0.8, "ecolor": "black"})
    ax.bar(x + width / 2, net_m, width, yerr=[net_lo, net_hi],
           color="#d62728", hatch="///", label="Net breach", alpha=0.82,
           error_kw={"elinewidth": 0.8, "ecolor": "black"})

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    percent_yticks(ax)
    label_axes(ax, ylabel="Breach rate (%)")
    ax.legend(framealpha=0.9, edgecolor="none")
    _save(fig, "fig5_breach_rates.png")


# ── Figure 6: Leakage rate ────────────────────────────────────────────────────

def fig6_leakage(df: pd.DataFrame) -> None:
    """Grouped bar — sensitive data leakage rate per scenario × model with CI."""
    models = sorted(df["model"].unique())
    scenarios = sorted(df["scenario_id"].unique())
    x = np.arange(len(scenarios))
    n_m = len(models)
    width = 0.7 / n_m

    fig, ax = plt.subplots(figsize=(DOUBLE_COL, DOUBLE_COL_H), constrained_layout=True)

    for i, model in enumerate(models):
        sub = df[df["model"] == model]
        means, lo_errs, hi_errs = [], [], []
        for sid in scenarios:
            mean, lo, hi = proportion_stats(sub[sub["scenario_id"] == sid]["leaked"])
            le, he = err_bars(mean, lo, hi)
            means.append(mean)
            lo_errs.append(le)
            hi_errs.append(he)

        offset = (i - (n_m - 1) / 2) * width
        ax.bar(x + offset, means, width * 0.92,
               yerr=[lo_errs, hi_errs],
               color=MODEL_COLORS.get(model, "#7f7f7f"),
               hatch=HATCH.get(model, ""),
               label=model, alpha=0.82,
               error_kw={"elinewidth": 0.8, "ecolor": "black"})

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    percent_yticks(ax)
    label_axes(ax, ylabel="Leakage rate (%)")
    ax.legend(framealpha=0.9, edgecolor="none")
    _save(fig, "fig6_leakage.png")


# ── Figure 7: Isolation difference forest plot (matched cohort) ───────────────
#
# Design rationale: when Docker vs None rates are nearly identical the grouped-
# bar format produces unreadable overlapping bars.  A difference forest plot
# directly asks "did isolation change the metric?" — each row is one scenario,
# x-axis is Δ% (isolation − none), vertical line at 0 = no effect.  CIs that
# span 0 confirm no significant change; any bar that clears 0 would flag a
# real reduction (or increase).

ISOLATION_COLORS = {
    "docker": "#1f77b4",   # blue
    "gvisor": "#2ca02c",   # green
    "wasm":   "#ff7f0e",   # orange
}

# Short, readable scenario labels
_SHORT_LABELS = {
    "A1_direct_01":          "A1 direct PI",
    "A2_indirect_01":        "A2 indirect PI",
    "B1_tool_abuse_01":      "B1 tool abuse",
    "B2_overprivilege_01":   "B2 overpriv.",
    "C1_exfiltration_01":    "C1 exfiltration",
    "D1_sandbox_escape_fs_01":  "D1 FS escape",
    "D2_sandbox_escape_net_01": "D2 net escape",
    "E1_memory_poison_01":   "E1 mem. poison",
}


def _diff_ci(
    k_iso: int, n_iso: int,
    k_ref: int, n_ref: int,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """
    Δ = p_iso - p_ref in percentage points, with a conservative 95% CI
    obtained by adding the two Wilson half-widths in quadrature.
    Returns (delta_pct, lo_pct, hi_pct).
    """
    p_iso = k_iso / n_iso if n_iso else 0.0
    p_ref = k_ref / n_ref if n_ref else 0.0
    _, hi_iso = wilson_ci(k_iso, n_iso, confidence)
    lo_iso, _  = wilson_ci(k_iso, n_iso, confidence)
    _, hi_ref  = wilson_ci(k_ref, n_ref, confidence)
    lo_ref, _  = wilson_ci(k_ref, n_ref, confidence)
    half_iso = (hi_iso - lo_iso) / 2
    half_ref = (hi_ref - lo_ref) / 2
    margin = np.sqrt(half_iso ** 2 + half_ref ** 2) * 100
    delta = (p_iso - p_ref) * 100
    return delta, delta - margin, delta + margin


def fig7_isolation_comparison(df_isolation: pd.DataFrame) -> None:
    """
    Difference forest plot — Δ% (isolation mode − none) per scenario per metric.
    Each non-none mode gets one panel column; metrics are rows.
    Double-column figure, landscape.
    """
    iso_modes = [m for m in sorted(df_isolation["isolation_mode"].unique())
                 if m != "none"]
    if not iso_modes:
        print("WARNING: no non-none isolation modes found, skipping fig7",
              file=sys.stderr)
        return

    ref_df = df_isolation[df_isolation["isolation_mode"] == "none"]
    scenarios = sorted(df_isolation["scenario_id"].unique())
    short = [_SHORT_LABELS.get(s, s) for s in scenarios]
    n_sc = len(scenarios)
    y = np.arange(n_sc)

    asr_col = "asr_execution" if "asr_execution" in df_isolation.columns else "asr_intent"
    metrics = [
        (asr_col,      "ΔASR execution (pp)"),
        ("fs_breach",  "ΔFS breach (pp)"),
        ("net_breach", "ΔNet breach (pp)"),
        ("leaked",     "ΔLeakage (pp)"),
    ]

    n_cols = len(iso_modes)
    n_rows = len(metrics)
    # Height: enough rows to read scenario labels clearly
    fig_h = max(3.5, n_sc * 0.38 + 1.0)
    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(DOUBLE_COL, fig_h * n_rows / 2),
        sharex=False, sharey="row",
        constrained_layout=True,
        squeeze=False,
    )

    for row, (col, xlabel) in enumerate(metrics):
        for c, mode in enumerate(iso_modes):
            ax = axes[row][c]
            iso_sub = df_isolation[df_isolation["isolation_mode"] == mode]
            color = ISOLATION_COLORS.get(mode, "#888888")

            deltas, lo_errs, hi_errs = [], [], []
            for sid in scenarios:
                s_iso = iso_sub[iso_sub["scenario_id"] == sid][col]
                s_ref = ref_df[ref_df["scenario_id"] == sid][col]
                k_iso, n_iso = int(s_iso.sum()), len(s_iso)
                k_ref, n_ref = int(s_ref.sum()), len(s_ref)
                d, lo, hi = _diff_ci(k_iso, n_iso, k_ref, n_ref)
                deltas.append(d)
                lo_errs.append(max(0.0, d - lo))
                hi_errs.append(max(0.0, hi - d))

            # Horizontal bars (forest plot orientation)
            bar_colors = [
                color if d < 0 else "#d62728"   # blue=reduction, red=increase
                for d in deltas
            ]
            ax.barh(y, deltas, xerr=[lo_errs, hi_errs],
                    color=bar_colors, alpha=0.80, height=0.55,
                    error_kw={"elinewidth": 0.8, "ecolor": "black",
                              "capsize": 3})

            # Reference line at 0
            ax.axvline(0, color="black", linewidth=0.9, linestyle="--")

            # Symmetric x-axis centred on 0
            max_extent = max(
                max(abs(d) + he for d, he in zip(deltas, hi_errs)),
                10.0   # minimum range ±10 pp so axis doesn't collapse
            )
            ax.set_xlim(-max_extent * 1.25, max_extent * 1.25)

            # Y-axis: scenario labels only on leftmost column
            ax.set_yticks(y)
            if c == 0:
                ax.set_yticklabels(short, fontsize=8)
            else:
                ax.set_yticklabels([])

            ax.set_xlabel(xlabel, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(axis="x", labelsize=8)

            # Column header (mode name) on top row only
            if row == 0:
                n_mode = len(iso_sub)
                n_ref_tot = len(ref_df)
                ax.set_title(
                    f"{mode}  (n={n_mode // n_sc} vs {n_ref_tot // n_sc} per scenario)",
                    fontsize=9, pad=4,
                )

    # Shared legend: blue=reduction, red=increase
    legend_patches = [
        mpatches.Patch(color=ISOLATION_COLORS.get(iso_modes[0], "#1f77b4"),
                       label="reduction vs. none"),
        mpatches.Patch(color="#d62728", label="increase vs. none"),
    ]
    axes[0][-1].legend(handles=legend_patches, loc="upper right",
                       fontsize=8, framealpha=0.9, edgecolor="none")

    for mode in iso_modes:
        n = len(df_isolation[df_isolation["isolation_mode"] == mode])
        print(f"  fig7: {mode} vs none — {n // n_sc} reps per scenario × {n_sc} scenarios")

    _save(fig, "fig7_isolation_comparison.png")


# ── Save helper ───────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, filename: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / filename
    fig.savefig(out)   # dpi and bbox handled by rcParams
    plt.close(fig)
    print(f"Saved: {out.relative_to(PROJECT_ROOT)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not METRICS_CSV.exists():
        print(f"ERROR: {METRICS_CSV} not found. Run analysis/compute_metrics.py first.")
        sys.exit(1)

    df = pd.read_csv(METRICS_CSV)
    df = df[df["model"] != "unknown"].copy()

    if df.empty:
        print("No usable data after filtering. Exiting.")
        sys.exit(1)

    print(f"Loaded {len(df)} rows — models: {sorted(df['model'].unique())}")

    # ── Cohort definitions ───────────────────────────────────────────────────
    #
    # df_baseline : all none-mode runs — maximum power for per-model comparisons
    #               (figs 1–4, 6)
    #
    # df_isolation: ONLY the matched milestone experiment that ran both none and
    #               docker (or gvisor) with the SAME rep count.  This is the only
    #               cohort where a none vs docker comparison is statistically
    #               valid. Using all none runs (3× more) would bias effect sizes.
    #
    df_baseline  = df[df["isolation_mode"] == "none"].copy()

    # Collect all experiments that tested ≥2 isolation modes
    isolation_experiments = []
    if "experiment" in df.columns:
        for exp, grp in df.groupby("experiment"):
            if grp["isolation_mode"].nunique() >= 2:
                isolation_experiments.append(exp)
    df_isolation = df[df["experiment"].isin(isolation_experiments)].copy() \
        if isolation_experiments else pd.DataFrame()

    # Report cohort sizes
    print(f"  Baseline cohort (none only):  {len(df_baseline)} rows")
    if not df_isolation.empty:
        by_mode = df_isolation.groupby("isolation_mode").size()
        print(f"  Isolation cohort: {dict(by_mode)}")
    else:
        print("  Isolation cohort: empty (no multi-mode experiments found)")

    # ── Figures ──────────────────────────────────────────────────────────────
    fig1_asr_forest(df_baseline)
    fig2_attack_layer(df_baseline)
    fig3_fidelity(df_baseline)
    fig4_asr_heatmap(df_baseline)
    fig5_breach_rates(df_baseline)
    fig6_leakage(df_baseline)

    if not df_isolation.empty:
        fig7_isolation_comparison(df_isolation)
    else:
        print("Skipping fig7 — no matched isolation-mode experiments yet.")

    print(f"\nAll figures → {FIGURES_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
