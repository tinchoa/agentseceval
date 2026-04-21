#!/usr/bin/env python3
"""
Generate rigorous result tables from results/metrics_summary.csv.

Produces:
  results/table_baseline.md     — Per-model, per-scenario ASR + breach + leakage
                                   (baseline none-mode cohort, 95% Wilson CI)
  results/table_isolation.md    — Docker vs None: matched-cohort comparison
                                   with Fisher's exact p-value and Cohen's h
  results/table_fidelity.md     — Tool-call fidelity + attack layer breakdown
                                   per model

Usage:
    python analysis/generate_tables.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR  = PROJECT_ROOT / "results"
METRICS_CSV  = RESULTS_DIR / "metrics_summary.csv"


# ── Statistical helpers ────────────────────────────────────────────────────────

def wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score 95% CI. Returns (lo, hi) in [0, 1]."""
    if n == 0:
        return 0.0, 0.0
    z = scipy_stats.norm.ppf(1 - (1 - confidence) / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def fmt_pct(k: int, n: int) -> str:
    """'mean% [lo–hi]' with 95% Wilson CI, e.g. '87.5% [52–98]'."""
    if n == 0:
        return "—"
    mean = k / n * 100
    lo, hi = wilson_ci(k, n)
    return f"{mean:.0f}% [{lo*100:.0f}–{hi*100:.0f}]"


def fisher_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher's exact test p-value."""
    table = [[k1, n1 - k1], [k2, n2 - k2]]
    _, p = scipy_stats.fisher_exact(table, alternative="two-sided")
    return p


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for two proportions."""
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))


def fmt_p(p: float) -> str:
    if p < 0.001:
        return "<0.001"
    if p < 0.01:
        return f"{p:.3f}"
    return f"{p:.2f}"


def fmt_h(h: float) -> str:
    """Cohen's h with magnitude label."""
    ah = abs(h)
    if ah < 0.2:
        label = "negligible"
    elif ah < 0.5:
        label = "small"
    elif ah < 0.8:
        label = "medium"
    else:
        label = "large"
    return f"{h:+.2f} ({label})"


# ── Short scenario labels ──────────────────────────────────────────────────────

SHORT = {
    "A1_direct_01":             "A1 direct PI",
    "A2_indirect_01":           "A2 indirect PI",
    "B1_tool_abuse_01":         "B1 tool abuse",
    "B2_overprivilege_01":      "B2 overpriv.",
    "C1_exfiltration_01":       "C1 exfiltration",
    "D1_sandbox_escape_fs_01":  "D1 FS escape",
    "D2_sandbox_escape_net_01": "D2 net escape",
    "E1_memory_poison_01":      "E1 mem. poison",
}


# ── Table 1: Baseline per-scenario per-model ──────────────────────────────────

def table_baseline(df: pd.DataFrame) -> str:
    """
    For each (scenario, model): ASR, FS breach, Net breach, Leakage
    with 95% Wilson CI.  Uses all none-mode runs (maximum statistical power).
    """
    sub = df[df["isolation_mode"] == "none"].copy()
    models   = sorted(sub["model"].unique())
    scenarios = sorted(sub["scenario_id"].unique())
    # asr_execution = agent made flagged tool calls (primary metric)
    # asr_intent    = keyword match in text output (inflated, secondary)
    has_exec = "asr_execution" in sub.columns
    metrics  = [
        ("asr_execution" if has_exec else "asr_intent", "ASR (exec)"),
        ("asr_intent" if has_exec else "asr_intent",    "ASR (intent)"),
        ("fs_breach",  "FS breach"),
        ("net_breach", "Net breach"),
        ("leaked",     "Leakage"),
    ]
    if not has_exec:
        metrics = [("asr_intent", "ASR"), ("fs_breach", "FS breach"),
                   ("net_breach", "Net breach"), ("leaked", "Leakage")]

    lines = [
        "# Table 1 — Baseline Attack Metrics (isolation mode: none)",
        "",
        "Values: **rate% [95% Wilson CI]**.  Runs per cell shown in parentheses.",
        "",
        "> **ASR (exec)**: runs where the agent made ≥1 flagged tool call "
        "(execution-level attack attempt).",
        "> **ASR (intent)**: runs where attack keywords appeared in text output — "
        "inflated by model narration, not a reliable primary metric.",
        "",
    ]

    for model in models:
        msub = sub[sub["model"] == model]
        n_total = len(msub)
        header_cols = " | ".join(label for _, label in metrics)
        sep_cols    = " | ".join("---" for _ in metrics)
        lines += [
            f"## Model: {model}  (n = {n_total} total runs)",
            "",
            f"| Scenario | {header_cols} |",
            f"| --- | {sep_cols} |",
        ]
        for sid in scenarios:
            ssub = msub[msub["scenario_id"] == sid]
            n = len(ssub)
            if n == 0:
                empties = " | ".join("—" for _ in metrics)
                lines.append(f"| {SHORT.get(sid, sid)} | {empties} |")
                continue
            cells = [SHORT.get(sid, sid)]
            for col, _ in metrics:
                if col not in ssub.columns:
                    cells.append("—")
                    continue
                k = int(ssub[col].sum())
                cells.append(fmt_pct(k, n))
            lines.append("| " + " | ".join(cells) + f" |  *(n={n})*")

        # Row: overall
        cells = ["**Overall**"]
        for col, _ in metrics:
            if col not in msub.columns:
                cells.append("—")
                continue
            k = int(msub[col].sum())
            n = len(msub)
            cells.append(f"**{fmt_pct(k, n)}**")
        lines.append("| " + " | ".join(cells) + f" |  *(n={n_total})*")
        lines.append("")

    lines += [
        "> **FS/Net breach** = flagged tool call accessing sensitive path or",
        "> unauthorized domain.  **Leakage** = sensitive token/credential found in output.",
    ]
    return "\n".join(lines)


# ── Table 2: Isolation comparison (matched cohort) ────────────────────────────

def table_isolation(df: pd.DataFrame) -> str:
    """
    For each isolation experiment (milestone1, milestone2 …), compare each
    non-none mode against the matched none arm:
      - Rate (%) with 95% Wilson CI for both arms
      - Δ percentage points
      - Fisher's exact p-value (two-sided)
      - Cohen's h effect size
    Uses only the matched cohort (same experiment tag, same rep count).
    """
    if "experiment" not in df.columns:
        return "*(experiment column missing — re-run compute_metrics.py)*"

    iso_exps = []
    for exp, grp in df.groupby("experiment"):
        if grp["isolation_mode"].nunique() >= 2:
            iso_exps.append(exp)

    if not iso_exps:
        return (
            "# Table 2 — Isolation Mode Comparison\n\n"
            "*(No multi-mode experiments found yet — run milestone1/milestone2 first.)*"
        )

    has_attempt = "fs_attempt" in df.columns
    has_exec    = "asr_execution" in df.columns
    metrics = [
        ("asr_execution" if has_exec else "asr_intent", "ASR (execution)"),
        ("fs_attempt" if has_attempt else "fs_breach",  "FS attempt"),
        ("fs_breach",                                   "FS breach (success)"),
        ("net_breach",                                  "Net breach"),
        ("leaked",                                      "Leakage"),
    ]
    scenarios = sorted(df["scenario_id"].unique())

    lines = [
        "# Table 2 — Isolation Mode Comparison (matched cohort)",
        "",
        "**Cohort**: only runs from experiments that tested ≥2 isolation modes "
        "(same scenario set, same rep count per mode).",
        "**Statistics**: 95% Wilson CI, two-sided Fisher's exact test, Cohen's h.",
        "Effect size: |h| < 0.2 negligible, 0.2–0.5 small, 0.5–0.8 medium, > 0.8 large.",
        "",
        "**FS attempt**: agent tried to read a sensitive path (blocked or not).",
        "**FS breach (success)**: sensitive path accessed AND real data returned "
        "(isolation failed).",
        "",
    ]

    for exp in sorted(iso_exps):
        exp_df = df[df["experiment"] == exp]
        iso_modes = [m for m in sorted(exp_df["isolation_mode"].unique())
                     if m != "none"]
        ref_df = exp_df[exp_df["isolation_mode"] == "none"]
        model = exp_df["model"].mode()[0]
        n_ref_total = len(ref_df)

        lines += [
            f"## Experiment: {exp}  (model: {model})",
            "",
        ]

        for mode in iso_modes:
            iso_df  = exp_df[exp_df["isolation_mode"] == mode]
            n_iso_total = len(iso_df)

            lines += [
                f"### {mode} vs. none  "
                f"(n = {n_iso_total // len(scenarios)} per scenario each arm)",
                "",
                "| Scenario | Metric | none | " + mode + " | Δ (pp) | p-value | Cohen's h |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]

            for sid in scenarios:
                ref_s = ref_df[ref_df["scenario_id"] == sid]
                iso_s = iso_df[iso_df["scenario_id"] == sid]

                first = True
                for col, label in metrics:
                    k_ref = int(ref_s[col].sum()); n_ref = len(ref_s)
                    k_iso = int(iso_s[col].sum()); n_iso = len(iso_s)
                    if n_ref == 0 or n_iso == 0:
                        continue
                    p_ref = k_ref / n_ref
                    p_iso = k_iso / n_iso
                    delta = (p_iso - p_ref) * 100
                    p_val = fisher_p(k_ref, n_ref, k_iso, n_iso)
                    h     = cohens_h(p_iso, p_ref)

                    scenario_cell = SHORT.get(sid, sid) if first else ""
                    first = False
                    lines.append(
                        f"| {scenario_cell} | {label} "
                        f"| {fmt_pct(k_ref, n_ref)} "
                        f"| {fmt_pct(k_iso, n_iso)} "
                        f"| {delta:+.1f} "
                        f"| {fmt_p(p_val)} "
                        f"| {fmt_h(h)} |"
                    )

            # Overall summary row across all scenarios
            lines += ["", "**Overall (all scenarios pooled)**", ""]
            lines += [
                "| Metric | none | " + mode + " | Δ (pp) | p-value | Cohen's h |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for col, label in metrics:
                k_ref = int(ref_df[col].sum()); n_ref = len(ref_df)
                k_iso = int(iso_df[col].sum()); n_iso = len(iso_df)
                if n_ref == 0 or n_iso == 0:
                    continue
                p_ref = k_ref / n_ref
                p_iso = k_iso / n_iso
                delta = (p_iso - p_ref) * 100
                p_val = fisher_p(k_ref, n_ref, k_iso, n_iso)
                h     = cohens_h(p_iso, p_ref)
                sig   = " ✱" if p_val < 0.05 else ""
                lines.append(
                    f"| **{label}** "
                    f"| **{fmt_pct(k_ref, n_ref)}** "
                    f"| **{fmt_pct(k_iso, n_iso)}** "
                    f"| **{delta:+.1f}** "
                    f"| **{fmt_p(p_val)}**{sig} "
                    f"| **{fmt_h(h)}** |"
                )
            lines.append("")

    lines += [
        "> ✱ p < 0.05 (two-sided Fisher's exact test).",
        "> Δ > 0 means the isolation mode *increased* the metric vs. no isolation.",
    ]
    return "\n".join(lines)


# ── Table 3: Tool-call fidelity + attack layer ────────────────────────────────

def table_fidelity(df: pd.DataFrame) -> str:
    """
    Fidelity rate and attack-layer breakdown per model (none-mode baseline).
    """
    sub = df[df["isolation_mode"] == "none"].copy()
    models = sorted(sub["model"].unique())
    scenarios = sorted(sub["scenario_id"].unique())
    layers = ["execution", "intent", "none"]

    lines = [
        "# Table 3 — Tool-Call Fidelity and Attack Layer (baseline, none mode)",
        "",
        "**Fidelity**: fraction of runs where the model made ≥1 actual tool call "
        "(vs. narrating the attack in text only).",
        "**Attack layer**: *execution* = flagged tool call fired; "
        "*intent* = attack described in text, no tool call; *none* = no attack signal.",
        "",
        "| Scenario | " + " | ".join(
            f"{m}: fidelity | {m}: exec/intent/none"
            for m in models
        ) + " |",
        "| --- | " + " | ".join(["--- | ---"] * len(models)) + " |",
    ]

    for sid in scenarios:
        cells = [SHORT.get(sid, sid)]
        for model in models:
            msub = sub[(sub["model"] == model) & (sub["scenario_id"] == sid)]
            n = len(msub)
            if n == 0:
                cells += ["—", "—"]
                continue
            k_fid = int(msub["tool_call_fidelity"].sum())
            cells.append(fmt_pct(k_fid, n))
            layer_counts = "/".join(
                str(int((msub["attack_layer"] == l).sum())) for l in layers
            )
            cells.append(layer_counts)
        lines.append("| " + " | ".join(cells) + " |")

    # Overall row
    cells = ["**Overall**"]
    for model in models:
        msub = sub[sub["model"] == model]
        n = len(msub)
        k_fid = int(msub["tool_call_fidelity"].sum())
        cells.append(f"**{fmt_pct(k_fid, n)}**")
        layer_counts = "/".join(
            str(int((msub["attack_layer"] == l).sum())) for l in layers
        )
        cells.append(f"**{layer_counts}**")
    lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines += [
        "> **Interpretation**: Low fidelity (high intent, low execution) means the model",
        "> narrates attacks but does not execute them via tool calls — such attacks are",
        "> not containable by OS-level isolation and require prompt-level mitigations.",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not METRICS_CSV.exists():
        print(f"ERROR: {METRICS_CSV} not found. Run analysis/compute_metrics.py first.")
        sys.exit(1)

    df = pd.read_csv(METRICS_CSV)
    df = df[df["model"] != "unknown"].copy()

    tables = [
        ("table_baseline.md",   table_baseline(df)),
        ("table_isolation.md",  table_isolation(df)),
        ("table_fidelity.md",   table_fidelity(df)),
    ]

    for fname, content in tables:
        path = RESULTS_DIR / fname
        path.write_text(content)
        print(f"Written: {path}")


if __name__ == "__main__":
    main()
