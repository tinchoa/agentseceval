"""Run log collection and persistence."""

import json
import os
from datetime import datetime
from pathlib import Path

from agentseceval.harness.agent.base import AgentResult
from agentseceval.harness.tools.base import LoggedTool


class LogCollector:
    """Collects an AgentResult + tool logs and persists them as JSON."""

    def __init__(self, results_dir: str = "results") -> None:
        self._results_dir = Path(results_dir)

    def collect(
        self,
        result: AgentResult,
        run_id: str,
        isolation_mode: str,
        model: str = "unknown",
        host_events: list[str] | None = None,
        latency_s: float | None = None,
    ) -> dict:
        """
        Combine AgentResult with LoggedTool records into a run_log dict,
        persist it to disk, and return the dict.
        """
        tool_call_records = [
            {
                "tool": r.tool_name,
                "args": r.args,
                "result": r.result,
                "timestamp": r.timestamp,
                "flagged": r.flagged,
                "flag_reason": r.flag_reason,
            }
            for r in LoggedTool.get_log()
        ]

        run_log = {
            "run_id": run_id,
            "scenario_id": result.scenario_id,
            "isolation_mode": isolation_mode,
            "model": model,
            "timestamp": datetime.utcnow().isoformat(),
            "latency_s": latency_s,
            "agent_output": result.raw_output,
            "tool_calls": tool_call_records,
            "reasoning_trace": result.reasoning_trace,
            "host_events": host_events or [],
            "error": result.error,
        }

        self._persist(run_log, run_id, result.scenario_id, isolation_mode)
        return run_log

    def _persist(
        self,
        run_log: dict,
        run_id: str,
        scenario_id: str,
        isolation_mode: str,
    ) -> None:
        run_dir = self._results_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{scenario_id}__{isolation_mode}.json"
        output_path = run_dir / filename
        with output_path.open("w") as f:
            json.dump(run_log, f, indent=2)
