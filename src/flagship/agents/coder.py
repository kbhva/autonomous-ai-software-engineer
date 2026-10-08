"""Coder role: implement a task using repository-scoped file tools only."""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from flagship.agents.messages import AgentMessage, CoderResult
from flagship.agents.runtime import ToolExecutor, model_tool_loop, parse_json_object


class Coder:
    actions = ("list_files", "read_file", "write_file")
    instructions = ("You are the Coder. Implement the requested task following the provided plan and feedback. "
                    "Inspect relevant files before editing. Use only list_files, read_file, and write_file; do not run shell commands or tests. "
                    "When done, return only a JSON object with summary (string) and changed_files (array of repository-relative paths).")

    def __init__(self, model: Any, executor: ToolExecutor):
        self.model, self.executor = model, executor

    def run(self, message: AgentMessage) -> CoderResult:
        try:
            payload = json.dumps({"task": message.task, **message.context}, ensure_ascii=False,
                                 default=lambda value: asdict(value) if is_dataclass(value) else str(value))
            raw = model_tool_loop(self.model, self.executor, role="Coder", task=payload,
                                  instructions=self.instructions, allowed_actions=self.actions)
            data = parse_json_object(raw)
            files = data.get("changed_files", [])
            if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
                raise ValueError("Coder changed_files must be an array of strings")
            return CoderResult(True, str(data.get("summary", "Implementation complete")), tuple(files))
        except Exception as exc:
            return CoderResult(False, "Coder failed", error=str(exc))
