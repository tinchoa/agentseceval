from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolCallRecord:
    tool_name: str
    args: dict
    result: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    flagged: bool = False
    flag_reason: str | None = None


class LoggedTool:
    """Mixin that wraps any tool to record all invocations."""

    _log: list[ToolCallRecord] = []

    def _record(self, tool_name: str, args: dict, result: str) -> ToolCallRecord:
        record = ToolCallRecord(tool_name=tool_name, args=args, result=result)
        self._log.append(record)
        return record

    @classmethod
    def get_log(cls) -> list[ToolCallRecord]:
        return cls._log

    @classmethod
    def clear_log(cls) -> None:
        cls._log = []
