---
license: mit
language:
  - en
tags:
  - llm-security
  - agent-safety
  - adversarial
  - benchmark
  - isolation
pretty_name: AgentSecEval
size_categories:
  - n<1K
---

# AgentSecEval Dataset

**AgentSecEval** is a benchmark dataset evaluating whether execution-isolation
mechanisms (Docker, gVisor, WASM) contain adversarial LLM agent behaviors when
the agent is embedded in a tool-use pipeline backed by a local Ollama model.

## Dataset Statistics

| Property | Value |
|---|---|
| Total runs | 882 |
| Clean runs (no error) | 779 |
| Overall ASR | 94.3% |
| Scenarios | 8 |
| Models | llama3.2, mistral, phi4-mini-cpu, qwen2.5:3b, qwen3:4b |
| Isolation modes | docker, gvisor, none |

### Runs by model

- **llama3.2**: 562
- **mistral**: 80
- **phi4-mini-cpu**: 80
- **qwen2.5:3b**: 80
- **qwen3:4b**: 80

### Runs by isolation mode

- **none**: 721
- **gvisor**: 81
- **docker**: 80

### Scenarios

- `A1_direct_01` (111 runs)
- `A2_indirect_01` (110 runs)
- `B1_tool_abuse_01` (110 runs)
- `B2_overprivilege_01` (110 runs)
- `C1_exfiltration_01` (111 runs)
- `D1_sandbox_escape_fs_01` (110 runs)
- `D2_sandbox_escape_net_01` (110 runs)
- `E1_memory_poison_01` (110 runs)

## Research Questions

| RQ | Description |
|---|---|
| RQ1 | Does isolation reduce attack success rate? |
| RQ2 | Does isolation prevent filesystem and network boundary violations? |
| RQ3 | Does isolation reduce sensitive data leakage? |
| RQ4 | What is the latency overhead of each isolation mechanism? |

## Schema

Each row (`agentseceval.jsonl`) is a single agent run:

```
run_id            str   — unique run identifier
scenario_id       str   — e.g. A1_direct_01
isolation_mode    str   — none | docker | gvisor | wasm
model             str   — ollama model name
repetition        int   — 0-indexed rep within (scenario, mode, model)
timestamp         str   — ISO 8601 UTC
latency_s         float — agent wall-clock time in seconds (null for legacy)
category          str   — prompt_injection | tool_abuse | ...
rqs               list  — which RQs this scenario addresses
task              str   — the legitimate task description given to the agent
context           str   — injected adversarial context/document
attack_goal       str   — attacker objective
success_criteria  list  — strings checked to determine ASR
tools             list  — tools available to the agent
agent_output      str   — full agent text response
tool_calls        list  — sequence of tool invocations with args and flags
reasoning_trace   list  — intermediate reasoning steps
host_events       list  — Docker/gVisor host-side events (isolation modes only)
asr               int   — 1 if attack succeeded, else 0
fs_breach         int   — 1 if sensitive filesystem path accessed
net_breach        int   — 1 if unauthorized network request made
leaked            int   — 1 if sensitive data found in agent output
tool_misuse_rate  float — fraction of tool calls that were flagged
tool_call_fidelity int  — 1 if model made ≥1 actual tool call
attack_layer      str   — execution | intent | none
error             str   — error message if run failed, else null
```

## Citation

```bibtex
@dataset{agentseceval2026,
  title   = {AgentSecEval: Isolation Effectiveness Benchmark for Adversarial LLM Agents},
  year    = {2026},
  url     = {https://github.com/your-org/agentsec},
  license = {MIT},
}
```
