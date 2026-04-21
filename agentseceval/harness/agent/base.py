from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    scenario_id: str
    raw_output: str
    tool_calls: list[dict]       # [{tool, args, result, timestamp}]
    reasoning_trace: list[str]   # intermediate steps if available
    error: str | None


class BaseAgent(ABC):
    @abstractmethod
    def run(self, scenario: dict) -> AgentResult:
        """Execute a scenario and return structured results."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Clear any stateful memory between runs."""
        ...
