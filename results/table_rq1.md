# RQ1: Sandbox Breach Rates by Isolation Mode

Metric values are **mean ± std** across all scenarios and repetitions.
A breach occurs when a flagged tool call would escape the isolation boundary.

| Isolation Mode | FS Breach Rate (%) | Net Breach Rate (%) |
| --- | --- | --- |
|     docker
Name: 0, dtype: str | 62.5 ± 48.7 | 50.0 ± 50.3 |
|     none
Name: 1, dtype: str | 51.1 ± 50.0 | 39.9 ± 49.0 |

> **Interpretation**: Lower breach rates indicate stronger OS-level containment.
> The `none` baseline should show the highest breach rates.