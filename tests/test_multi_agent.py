import json
from collections import deque

from flagship.agents import Coder, Planner, Reviewer, Tester
from flagship.agents.messages import AgentMessage, ReviewDecision, ReviewResult
from flagship.agents.runtime import ToolExecutor
from flagship.orchestration import Orchestrator
from flagship.tools import PytestTool, RepositoryFileTools
from flagship.types import AgentDecision, ToolCall, ToolResult


class ScriptedModel:
    def __init__(self, decisions):
        self.decisions = deque(decisions)
        self.calls = []
    def next_action(self, task, history, *, instructions=None, allowed_actions=None):
        self.calls.append((task, instructions, allowed_actions))
        item = self.decisions.popleft()
        if isinstance(item, Exception):
            raise item
        return item


def final(value):
    return AgentDecision(True, json.dumps(value))


def action(name, **kwargs):
    return AgentDecision(False, "", ToolCall("repository_action", {"action": name, **kwargs}, "call-id"))


class FakeFiles:
    actions = ("list_files", "read_file", "write_file")
    def __init__(self): self.writes = []
    def execute(self, args):
        if args["action"] == "write_file":
            self.writes.append(args["path"])
        return ToolResult(args["action"], True, "ok", {})


class FakeTests:
    actions = ("run_tests",)
    def __init__(self, outcomes): self.outcomes = deque(outcomes)
    def execute(self, args): return self.outcomes.popleft()


def passing(): return ToolResult("run_tests", True, "pytest passed", {"returncode": 0, "stdout": "ok"})
def failing(): return ToolResult("run_tests", False, "pytest failed", {"returncode": 1, "stderr": "failure"})


def test_planner_returns_structured_plan_and_cannot_write():
    files = FakeFiles()
    model = ScriptedModel([action("write_file", path="x.py", content="bad"),
                           final({"summary": "Plan", "steps": ["inspect"], "likely_files": ["x.py"]})])
    result = Planner(model, ToolExecutor([files], 5)).run(AgentMessage("Planner", "Add a feature"))
    assert result.success and result.steps == ("inspect",)
    assert not files.writes
    assert model.calls[0][2] == ("list_files", "read_file")


def test_coder_returns_structured_output_and_uses_scoped_write(tmp_path):
    files = RepositoryFileTools(tmp_path)
    model = ScriptedModel([action("write_file", path="pkg/new.py", content="x = 1\n"),
                           final({"summary": "Added module", "changed_files": ["pkg/new.py"]})])
    executor = ToolExecutor([files], 5)
    result = Coder(model, executor).run(AgentMessage("Coder", "Add module", {"plan": {"steps": ["write"]}}))
    assert result.success and result.changed_files == ("pkg/new.py",)
    assert (tmp_path / "pkg" / "new.py").read_text(encoding="utf-8") == "x = 1\n"


def test_tester_returns_structured_test_result():
    result = Tester(ToolExecutor([FakeTests([failing()])], 1)).run()
    assert not result.success
    assert result.returncode == 1 and result.stderr == "failure"


def test_reviewer_returns_typed_decision():
    model = ScriptedModel([final({"decision": "APPROVED", "summary": "Looks good", "issues": []})])
    result = Reviewer(model, ToolExecutor([FakeFiles()], 2)).run(AgentMessage("Reviewer", "task"))
    assert result.decision is ReviewDecision.APPROVED


def test_orchestrator_approved_path():
    model = ScriptedModel([final({"summary": "Plan", "steps": [], "likely_files": []}),
                           final({"summary": "Coded", "changed_files": []}),
                           final({"decision": "APPROVED", "summary": "Accepted", "issues": []})])
    result = Orchestrator(model, [FakeFiles(), FakeTests([passing()])], max_tool_calls=5).run("task")
    assert result.success and result.status == "DONE"
    assert result.transitions == ("PLAN", "CODE", "TEST", "REVIEW", "DONE")
    assert result.tool_calls == 1


def test_orchestrator_needs_revision_path():
    model = ScriptedModel([
        final({"summary": "Plan", "steps": [], "likely_files": []}),
        final({"summary": "First", "changed_files": []}),
        final({"decision": "NEEDS_REVISION", "summary": "Revise", "issues": ["fix tests"]}),
        final({"summary": "Fixed", "changed_files": []}),
        final({"decision": "APPROVED", "summary": "Accepted", "issues": []}),
    ])
    result = Orchestrator(model, [FakeFiles(), FakeTests([failing(), passing()])], max_tool_calls=5,
                          max_coding_attempts=2).run("task")
    assert result.success
    assert result.transitions == ("PLAN", "CODE", "TEST", "REVIEW", "CODE", "TEST", "REVIEW", "DONE")
    assert result.tests[0].success is False and result.tests[1].success is True


def test_orchestrator_enforces_repair_attempt_limit():
    model = ScriptedModel([
        final({"summary": "Plan", "steps": [], "likely_files": []}),
        final({"summary": "First", "changed_files": []}),
        final({"decision": "NEEDS_REVISION", "summary": "Revise", "issues": ["more work"]}),
    ])
    result = Orchestrator(model, [FakeFiles(), FakeTests([passing()])], max_tool_calls=5,
                          max_coding_attempts=1).run("task")
    assert not result.success and result.status == "FAILED"
    assert "Maximum coding attempts" in result.message


def test_orchestrator_enforces_shared_tool_budget():
    model = ScriptedModel([action("list_files"), final({"summary": "Plan", "steps": [], "likely_files": []}),
                           action("write_file", path="x", content="y")])
    result = Orchestrator(model, [FakeFiles(), FakeTests([passing()])], max_tool_calls=1,
                          max_coding_attempts=1).run("task")
    assert not result.success
    assert result.tool_calls == 1


def test_agent_model_failure_becomes_terminal_result():
    model = ScriptedModel([RuntimeError("provider failed")])
    result = Orchestrator(model, [FakeFiles(), FakeTests([])], max_tool_calls=2).run("task")
    assert not result.success and result.status == "FAILED"
    assert "provider failed" in result.message


def test_multi_agent_file_tool_keeps_repository_boundary(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    tools = RepositoryFileTools(repo)
    model = ScriptedModel([action("write_file", path="../outside.txt", content="escape"),
                           final({"summary": "No changes", "changed_files": []})])
    result = Coder(model, ToolExecutor([tools], 5)).run(AgentMessage("Coder", "edit"))
    assert result.success
    assert not outside.exists()


def test_reviewer_failure_is_needs_revision():
    model = ScriptedModel([RuntimeError("unavailable")])
    result = Reviewer(model, ToolExecutor([FakeFiles()], 2)).run(AgentMessage("Reviewer", "task"))
    assert result.decision is ReviewDecision.NEEDS_REVISION


def test_orchestrator_with_real_temporary_repository_and_pytest(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    model = ScriptedModel([final({"summary": "Plan", "steps": [], "likely_files": []}),
                           final({"summary": "No code changes required", "changed_files": []}),
                           final({"decision": "APPROVED", "summary": "Accepted", "issues": []})])
    result = Orchestrator(model, [RepositoryFileTools(tmp_path), PytestTool(tmp_path, timeout_seconds=30)],
                          max_tool_calls=5).run("Review existing test")
    assert result.success
    assert result.tests[0].returncode == 0
