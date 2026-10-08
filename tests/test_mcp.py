import io
import json
import subprocess
from collections import deque

from flagship.agents.messages import ReviewDecision
from flagship.mcp import MCPClient, MCPToolProvider
from flagship.orchestration import Orchestrator
from flagship.tools import PytestTool, RepositoryFileTools
from flagship.tools.shell import MAX_OUTPUT_CHARS
from flagship.types import AgentDecision, ToolCall


def provider_for(root, timeout=30):
    client = MCPClient.for_repository(root, test_timeout=timeout)
    return client, MCPToolProvider(client)


def call(model_action, **arguments):
    return AgentDecision(False, "", ToolCall("repository_action", {"action": model_action, **arguments}, "mcp-call"))


def test_mcp_server_initializes_and_registers_only_expected_tools(tmp_path):
    client, _ = provider_for(tmp_path)
    assert set(client.list_tools()) == {"list_files", "read_file", "write_file", "run_tests"}


def test_list_files_through_mcp(tmp_path):
    (tmp_path / "a.py").write_text("x=1", encoding="utf-8")
    _, provider = provider_for(tmp_path)
    result = provider.execute("list_files", {})
    assert result.success and result.data["files"] == ["a.py"]


def test_read_file_through_mcp(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    _, provider = provider_for(tmp_path)
    result = provider.execute("read_file", {"path": "a.txt"})
    assert result.success and result.data["content"] == "hello"


def test_write_file_through_mcp(tmp_path):
    _, provider = provider_for(tmp_path)
    result = provider.execute("write_file", {"path": "new.txt", "content": "MCP"})
    assert result.success and (tmp_path / "new.txt").read_text(encoding="utf-8") == "MCP"


def test_run_tests_through_mcp(tmp_path):
    (tmp_path / "test_pass.py").write_text("def test_pass():\n    assert True\n", encoding="utf-8")
    _, provider = provider_for(tmp_path)
    result = provider.execute("run_tests", {"args": ["-q"]})
    assert result.success and result.data["returncode"] == 0


def test_path_traversal_and_write_escape_blocked_through_mcp(tmp_path):
    root, outside = tmp_path / "repo", tmp_path / "outside.txt"
    root.mkdir()
    _, provider = provider_for(root)
    read_result = provider.execute("read_file", {"path": "../outside.txt"})
    write_result = provider.execute("write_file", {"path": "../outside.txt", "content": "bad"})
    assert not read_result.success and not write_result.success
    assert not outside.exists()


def test_symlink_escape_blocked_through_mcp(tmp_path):
    root, outside = tmp_path / "repo", tmp_path / "outside"
    root.mkdir(); outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (root / "escape").symlink_to(outside, target_is_directory=True)
    _, provider = provider_for(root)
    result = provider.execute("read_file", {"path": "escape/secret.txt"})
    assert not result.success


def test_arbitrary_shell_command_is_not_an_mcp_tool(tmp_path):
    client, provider = provider_for(tmp_path)
    result = provider.execute("run_command", {"command": "whoami"})
    assert not result.success
    assert set(client.list_tools()) == set(provider.actions)


def test_pytest_timeout_is_preserved_through_mcp(tmp_path, monkeypatch):
    class Process:
        stdout = io.BytesIO(b"partial")
        stderr = io.BytesIO(b"stuck")
        returncode = -9
        def wait(self, timeout=None):
            if timeout is not None: raise subprocess.TimeoutExpired("pytest", timeout)
        def kill(self): pass
    monkeypatch.setattr("flagship.tools.shell.subprocess.Popen", lambda *a, **kw: Process())
    _, provider = provider_for(tmp_path, timeout=1)
    result = provider.execute("run_tests", {})
    assert not result.success and result.data["timed_out"]


def test_bounded_output_is_preserved_through_mcp(tmp_path, monkeypatch):
    class Process:
        returncode = 1
        stdout = io.BytesIO(b"x" * (MAX_OUTPUT_CHARS + 1))
        stderr = io.BytesIO(b"y" * (MAX_OUTPUT_CHARS + 1))
        def wait(self, timeout=None): return self.returncode
    monkeypatch.setattr("flagship.tools.shell.subprocess.Popen", lambda *a, **kw: Process())
    _, provider = provider_for(tmp_path)
    result = provider.execute("run_tests", {})
    assert not result.success and result.data["output_truncated"]
    assert len(result.data["stdout"]) == MAX_OUTPUT_CHARS


def test_mcp_error_handling_returns_structured_failure(tmp_path, monkeypatch):
    client, provider = provider_for(tmp_path)
    async def fail_call_tool(name, arguments):
        raise RuntimeError("connection lost")
    monkeypatch.setattr(client, "_call_tool", fail_call_tool)
    result = provider.execute("list_files", {})
    assert not result.success and result.error.startswith("RuntimeError:")


class ScriptedModel:
    def __init__(self, actions): self.actions = deque(actions)
    def next_action(self, task, history, *, instructions=None, allowed_actions=None):
        return self.actions.popleft()


def final(value): return AgentDecision(True, json.dumps(value))


def test_multi_mcp_orchestrator_executes_every_tool_via_mcp(tmp_path):
    model = ScriptedModel([
        call("list_files"), final({"summary": "Plan", "steps": ["add test"], "likely_files": ["test_added.py"]}),
        call("write_file", path="test_added.py", content="def test_added():\n    assert 1 == 1\n"),
        final({"summary": "Added test", "changed_files": ["test_added.py"]}),
        call("read_file", path="test_added.py"),
        final({"decision": "APPROVED", "summary": "Accepted", "issues": []}),
    ])
    provider = MCPToolProvider(MCPClient.for_repository(tmp_path, test_timeout=30))
    result = Orchestrator(model, provider, max_tool_calls=10, max_coding_attempts=2,
                          mode="multi-mcp").run("Add a passing test")
    assert result.success and result.mode == "multi-mcp"
    assert result.mcp_tool_calls == result.tool_calls == 4
    assert all(entry.provider == "mcp" for entry in result.audit)
    assert result.tool_latency_ms >= 0
    assert result.tool_errors == 0


def test_mcp_tool_call_budget_is_enforced(tmp_path):
    model = ScriptedModel([call("list_files"), final({"summary": "Plan", "steps": [], "likely_files": []}),
                           final({"summary": "No code changes", "changed_files": []}),
                           final({"decision": "APPROVED", "summary": "Review", "issues": []})])
    provider = MCPToolProvider(MCPClient.for_repository(tmp_path))
    result = Orchestrator(model, provider, max_tool_calls=1, max_coding_attempts=1,
                          mode="multi-mcp").run("Check repository")
    assert not result.success
    assert result.tool_calls == result.mcp_tool_calls == 1


def test_direct_orchestrator_regression_does_not_use_mcp(tmp_path):
    model = ScriptedModel([final({"summary": "Plan", "steps": [], "likely_files": []}),
                           final({"summary": "No changes", "changed_files": []}),
                           final({"decision": "APPROVED", "summary": "Accepted", "issues": []})])
    class GoodTests:
        actions = ("run_tests",)
        def execute(self, arguments):
            from flagship.types import ToolResult
            return ToolResult("run_tests", True, "passed", {"returncode": 0})
    result = Orchestrator(model, [RepositoryFileTools(tmp_path), GoodTests()], 4).run("task")
    assert result.success and result.mode == "multi" and result.mcp_tool_calls == 0
