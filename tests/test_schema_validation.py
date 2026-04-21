"""Tests for dataset schema validation."""

import sys
from pathlib import Path

import pytest
import yaml
import jsonschema

# Ensure project root is on sys.path for standalone dataset validator
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
SCHEMA_PATH = DATASET_DIR / "schema.yaml"
SCENARIOS_DIR = DATASET_DIR / "scenarios"


def _load_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return yaml.safe_load(f)


def test_all_scenarios_valid():
    """All 8 scenario YAML files must pass schema validation."""
    schema = _load_schema()
    scenario_files = list(SCENARIOS_DIR.rglob("*.yaml"))

    assert len(scenario_files) == 8, (
        f"Expected 8 scenario files, found {len(scenario_files)}: "
        + ", ".join(str(p.name) for p in scenario_files)
    )

    for path in scenario_files:
        with path.open() as f:
            scenario = yaml.safe_load(f)
        try:
            jsonschema.validate(instance=scenario, schema=schema)
        except jsonschema.ValidationError as exc:
            pytest.fail(f"{path.name} failed validation: {exc.message}")


def test_schema_rejects_invalid():
    """A scenario missing required fields must raise jsonschema.ValidationError."""
    schema = _load_schema()

    # Missing 'category', 'task', 'context', 'tools', 'attack_goal', 'success_criteria'
    invalid_scenario = {
        "id": "Z1_test_01",
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_scenario, schema=schema)


def test_schema_rejects_invalid_category():
    """A scenario with an unknown category must fail validation."""
    schema = _load_schema()

    invalid_scenario = {
        "id": "Z1_test_01",
        "category": "not_a_real_category",
        "task": "Do something",
        "context": {"type": "user_input", "content": "Hello"},
        "tools": ["filesystem.read"],
        "attack_goal": {"type": "data_exfiltration", "target": "something"},
        "success_criteria": ["some criterion"],
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_scenario, schema=schema)


def test_schema_rejects_empty_success_criteria():
    """A scenario with an empty success_criteria list must fail (minItems: 1)."""
    schema = _load_schema()

    invalid_scenario = {
        "id": "Z1_test_01",
        "category": "tool_abuse",
        "task": "Do something",
        "context": {"type": "user_input", "content": "Hello"},
        "tools": ["filesystem.read"],
        "attack_goal": {"type": "data_exfiltration", "target": "something"},
        "success_criteria": [],  # empty — violates minItems: 1
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_scenario, schema=schema)
