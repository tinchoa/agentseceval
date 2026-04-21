#!/usr/bin/env python3
"""
AgentSecEval end-to-end pipeline.

Runs every experiment config, then computes metrics, generates tables,
and generates figures — all in one command.

Usage:
    python pipeline.py                          # run all configs in default order
    python pipeline.py --configs baseline       # run only baseline (llama3.2)
    python pipeline.py --configs baseline mistral
    python pipeline.py --skip-experiments       # metrics + figures only (results already exist)
    python pipeline.py --skip-figures           # experiments + metrics + tables only
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.rule import Rule
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).parent
CONFIGS_DIR = PROJECT_ROOT / "agentseceval" / "experiments" / "configs"

# Ordered list of (alias, config_path) — run in this sequence
ALL_CONFIGS = [
    ("llama3.2 baseline (30 reps)",           CONFIGS_DIR / "baseline.yaml"),
    ("mistral baseline (10 reps)",             CONFIGS_DIR / "baseline_mistral.yaml"),
    ("qwen2.5 baseline (10 reps)",             CONFIGS_DIR / "baseline_qwen25.yaml"),
    ("qwen3 baseline (10 reps)",               CONFIGS_DIR / "baseline_qwen3.yaml"),
    ("qwen3 rerun timed-out scenarios",        CONFIGS_DIR / "baseline_qwen3_rerun.yaml"),
    ("phi4-mini baseline (10 reps)",           CONFIGS_DIR / "baseline_phi4mini.yaml"),
    ("milestone1 docker vs none (10 reps)",    CONFIGS_DIR / "milestone1.yaml"),
    ("milestone2 gvisor vs none (10 reps)",    CONFIGS_DIR / "milestone2_gvisor.yaml"),
]

ANALYSIS_SCRIPTS = [
    ("Compute metrics",    PROJECT_ROOT / "analysis" / "compute_metrics.py"),
    ("Generate tables",    PROJECT_ROOT / "analysis" / "generate_tables.py"),
    ("Generate figures",   PROJECT_ROOT / "analysis" / "generate_figures.py"),
    ("Build dataset",      PROJECT_ROOT / "dataset"  / "build_dataset.py"),
]


def run_step(label: str, cmd: list[str]) -> tuple[bool, float]:
    """Run a subprocess step, stream output, return (success, elapsed_seconds)."""
    console.print(Rule(f"[bold cyan]{label}[/bold cyan]"))
    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    elapsed = time.monotonic() - t0
    if result.returncode == 0:
        console.print(f"[green]✓[/green] {label} completed in {elapsed:.1f}s")
    else:
        console.print(f"[red]✗[/red] {label} failed (exit {result.returncode}) after {elapsed:.1f}s")
    return result.returncode == 0, elapsed


def resolve_configs(aliases: list[str]) -> list[tuple[str, Path]]:
    """Filter ALL_CONFIGS by alias keywords provided on the CLI."""
    if not aliases:
        return ALL_CONFIGS
    selected = []
    for alias, path in ALL_CONFIGS:
        if any(kw.lower() in alias.lower() for kw in aliases):
            selected.append((alias, path))
    if not selected:
        console.print(f"[red]No configs matched: {aliases}[/red]")
        console.print("Available aliases:")
        for alias, _ in ALL_CONFIGS:
            console.print(f"  - {alias}")
        sys.exit(1)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentSecEval end-to-end pipeline")
    parser.add_argument(
        "--configs",
        nargs="*",
        default=[],
        metavar="ALIAS",
        help="Keyword(s) to filter which experiment configs to run (default: all)",
    )
    parser.add_argument(
        "--skip-experiments",
        action="store_true",
        help="Skip experiment runs — use existing results in results/",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Skip figure generation",
    )
    args = parser.parse_args()

    python = sys.executable
    step_results: list[tuple[str, bool, float]] = []

    # ── Phase 1: experiments ────────────────────────────────────────────────
    if not args.skip_experiments:
        configs = resolve_configs(args.configs)
        console.print(f"\n[bold]Phase 1: Running {len(configs)} experiment config(s)[/bold]")
        for label, config_path in configs:
            ok, elapsed = run_step(
                f"Experiment: {label}",
                [python, "-m", "agentseceval.experiments.orchestrator",
                 "--config", str(config_path)],
            )
            step_results.append((f"Experiment: {label}", ok, elapsed))
            if not ok:
                console.print("[yellow]Warning: experiment failed — continuing to analysis.[/yellow]")
    else:
        console.print("[yellow]Skipping experiments (--skip-experiments)[/yellow]")

    # ── Phase 2: analysis ───────────────────────────────────────────────────
    console.print(f"\n[bold]Phase 2: Analysis[/bold]")
    for label, script in ANALYSIS_SCRIPTS:
        if args.skip_figures and "figure" in label.lower():
            console.print(f"[yellow]Skipping {label} (--skip-figures)[/yellow]")
            continue
        if not script.exists():
            console.print(f"[yellow]Skipping {label} — {script.name} not found yet[/yellow]")
            continue
        ok, elapsed = run_step(label, [python, str(script)])
        step_results.append((label, ok, elapsed))

    # ── Summary ─────────────────────────────────────────────────────────────
    console.print(Rule("[bold]Pipeline Summary[/bold]"))
    summary = Table(show_lines=True)
    summary.add_column("Step", style="cyan")
    summary.add_column("Status", justify="center")
    summary.add_column("Time (s)", justify="right")

    all_ok = True
    for label, ok, elapsed in step_results:
        status = "[green]PASS[/green]" if ok else "[red]FAIL[/red]"
        summary.add_row(label, status, f"{elapsed:.1f}")
        if not ok:
            all_ok = False

    console.print(summary)

    total = sum(e for _, _, e in step_results)
    console.print(f"\nTotal wall time: {total:.1f}s")

    results_dir = PROJECT_ROOT / "results"
    outputs = list(results_dir.glob("metrics_summary.csv")) + \
              list(results_dir.glob("table_*.md")) + \
              list(results_dir.glob("*.png"))
    if outputs:
        console.print("\n[bold]Output files:[/bold]")
        for p in sorted(outputs):
            console.print(f"  {p.relative_to(PROJECT_ROOT)}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
