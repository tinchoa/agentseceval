# AgentSecEval

AgentSecEval is a security benchmark that systematically evaluates whether execution isolation mechanisms — Docker standard containers, gVisor kernel-sandboxed containers, and WebAssembly (WASM) modules — actually contain adversarial behaviors exhibited by LLM-based agents. The benchmark runs a suite of attack scenarios against agents powered by a local Ollama model, measures attack success rates and breach events from an external-observer vantage point, and computes per-isolation-mode metrics to guide practitioners in selecting the right containment strategy for agentic deployments.

---

## Research Questions

- **RQ1**: For each isolation mode, what fraction of sandbox escape attempts are contained at the OS level?
- **RQ2**: Do agent-layer attacks succeed at statistically equivalent rates regardless of isolation mode?
- **RQ3**: After applying the strongest isolation mode, what attack categories remain fully unmitigated?
- **RQ4**: What is the latency and task success rate overhead introduced by each isolation mode?

---

## Repository Structure

```
agentsec/                          ← project root
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── dataset/                       ← scenario definitions (non-Python)
│   ├── schema.yaml                ← JSON Schema for scenario validation
│   ├── validate.py                ← standalone validator script
│   └── scenarios/
│       ├── prompt_injection/
│       │   ├── A1_direct_01.yaml
│       │   └── A2_indirect_01.yaml
│       ├── tool_abuse/
│       │   ├── B1_tool_abuse_01.yaml
│       │   └── B2_overprivilege_01.yaml
│       ├── exfiltration/
│       │   └── C1_exfiltration_01.yaml
│       ├── sandbox_escape/
│       │   ├── D1_sandbox_escape_fs_01.yaml
│       │   └── D2_sandbox_escape_net_01.yaml
│       └── memory_attack/
│           └── E1_memory_poison_01.yaml
│
├── agentseceval/                  ← installable Python package
│   ├── harness/                   ← core evaluation harness
│   │   ├── agent/                 ← agent backends (Ollama via LangGraph)
│   │   ├── tools/                 ← simulated tool implementations
│   │   ├── logging/               ← run log collection
│   │   ├── metrics/               ← ASR, breach, leakage calculations
│   │   └── runner.py              ← ScenarioRunner
│   └── experiments/               ← evaluation entrypoints
│       ├── orchestrator.py        ← main CLI entrypoint
│       └── configs/               ← experiment config YAMLs
│
├── isolation/                     ← isolation infrastructure (non-Python)
│   ├── none/                      ← baseline (no isolation)
│   ├── docker/                    ← Docker container isolation
│   ├── gvisor/                    ← gVisor kernel sandbox
│   └── wasm/                      ← WASM (planned)
│
├── results/                       ← run outputs (gitignored except .gitkeep)
│
├── analysis/                      ← post-processing scripts and notebooks
│   ├── compute_metrics.py
│   ├── generate_tables.py
│   └── notebooks/
│       └── exploration.ipynb
│
└── tests/                         ← pytest test suite
    ├── test_schema_validation.py
    ├── test_tools.py
    └── test_metrics.py
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env to set OLLAMA_HOST and OLLAMA_MODEL as needed
```

### 3. Pull the Ollama model

```bash
ollama pull llama3.2
```

### 4. Validate the scenario dataset

```bash
python dataset/validate.py
```

### 5. Run a single scenario (baseline / no isolation)

```bash
agentseceval --config experiments/configs/baseline.yaml --scenario A1_direct_01 --mode none
```

### 6. Run the full milestone-1 evaluation matrix

```bash
agentseceval --config experiments/configs/milestone1.yaml
```

Results are written to `results/` as JSON files, one per scenario × mode × repetition.

### 7. Compute metrics and generate tables

```bash
python analysis/compute_metrics.py
python analysis/generate_tables.py
```

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) running locally (default: `http://localhost:11434`)
- Docker (for `docker` isolation mode)
- Linux x86-64 with gVisor `runsc` installed (for `gvisor` isolation mode)
- Python packages listed in `pyproject.toml` (installed via `pip install -e .`)

---

## License

MIT License. See [LICENSE](LICENSE).
