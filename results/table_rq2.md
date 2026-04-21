# RQ2: Attack Success Rate (ASR) by Category and Isolation Mode

ASR values are **mean ± std** (%) across repetitions.
Agent-layer attacks (prompt injection, tool abuse, exfiltration, memory) are expected
to succeed at similar rates regardless of isolation mode.

| Category | docker | none |
| --- | --- | --- |
| data_exfiltration | 100.0 ± 0.0 | 100.0 ± 0.0 |
| memory_attack | 100.0 ± 0.0 | 82.0 ± 38.8 |
| prompt_injection_direct | 100.0 ± 0.0 | 98.0 ± 14.0 |
| prompt_injection_indirect | 100.0 ± 0.0 | 100.0 ± 0.0 |
| sandbox_escape | 100.0 ± 0.0 | 100.0 ± 0.0 |
| tool_abuse | 100.0 ± 0.0 | 100.0 ± 0.0 |

> **Interpretation**: If ASR is statistically equivalent across modes for a category,
> that attack type is an agent-layer concern that isolation alone cannot mitigate (RQ2).
> Categories with lower ASR under stronger isolation indicate OS-level mitigation (RQ3).