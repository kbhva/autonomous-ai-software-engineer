"""Planner role: inspect repository and return a structured plan, without writes."""

import json
from typing import Any

from flagship.agents.messages import AgentMessage, PlannerResult
from flagship.agents.runtime import ToolExecutor, model_tool_loop, parse_json_object


class Planner:
    actions = ("list_files", "read_file")
    instructions = ("You are the Planner. Understand the task and inspect the repository using only list_files and read_file. "
                    "Do not modify files. Return only a JSON object with summary (string), steps (array of strings), "
                    "and likely_files (array of repository-relative paths).")

    def __init__(self, model: Any, executor: ToolExecutor, repository_id: str | None = None):
        self.model, self.executor = model, executor
        self.repository_id = repository_id

    def run(self, message: AgentMessage) -> PlannerResult:
        try:
            result_start = len(self.executor.results)
            actions = (*self.actions, "search_repository") if self.repository_id else self.actions
            instructions = self.instructions
            if self.repository_id:
                instructions += (f" Retrieve relevant repository evidence with search_repository before planning. "
                                 f"Every search must include repository_id={self.repository_id!r}, query, and top_k. "
                                 "Use the retrieved evidence in your plan.")
            raw = model_tool_loop(self.model, self.executor, role="Planner",
                                  task=json.dumps({"task": message.task, **message.context}, ensure_ascii=False),
                                  instructions=instructions, allowed_actions=actions)
            data = parse_json_object(raw)
            steps, files = data.get("steps", []), data.get("likely_files", [])
            if not isinstance(steps, list) or not all(isinstance(item, str) for item in steps):
                raise ValueError("Planner steps must be an array of strings")
            if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
                raise ValueError("Planner likely_files must be an array of strings")
            retrieval = tuple(item.data for action, item in self.executor.results[result_start:]
                              if action == "search_repository" and item.success)
            return PlannerResult(True, str(data.get("summary", "Plan ready")), tuple(steps), tuple(files),
                                 retrieval_evidence=retrieval)
        except Exception as exc:
            return PlannerResult(False, "Planner failed", error=str(exc))
