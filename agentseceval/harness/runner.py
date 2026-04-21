"""ScenarioRunner — orchestrates single and batch scenario runs."""

import time
import uuid

from agentseceval.harness.agent.base import BaseAgent
from agentseceval.harness.logging.collector import LogCollector
from agentseceval.harness.tools.base import LoggedTool


class ScenarioRunner:
    def __init__(
        self,
        isolation_mode: str,
        agent: BaseAgent,
        collector: LogCollector,
        model: str = "unknown",
    ) -> None:
        self._isolation_mode = isolation_mode
        self._agent = agent
        self._collector = collector
        self._model = model

    def run_scenario(self, scenario: dict, run_id: str | None = None) -> dict:
        """
        1. Reset agent state
        2. Reset tool logs
        3. Run agent on scenario
        4. Collect and persist logs
        5. Return run_log dict
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        self._agent.reset()
        LoggedTool.clear_log()

        t0 = time.monotonic()
        result = self._agent.run(scenario)
        latency_s = round(time.monotonic() - t0, 3)

        run_log = self._collector.collect(
            result=result,
            run_id=run_id,
            isolation_mode=self._isolation_mode,
            model=self._model,
            latency_s=latency_s,
        )
        return run_log

    def run_batch(
        self,
        scenarios: list[dict],
        repetitions: int = 3,
        run_id: str | None = None,
    ) -> list[dict]:
        """
        Run all scenarios N times each.
        Returns flat list of all run_log dicts.
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        all_logs = []
        for scenario in scenarios:
            for rep in range(repetitions):
                rep_run_id = f"{run_id}_rep{rep}"
                log = self.run_scenario(scenario, run_id=rep_run_id)
                all_logs.append(log)
        return all_logs
