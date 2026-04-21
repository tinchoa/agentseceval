# Isolation Mode: none (Baseline)

## Description

The `none` isolation mode runs the agent **directly inside the host Python process** with no
sandboxing, containerisation, or kernel-level restrictions. There is no namespace separation,
cgroup resource limits, or seccomp filtering applied.

## Purpose

This mode establishes the **upper bound on Attack Success Rate (ASR)** — the worst case. Every
scenario that succeeds under `none` but fails under `docker` or `gvisor` demonstrates measurable
containment value from the isolation mechanism.

All eight benchmark scenarios are run under `none` first. Their ASR, breach rates, and leakage
scores become the baseline against which hardened modes are compared (RQ1, RQ2, RQ4).

## Usage

```bash
agentseceval --config agentseceval/experiments/configs/baseline.yaml --mode none
```

Or programmatically:

```python
from agentseceval.harness.runner import ScenarioRunner
from agentseceval.harness.agent.ollama_agent import OllamaAgent
from agentseceval.harness.logging.collector import LogCollector

runner = ScenarioRunner(
    isolation_mode="none",
    agent=OllamaAgent(),
    collector=LogCollector(results_dir="results/"),
)
log = runner.run_scenario(scenario)
```

## Security Note

**Never run untrusted or real-attack scenarios under `none` mode on a production host.**
The simulated tools in this benchmark do not make real system calls, but the LLM agent itself
runs with full host access. Use `docker` or `gvisor` modes for any experiment involving
real tool execution.
