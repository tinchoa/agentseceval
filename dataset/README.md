# AgentSecEval Dataset

Benchmark evaluating whether execution isolation (Docker, gVisor) contains adversarial LLM agent behaviors across 8 attack scenarios and 5 local models (llama3.2, mistral, qwen2.5:3b, qwen3:4b, phi4-mini).

## Files

| File | Description |
|------|-------------|
| `release/agentseceval.jsonl` | Full dataset — one JSON record per run (882 rows) |
| `release/agentseceval.parquet` | Same data in Parquet format (faster loads) |
| `release/dataset_card.md` | Dataset card with statistics and field descriptions |
| `scenarios/` | Raw YAML scenario definitions (8 attack scenarios) |
| `schema.yaml` | JSON Schema for scenario validation |
| `validate.py` | Validate all scenario YAMLs against the schema |

## Quick Start

### Load with pandas

```python
import pandas as pd

# From JSONL
df = pd.read_json("dataset/release/agentseceval.jsonl", lines=True)

# From Parquet (faster)
df = pd.read_parquet("dataset/release/agentseceval.parquet")

print(df.shape)          # (882, 26)
print(df.columns.tolist())
```

### Basic queries

```python
# Attack success rate by model
df.groupby("model")["asr"].mean().round(3)

# Filter to clean runs only (no timeout/error)
clean = df[df["error"].isna()]

# Execution-layer attacks only
exec_attacks = df[df["attack_layer"] == "execution"]

# Isolation comparison
df.groupby(["isolation_mode", "model"])["asr"].mean().unstack()
```

### Load scenario definitions

```python
import yaml, pathlib

scenarios_dir = pathlib.Path("dataset/scenarios")
scenarios = []
for path in scenarios_dir.rglob("*.yaml"):
    with open(path) as f:
        scenarios.append(yaml.safe_load(f))

# Access a scenario
s = scenarios[0]
print(s["id"], s["category"], s["task"])
```

### Key columns

| Column | Type | Description |
|--------|------|-------------|
| `scenario_id` | str | Scenario identifier (e.g. `A1_direct_01`) |
| `category` | str | Attack category (`prompt_injection`, `tool_abuse`, etc.) |
| `model` | str | Ollama model name |
| `isolation_mode` | str | `none`, `docker`, or `gvisor` |
| `asr` | int | Attack success (1 = succeeded, 0 = blocked/refused) |
| `attack_layer` | str | `execution` (tool called) or `intent` (text only) |
| `fs_breach` | int | Filesystem breach detected |
| `net_breach` | int | Network breach detected |
| `leaked` | int | Sensitive data leaked |
| `latency_s` | float | Wall-clock time for the run (seconds) |
| `error` | str/null | Timeout or runtime error message, null if clean |

## Requirements

```
pip install pandas pyarrow pyyaml
```
