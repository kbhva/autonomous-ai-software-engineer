"""OpenAI Responses API adapter. Provider-specific code stays in this module."""

import json
import os
from typing import Any, Protocol

from flagship.types import AgentDecision, ToolCall


TOOL_SCHEMA: dict[str, Any] = {
    "type": "function", "name": "repository_action", "description": "Perform one allowed repository action.",
    "parameters": {
        "type": "object", "properties": {
            "action": {"type": "string", "enum": ["list_files", "read_file", "write_file", "run_tests"]},
            "path": {"type": "string"}, "content": {"type": "string"},
            "limit": {"type": "integer"}, "args": {"type": "array", "items": {"type": "string"}},
            "repository_id": {"type": "string"}, "query": {"type": "string"},
            "top_k": {"type": "integer"},
        }, "required": ["action"], "additionalProperties": False,
    },
}


class Model(Protocol):
    def next_action(self, task: str, history: list[dict[str, Any]], *,
                    instructions: str | None = None,
                    allowed_actions: tuple[str, ...] | None = None) -> AgentDecision: ...


class OpenAIResponsesModel:
    def __init__(self, model: str | None = None, client: Any | None = None):
        self.model = model or os.getenv("FLAGSHIP_MODEL", "gpt-5")
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        self.client = client
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.total_tokens: int | None = None
        self.usage_available = False

    def next_action(self, task: str, history: list[dict[str, Any]], *,
                    instructions: str | None = None,
                    allowed_actions: tuple[str, ...] | None = None) -> AgentDecision:
        tool_schema = json.loads(json.dumps(TOOL_SCHEMA))
        if allowed_actions is not None:
            tool_schema["parameters"]["properties"]["action"]["enum"] = list(allowed_actions)
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions or ("You are a careful coding agent working in one repository. Inspect before editing. "
                          "Use only the repository_action function for list_files, read_file, write_file, and run_tests. "
                          "After changes, run tests and repair failures within the available attempts. "
                          "When done, respond with a concise summary and no tool call."),
            input=[{"role": "user", "content": f"Task: {task}"}, *history],
            tools=[tool_schema],
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            values = []
            for field in ("input_tokens", "output_tokens", "total_tokens"):
                value = getattr(usage, field, None)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    current = getattr(self, field)
                    setattr(self, field, value + (current or 0))
                    values.append(value)
            self.usage_available = self.usage_available or bool(values)
        for item in response.output:
            if getattr(item, "type", None) == "function_call" and getattr(item, "name", None) == "repository_action":
                try:
                    arguments = json.loads(item.arguments)
                except (TypeError, json.JSONDecodeError):
                    arguments = {}
                return AgentDecision(False, "", ToolCall("repository_action", arguments, getattr(item, "call_id", "")))
        return AgentDecision(True, getattr(response, "output_text", "Task finished"))
