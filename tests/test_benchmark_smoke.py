"""Deterministic C/D machinery smoke; no benchmark tasks or external models."""

import json
from collections import deque
from types import SimpleNamespace

from flagship.benchmark.harness import VARIANTS
from flagship.mcp import MCPToolProvider
from flagship.mcp.tools import encode_tool_result
from flagship.orchestration import Orchestrator
from flagship.repomind import Evidence, RepoMindToolProvider, RetrievalResponse
from flagship.tools import PytestTool, RepositoryFileTools
from flagship.tools.provider import CompositeToolProvider
from flagship.types import AgentDecision, ToolCall, ToolResult


class ScriptedModel:
    def __init__(self, use_retrieval):
        self.use_retrieval = use_retrieval
        self.calls = []
        self.stage = 0

    def next_action(self, task, history, *, instructions=None, allowed_actions=None):
        self.calls.append((task, instructions, allowed_actions))
        if self.stage == 0 and self.use_retrieval:
            self.stage += 1
            return AgentDecision(False, "", ToolCall("repository_action", {
                "action": "search_repository", "repository_id": "00000000-0000-0000-0000-000000000001",
                "query": "find the relevant implementation", "top_k": 2,
            }, "search-1"))
        self.stage += 1
        if self.stage == (2 if self.use_retrieval else 1):
            value = {"summary": "Plan", "steps": ["inspect"], "likely_files": ["src/app.py"]}
        elif self.stage == (3 if self.use_retrieval else 2):
            value = {"summary": "Implemented", "changed_files": []}
        else:
            value = {"decision": "APPROVED", "summary": "Accepted", "issues": []}
        return AgentDecision(True, json.dumps(value))


class FakeMCPClient:
    """MCP client-shaped deterministic transport for sandbox-host independence."""
    def __init__(self, files, tests):
        self.tools = {"list_files": files, "read_file": files, "write_file": files, "run_tests": tests}
        self.calls = []

    def list_tools(self):
        return tuple(self.tools)

    def call_tool(self, name, arguments):
        self.calls.append(name)
        result = self.tools[name].execute({"action": name, **arguments})
        return SimpleNamespace(is_error=False, content=[SimpleNamespace(text=encode_tool_result(result))])


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, repository_id, query, top_k):
        self.calls.append((repository_id, query, top_k))
        evidence = Evidence(repository_id, "doc-1", "chunk-1", "src/app.py", "src/app.py", {},
                            "code", "def target(): return 42", 0.91)
        return RetrievalResponse(repository_id, query, top_k, (evidence,), 2.5)


def test_c_and_d_follow_same_mcp_and_test_path_with_retrieval_only_in_d(tmp_path):
    (tmp_path / "test_pass.py").write_text("def test_pass():\n    assert True\n", encoding="utf-8")
    files = RepositoryFileTools(tmp_path)
    tests = PytestTool(tmp_path, timeout_seconds=30, test_command="python -m pytest -q")
    c_client = FakeMCPClient(files, tests)
    d_client = FakeMCPClient(files, tests)
    c_mcp, d_mcp = MCPToolProvider(c_client), MCPToolProvider(d_client)
    retriever = FakeRetriever()
    repo_id = "00000000-0000-0000-0000-000000000001"
    d_tools = CompositeToolProvider([d_mcp, RepoMindToolProvider(retriever, repo_id)])

    c_model, d_model = ScriptedModel(False), ScriptedModel(True)
    c_result = Orchestrator(c_model, c_mcp, max_tool_calls=10, max_coding_attempts=1,
                            mode="multi-mcp").run("Inspect and fix safely")
    d_result = Orchestrator(d_model, d_tools, max_tool_calls=10, max_coding_attempts=1,
                            mode="multi-mcp-repomind", repository_id=repo_id).run("Inspect and fix safely")

    assert c_result.success and d_result.success
    assert c_client.calls == d_client.calls == ["run_tests"]
    assert c_result.mcp_tool_calls == d_result.mcp_tool_calls == 1
    assert not any("search_repository" in (call[2] or ()) for call in c_model.calls)
    assert len(retriever.calls) == 1
    assert d_result.planner.retrieval_evidence[0]["results"][0]["source_id"] == "src/app.py"
    assert "src/app.py" in d_model.calls[2][0]
    assert c_result.retrieval_latency_ms == 0
    assert d_result.retrieval_latency_ms == 2.5
