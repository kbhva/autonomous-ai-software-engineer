"""Reviewer role: inspect scoped repository context and make a structured decision."""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from flagship.agents.messages import AgentMessage, ReviewDecision, ReviewResult
from flagship.agents.runtime import ToolExecutor, model_tool_loop, parse_json_object


class Reviewer:
    actions = ("list_files", "read_file")
    instructions = ("You are the Reviewer. Assess whether the task is satisfied, using task, plan, changed file list, and test results. "
                    "Inspect relevant repository files with list_files/read_file. Do not modify files or run commands. "
                    "Return only JSON with decision (APPROVED or NEEDS_REVISION), summary (string), and issues (array of strings). "
                    "Approve only when the changes satisfy the task and tests pass; report concrete remaining problems otherwise.")

    def __init__(self, model: Any, executor: ToolExecutor):
        self.model, self.executor = model, executor

    def run(self, message: AgentMessage) -> ReviewResult:
        try:
            raw = model_tool_loop(self.model, self.executor, role="Reviewer",
                                  task=json.dumps({"task": message.task, **message.context}, ensure_ascii=False,
                                                  default=lambda value: asdict(value) if is_dataclass(value) else str(value)),
                                  instructions=self.instructions, allowed_actions=self.actions)
            data = parse_json_object(raw)
            decision = ReviewDecision(data["decision"])
            issues = data.get("issues", [])
            if not isinstance(issues, list) or not all(isinstance(item, str) for item in issues):
                raise ValueError("Reviewer issues must be an array of strings")
            return ReviewResult(decision, str(data.get("summary", "Review complete")), tuple(issues))
        except Exception as exc:
            return ReviewResult(ReviewDecision.NEEDS_REVISION, "Reviewer failed", (str(exc),))
