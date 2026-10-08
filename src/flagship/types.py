"""Shared, provider-neutral data structures."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    tool: str
    success: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "success": self.success, "summary": self.summary,
                "data": self.data, "error": self.error}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass(frozen=True)
class AgentDecision:
    complete: bool
    message: str
    tool_call: ToolCall | None = None


@dataclass(frozen=True)
class AuditEntry:
    sequence: int
    tool: str
    success: bool
    summary: str
    provider: str = "direct"
    latency_ms: float = 0.0
    error: str | None = None


@dataclass(frozen=True)
class AgentResult:
    success: bool
    message: str
    tool_calls: int
    repair_attempts: int
    audit: tuple[AuditEntry, ...]
