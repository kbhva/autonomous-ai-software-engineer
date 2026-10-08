"""Bounded single-agent loop, depending only on model and tool interfaces."""

import json
import logging
import time
from typing import Any, Iterable

from flagship.types import AgentDecision, AgentResult, AuditEntry, ToolResult

logger = logging.getLogger("flagship.audit")


class CodingAgent:
    def __init__(self, model: Any, tools: Iterable[Any], max_tool_calls: int = 20, max_repair_attempts: int = 2):
        if max_tool_calls < 1 or max_repair_attempts < 0:
            raise ValueError("Tool-call budget must be positive and repair budget cannot be negative")
        self.model = model
        self.tools = {action: tool for tool in tools for action in tool.actions}
        self.max_tool_calls = max_tool_calls
        self.max_repair_attempts = max_repair_attempts

    def run(self, task: str) -> AgentResult:
        history: list[dict[str, Any]] = []
        audit: list[AuditEntry] = []
        test_runs = 0
        latest_tests_passed: bool | None = None
        while True:
            decision: AgentDecision = self.model.next_action(task, history)
            if decision.complete:
                if test_runs == 0:
                    return AgentResult(False, "Task cannot be reported complete before pytest verification.", len(audit), 0, tuple(audit))
                if latest_tests_passed is not True:
                    return AgentResult(False, "Task cannot be reported complete while pytest is failing.", len(audit), max(0, test_runs - 1), tuple(audit))
                return AgentResult(True, decision.message, len(audit), max(0, test_runs - 1), tuple(audit))
            call = decision.tool_call
            if call is None:
                return AgentResult(False, "Model returned neither a tool call nor a completion.", len(audit), max(0, test_runs - 1), tuple(audit))
            if len(audit) >= self.max_tool_calls:
                return AgentResult(False, "Tool-call limit reached before task completion.", len(audit), max(0, test_runs - 1), tuple(audit))
            sequence = len(audit) + 1
            action = call.arguments.get("action")
            if action == "run_tests" and test_runs >= self.max_repair_attempts + 1:
                return AgentResult(False, "Repair-attempt limit reached.", len(audit), max(0, test_runs - 1), tuple(audit))
            tool = self.tools.get(action)
            started = time.perf_counter()
            if tool is None or action not in {"list_files", "read_file", "write_file", "run_tests"}:
                result = ToolResult("validate_tool", False, "Rejected unsupported tool request", error=f"Unsupported action: {action}")
            else:
                args = call.arguments if action != "run_tests" else call.arguments
                result = tool.execute(args)
                if action == "run_tests":
                    test_runs += 1
                    latest_tests_passed = result.success
            latency_ms = (time.perf_counter() - started) * 1000
            entry = AuditEntry(sequence, result.tool, result.success, result.summary,
                               latency_ms=latency_ms, error=result.error)
            audit.append(entry)
            logger.info("tool_call=%s success=%s summary=%s", result.tool, result.success, result.summary)
            history.append({"type": "function_call", "call_id": call.call_id, "name": call.name,
                            "arguments": json.dumps(call.arguments, ensure_ascii=False)})
            history.append({"type": "function_call_output", "call_id": call.call_id,
                            "output": json.dumps(result.to_dict(), ensure_ascii=False)})
