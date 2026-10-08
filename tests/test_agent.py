from collections import deque

from flagship.agent import CodingAgent
from flagship.types import AgentDecision, ToolCall, ToolResult


class FakeModel:
    def __init__(self, decisions):
        self.decisions = deque(decisions)
        self.calls = 0
    def next_action(self, task, history):
        self.calls += 1
        return self.decisions.popleft()


class FakeFiles:
    name = "repository_files"
    actions = ("list_files", "read_file", "write_file")
    def execute(self, arguments):
        return ToolResult(arguments["action"], True, "ok", {})


class FakeTests:
    name = "run_tests"
    actions = ("run_tests",)
    def __init__(self, outcomes): self.outcomes = deque(outcomes)
    def execute(self, arguments): return self.outcomes.popleft()


def call(action):
    return AgentDecision(False, "", ToolCall("repository_action", {"action": action}, "id"))


def test_agent_stops_at_tool_call_limit():
    model = FakeModel([call("list_files")] * 5)
    result = CodingAgent(model, [FakeFiles()], max_tool_calls=2).run("task")
    assert not result.success
    assert result.tool_calls == 2
    assert model.calls == 3  # One final decision after the two permitted tool calls.


def test_agent_stops_at_repair_attempt_limit():
    model = FakeModel([call("run_tests"), call("run_tests"), call("run_tests")])
    failures = [ToolResult("run_tests", False, "failed", {}) for _ in range(2)]
    result = CodingAgent(model, [FakeTests(failures)], max_tool_calls=10, max_repair_attempts=1).run("task")
    assert not result.success
    assert "Repair-attempt limit" in result.message
    assert result.repair_attempts == 1  # One repair after the initial verification.
    assert model.calls == 3


def test_agent_completes_and_records_audit():
    model = FakeModel([call("list_files"), call("run_tests"), AgentDecision(True, "Completed")])
    tests = FakeTests([ToolResult("run_tests", True, "passed", {})])
    result = CodingAgent(model, [FakeFiles(), tests]).run("task")
    assert result.success
    assert result.message == "Completed"
    assert result.audit[0].tool == "list_files"


def test_agent_requires_pytest_before_completion():
    model = FakeModel([AgentDecision(True, "Done")])
    result = CodingAgent(model, [FakeFiles()]).run("task")
    assert not result.success
    assert "pytest verification" in result.message


def test_agent_repairs_failed_tests_then_completes():
    model = FakeModel([call("run_tests"), call("write_file"), call("run_tests"), AgentDecision(True, "Repaired")])
    tests = FakeTests([ToolResult("run_tests", False, "failed", {}), ToolResult("run_tests", True, "passed", {})])
    result = CodingAgent(model, [FakeFiles(), tests], max_repair_attempts=1).run("task")
    assert result.success
    assert result.repair_attempts == 1


def test_agent_rejects_completion_with_failing_tests():
    model = FakeModel([call("run_tests"), AgentDecision(True, "Done")])
    tests = FakeTests([ToolResult("run_tests", False, "failed", {})])
    result = CodingAgent(model, [tests], max_repair_attempts=0).run("task")
    assert not result.success
    assert "pytest is failing" in result.message
