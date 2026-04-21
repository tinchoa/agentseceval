# Isolation Mode: WASM (Planned — Milestone 2)

## Status

**Not yet implemented.** The WASM isolation mode is scheduled for Milestone 2.

---

## Intended Approach

The WASM isolation mode will wrap individual agent tool binaries as
**WASI (WebAssembly System Interface) modules** executed by the
[Wasmtime](https://wasmtime.dev/) runtime. Each tool invocation will:

1. Compile the tool implementation to a `.wasm` binary via a WASI-compatible toolchain.
2. Execute the `.wasm` module inside Wasmtime with explicit capability grants:
   - Filesystem access restricted to a pre-approved directory tree.
   - No network access by default (WASI has no ambient network authority).
   - CPU and memory limits enforced by Wasmtime's fuel metering.
3. Pass tool arguments and results over stdin/stdout as JSON.

This approach provides **fine-grained, per-tool isolation** rather than per-container
isolation, making it possible to allow one tool (e.g. `filesystem.read`) while denying
another (`http.request`) within the same agent run.

---

## Design Rationale

This design is inspired by the **MCP-SandboxScan** paper, which demonstrates that MCP
(Model Context Protocol) tool servers can be sandboxed at the WASI boundary to prevent
privilege escalation across tool calls. AgentSecEval's WASM mode applies the same
principle to LangChain/LangGraph tool nodes.

Reference: [MCP-SandboxScan — Sandboxing MCP Servers with WebAssembly](https://arxiv.org/abs/2504.03767) *(see paper for full citation)*

---

## Prerequisites (Milestone 2)

- Wasmtime CLI and Python bindings (`pip install wasmtime`)
- WASI-compatible Python toolchain (e.g. `py2wasm` or Rust-based tool wrappers)
- Tool implementations rewritten or wrapped as WASI modules

---

## Expected Metrics Impact

WASM isolation is expected to:
- Block all filesystem traversal escapes (RQ1) due to WASI's capability-based FS model.
- Block all unauthorized network requests (RQ1) due to WASI's lack of ambient networking.
- Have **no effect** on agent-layer prompt injection attacks (RQ2/RQ3), since those operate
  at the LLM reasoning level, not the tool execution level.
- Introduce per-tool-call latency overhead of 1–5 ms (RQ4), to be benchmarked.
