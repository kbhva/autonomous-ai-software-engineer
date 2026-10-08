"""Run a deterministic, offline demonstration of the existing orchestrator.

The scripted model follows the same next_action protocol as the real model
adapter. Repository tools and pytest are real; model decisions are scripted.
This is a workflow demo, not an evaluation of model or agent quality.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from flagship.orchestration import Orchestrator
from flagship.tools import PytestTool, RepositoryFileTools
from flagship.types import AgentDecision, ToolCall


TASK = "Make is_successful_status return True only for HTTP 2xx status codes."

INITIAL_SOURCE = '''def is_successful_status(code: int) -> bool:
    return 200 <= code < 500
'''

TEST_SOURCE = '''from status import is_successful_status


def test_2xx_is_successful():
    assert is_successful_status(201) is True


def test_redirect_is_not_successful():
    assert is_successful_status(302) is False


def test_5xx_is_not_successful():
    assert is_successful_status(503) is False
'''

FIRST_ATTEMPT_SOURCE = '''def is_successful_status(code: int) -> bool:
    return 200 <= code < 500
'''

REPAIRED_SOURCE = '''def is_successful_status(code: int) -> bool:
    return 200 <= code < 300
'''


class ScriptedModel:
    """A deterministic stand-in implementing the model adapter protocol."""

    def __init__(self) -> None:
        self._call_number = 0
        self.review_decisions: list[str] = []

    def _tool_call(self, action: str, **arguments: Any) -> AgentDecision:
        self._call_number += 1
        return AgentDecision(
            False,
            "",
            ToolCall(
                "repository_action",
                {"action": action, **arguments},
                f"demo-call-{self._call_number}",
            ),
        )

    @staticmethod
    def _called_actions(history: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        for item in history:
            if item.get("type") != "function_call":
                continue
            try:
                arguments = json.loads(item.get("arguments", "{}"))
            except (TypeError, json.JSONDecodeError):
                continue
            action = arguments.get("action")
            if isinstance(action, str):
                actions.append(action)
        return actions

    def next_action(
        self,
        task: str,
        history: list[dict[str, Any]],
        *,
        instructions: str | None = None,
        allowed_actions: tuple[str, ...] | None = None,
    ) -> AgentDecision:
        role_instructions = instructions or ""
        actions = self._called_actions(history)

        if role_instructions.startswith("You are the Planner."):
            if not actions:
                return self._tool_call("read_file", path="status.py")
            return AgentDecision(True, json.dumps({
                "summary": "Keep success status codes within the HTTP 2xx range.",
                "steps": ["Inspect status.py", "Use an inclusive 200 lower bound and exclusive 300 upper bound"],
                "likely_files": ["status.py"],
            }))

        if role_instructions.startswith("You are the Coder."):
            payload = json.loads(task)
            has_feedback = bool(payload.get("previous_feedback"))
            if not actions:
                return self._tool_call("read_file", path="status.py")
            if actions[-1] == "read_file":
                source = REPAIRED_SOURCE if has_feedback else FIRST_ATTEMPT_SOURCE
                return self._tool_call("write_file", path="status.py", content=source)
            return AgentDecision(True, json.dumps({
                "summary": "Updated the status-code predicate.",
                "changed_files": ["status.py"],
            }))

        if role_instructions.startswith("You are the Reviewer."):
            if not actions:
                return self._tool_call("read_file", path="status.py")
            payload = json.loads(task)
            tests_passed = bool(payload.get("tests", {}).get("success"))
            decision = "APPROVED" if tests_passed else "NEEDS_REVISION"
            self.review_decisions.append(decision)
            return AgentDecision(True, json.dumps({
                "decision": decision,
                "summary": "Tests pass and the status range matches the task."
                if tests_passed else "The test run failed; revise the status range.",
                "issues": [] if tests_passed else ["The redirect status test failed."],
            }))

        raise ValueError(f"Unexpected scripted role: {role_instructions[:80]}")


def main() -> int:
    print("Flagship deterministic workflow demo")
    print("Model: scripted; no OpenAI API calls")
    print("Tools: real repository-scoped file tools and pytest; direct provider")
    print("RepoMind, MCP SDK transport, and hidden benchmark evaluators: not used")
    print(f"Task: {TASK}\n")

    with tempfile.TemporaryDirectory(prefix="flagship-demo-") as directory:
        workspace = Path(directory)
        (workspace / "status.py").write_text(INITIAL_SOURCE, encoding="utf-8")
        (workspace / "test_status.py").write_text(TEST_SOURCE, encoding="utf-8")

        files = RepositoryFileTools(workspace)
        pytest_tool = PytestTool(workspace, timeout_seconds=30)
        model = ScriptedModel()
        result = Orchestrator(
            model,
            [files, pytest_tool],
            max_tool_calls=30,
            max_coding_attempts=2,
            mode="multi",
        ).run(TASK)

        print("State transitions:", " -> ".join(result.transitions))
        for index, test_result in enumerate(result.tests, start=1):
            print(f"pytest attempt {index}: {test_result.summary}")
        print("Scripted reviewer decisions:", " -> ".join(model.review_decisions))
        print("Repair attempts:", result.repair_attempts)
        print("Tool calls:", result.tool_calls)
        print("Changed files:", ", ".join(
            dict.fromkeys(path for coder in result.coder_attempts for path in coder.changed_files)
        ))
        print("Final status:", result.status)
        print("Final source:")
        print((workspace / "status.py").read_text(encoding="utf-8"), end="")

        return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
