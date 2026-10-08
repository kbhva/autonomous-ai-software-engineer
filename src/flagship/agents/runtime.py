"""Shared bounded tool access and model interaction for role agents."""

import json
import logging
import time
from typing import Any

from flagship.types import AgentDecision, AuditEntry, ToolResult
from flagship.tools.provider import DirectToolProvider

logger = logging.getLogger("flagship.audit")


class ToolBudgetExceeded(RuntimeError):
    pass


class ToolExecutor:
    """Dispatches existing tools and enforces one run-wide budget."""

    def __init__(self, tools: Any, max_tool_calls: int):
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be positive")
        self.provider = tools if hasattr(tools, "provider_name") else DirectToolProvider(tools)
        self.max_tool_calls = max_tool_calls
        self.audit: list[AuditEntry] = []
        self.written_files: list[str] = []
        self.results: list[tuple[str, ToolResult]] = []

    def execute(self, action: str, arguments: dict[str, Any], allowed: tuple[str, ...]) -> ToolResult:
        if len(self.audit) >= self.max_tool_calls:
            raise ToolBudgetExceeded("Total tool-call budget exhausted")
        if action not in allowed:
            result = ToolResult("validate_tool", False, "Rejected action outside this agent's permissions",
                                error=f"Action is not allowed for this role: {action}")
            self.record(result, provider="runtime")
            return result
        started = time.perf_counter()
        try:
            result = self.provider.execute(action, arguments)
        except Exception as exc:
            result = ToolResult(action, False, "Tool provider failed", error=f"{type(exc).__name__}: {exc}")
        latency_ms = (time.perf_counter() - started) * 1000
        if action == "write_file" and result.success and isinstance(arguments.get("path"), str):
            self.written_files.append(arguments["path"])
        self.results.append((action, result))
        provider_name = self.provider.provider_for(action) if hasattr(self.provider, "provider_for") else None
        self.record(result, latency_ms, provider_name)
        return result

    @property
    def mcp_tool_calls(self) -> int:
        return sum(entry.provider == "mcp" for entry in self.audit)

    @property
    def mcp_tool_latency_ms(self) -> float:
        return sum(entry.latency_ms for entry in self.audit if entry.provider == "mcp")

    @property
    def tool_latency_ms(self) -> float:
        return sum(entry.latency_ms for entry in self.audit if entry.provider != "repomind")

    @property
    def retrieval_latency_ms(self) -> float:
        return sum(float(result.data.get("retrieval_latency_ms", 0.0))
                   for action, result in self.results if action == "search_repository" and result.success)

    @property
    def tool_errors(self) -> int:
        return sum(not entry.success for entry in self.audit)

    def record(self, result: ToolResult, latency_ms: float = 0.0, provider: str | None = None) -> None:
        provider_name = provider or getattr(self.provider, "provider_name", "direct")
        entry = AuditEntry(len(self.audit) + 1, result.tool, result.success, result.summary,
                           provider=provider_name, latency_ms=latency_ms, error=result.error)
        self.audit.append(entry)
        logger.info("tool_call=%s success=%s summary=%s", result.tool, result.success, result.summary)


def model_tool_loop(model: Any, executor: ToolExecutor, *, role: str, task: str,
                    instructions: str, allowed_actions: tuple[str, ...],
                    max_interactions: int = 20) -> str:
    """Run one role's bounded tool interaction; it never invokes another agent."""
    history: list[dict[str, Any]] = []
    for _ in range(max_interactions + 1):
        decision: AgentDecision = model.next_action(task, history, instructions=instructions,
                                                    allowed_actions=allowed_actions)
        if decision.complete:
            return decision.message
        call = decision.tool_call
        if call is None:
            raise ValueError(f"{role} model returned neither a tool call nor a result")
        action = call.arguments.get("action")
        result = executor.execute(action, {key: value for key, value in call.arguments.items() if key != "action"}, allowed_actions)
        history.extend([
            {"type": "function_call", "call_id": call.call_id, "name": call.name,
             "arguments": json.dumps(call.arguments, ensure_ascii=False)},
            {"type": "function_call_output", "call_id": call.call_id,
             "output": json.dumps(result.to_dict(), ensure_ascii=False)},
        ])
    raise ToolBudgetExceeded(f"{role} interaction limit reached")


def parse_json_object(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Agent result must be a JSON object")
    return value
