#!/usr/bin/env python3
"""
Standalone scenario validator — no harness imports.

Usage:
    python dataset/validate.py
"""

import sys
from pathlib import Path

import yaml
import jsonschema
from rich.console import Console
from rich.table import Table

DATASET_DIR = Path(__file__).parent
SCHEMA_PATH = DATASET_DIR / "schema.yaml"
SCENARIOS_DIR = DATASET_DIR / "scenarios"


def load_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return yaml.safe_load(f)


def validate_file(path: Path, schema: dict) -> tuple[bool, str]:
    """Return (passed, error_message). error_message is empty string on success."""
    try:
        with path.open() as f:
            scenario = yaml.safe_load(f)
        jsonschema.validate(instance=scenario, schema=schema)
        return True, ""
    except yaml.YAMLError as exc:
        return False, f"YAML parse error: {exc}"
    except jsonschema.ValidationError as exc:
        return False, exc.message
    except Exception as exc:
        return False, str(exc)


def main() -> None:
    console = Console()

    schema = load_schema()

    scenario_files = sorted(SCENARIOS_DIR.rglob("*.yaml"))
    if not scenario_files:
        console.print("[bold red]No scenario files found under dataset/scenarios/[/bold red]")
        sys.exit(1)

    table = Table(title="Scenario Validation Results", show_lines=True)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    failures = 0
    for path in scenario_files:
        relative = path.relative_to(DATASET_DIR)
        passed, error = validate_file(path, schema)
        if passed:
            table.add_row(str(relative), "[green]PASS[/green]", "")
        else:
            table.add_row(str(relative), "[red]FAIL[/red]", error)
            failures += 1

    console.print(table)

    total = len(scenario_files)
    passed_count = total - failures
    console.print(
        f"\n[bold]Results: {passed_count}/{total} passed[/bold]"
        + ("" if failures == 0 else f", [red]{failures} failed[/red]")
    )

    if failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
