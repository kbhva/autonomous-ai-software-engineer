import json
from collections import deque
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from flagship.agents.messages import AgentMessage
from flagship.agents.planner import Planner
from flagship.agents.runtime import ToolExecutor
from flagship.orchestration import Orchestrator
from flagship.repomind import RepoMindError, RepoMindRetriever, RepoMindToolProvider
from flagship.tools.provider import CompositeToolProvider
from flagship.types import AgentDecision, ToolCall, ToolResult


REPO_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
REPO_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def payload(repository_id=REPO_A):
    return {"repository_id": repository_id, "evidence": [
        {"id": "chunk-b", "repository_id": repository_id, "document_id": "doc-2",
         "content": "second", "source_type": "code", "metadata": {"path": "src/b.py", "source_id": "src/b.py"}, "score": 0.8},
        {"id": "chunk-a", "repository_id": repository_id, "document_id": "doc-1",
         "content": "first", "source_type": "doc", "metadata": {"path": "README.md", "source_id": "README.md"}, "score": 0.8},
    ], "metrics": {"retrieval_latency_ms": 12.5}}


class Response:
    def __init__(self, body): self.body = json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self): return self.body


def test_search_forwards_explicit_repository_and_top_k(monkeypatch):
    observed = {}
    def fake_urlopen(request, timeout):
        observed["request"] = request
        observed["timeout"] = timeout
        return Response(payload())
    monkeypatch.setattr("flagship.repomind.urlopen", fake_urlopen)
    result = RepoMindRetriever("http://repomind", 4).search(REPO_A, "where is parser", 2)
    assert json.loads(observed["request"].data) == {"repository_id": REPO_A, "query": "where is parser", "top_k": 2}
    assert observed["timeout"] == 4
    assert result.repository_id == REPO_A and result.top_k == 2


def test_provider_requires_repository_id_without_default(monkeypatch):
    retriever = RepoMindRetriever("http://repomind")
    provider = RepoMindToolProvider(retriever)
    result = provider.execute("search_repository", {"query": "find parser"})
    assert not result.success
    assert result.data["error_code"] == "missing_repository_id"


@pytest.mark.parametrize("repository_id", ["", None, "not-a-uuid"])
def test_provider_rejects_missing_or_invalid_repository_id(repository_id):
    provider = RepoMindToolProvider(RepoMindRetriever("http://repomind"))
    result = provider.execute("search_repository", {"repository_id": repository_id, "query": "find parser"})
    assert not result.success
    assert result.data["error_code"] in {"missing_repository_id", "invalid_repository_id"}


def test_query_and_top_k_validation_happens_before_network(monkeypatch):
    def unexpected(*_args, **_kwargs): raise AssertionError("network must not be called")
    monkeypatch.setattr("flagship.repomind.urlopen", unexpected)
    provider = RepoMindToolProvider(RepoMindRetriever("http://repomind"))
    assert provider.execute("search_repository", {"repository_id": REPO_A, "query": "  "}).data["error_code"] == "invalid_query"
    assert provider.execute("search_repository", {"repository_id": REPO_A, "query": "find parser", "top_k": 51}).data["error_code"] == "invalid_top_k"


def test_evidence_conversion_preserves_metadata_scope_and_latency(monkeypatch):
    monkeypatch.setattr("flagship.repomind.urlopen", lambda *_args, **_kwargs: Response(payload()))
    result = RepoMindToolProvider(RepoMindRetriever("http://repomind")).execute(
        "search_repository", {"repository_id": REPO_A, "query": "find parser", "top_k": 2})
    assert result.success
    assert result.data["retrieval_latency_ms"] == 12.5
    assert [item["chunk_id"] for item in result.data["results"]] == ["chunk-a", "chunk-b"]
    evidence = result.data["results"][0]
    assert evidence == {"repository_id": REPO_A, "document_id": "doc-1", "chunk_id": "chunk-a",
                        "source_id": "README.md", "path": "README.md",
                        "metadata": {"path": "README.md", "source_id": "README.md"}, "source_type": "doc",
                        "text": "first", "score": 0.8, "source_range": None}


def test_provider_reports_repo_failure_structurally(monkeypatch):
    def fail(*_args, **_kwargs): raise URLError("secret database hostname")
    monkeypatch.setattr("flagship.repomind.urlopen", fail)
    result = RepoMindToolProvider(RepoMindRetriever("http://repomind")).execute(
        "search_repository", {"repository_id": REPO_A, "query": "find parser"})
    assert not result.success
    assert result.data == {"error_code": "repomind_unavailable", "retryable": True}
    assert "secret" not in result.error


def test_http_404_maps_to_empty_success(monkeypatch):
    def no_evidence(*_args, **_kwargs):
        raise HTTPError("http://repomind/query", 404, "missing", {}, BytesIO(b""))
    monkeypatch.setattr("flagship.repomind.urlopen", no_evidence)
    result = RepoMindToolProvider(RepoMindRetriever("http://repomind")).execute(
        "search_repository", {"repository_id": REPO_A, "query": "find parser"})
    assert result.success and result.data["results"] == []


def test_repository_b_never_receives_repository_a_evidence(monkeypatch):
    monkeypatch.setattr("flagship.repomind.urlopen", lambda *_args, **_kwargs: Response(payload(REPO_A)))
    result = RepoMindToolProvider(RepoMindRetriever("http://repomind")).execute(
        "search_repository", {"repository_id": REPO_B, "query": "find parser"})
    assert not result.success
    assert result.data["error_code"] == "repository_scope_mismatch"


class ScriptedModel:
    def __init__(self, decisions): self.decisions = deque(decisions); self.calls = []
    def next_action(self, task, history, *, instructions=None, allowed_actions=None):
        self.calls.append((instructions, allowed_actions))
        return self.decisions.popleft()


def call(action, **kwargs):
    return AgentDecision(False, "", ToolCall("repository_action", {"action": action, **kwargs}, "call-1"))


def final(value): return AgentDecision(True, json.dumps(value))


def test_planner_can_retrieve_and_passes_evidence_to_plan(monkeypatch):
    monkeypatch.setattr("flagship.repomind.urlopen", lambda *_args, **_kwargs: Response(payload()))
    provider = RepoMindToolProvider(RepoMindRetriever("http://repomind"), REPO_A)
    model = ScriptedModel([call("search_repository", repository_id=REPO_A, query="find parser", top_k=2),
                           final({"summary": "Use parser context", "steps": ["edit parser"], "likely_files": ["src/parser.py"]})])
    result = Planner(model, ToolExecutor(provider, 4), REPO_A).run(AgentMessage("Planner", "fix parser"))
    assert result.success and result.retrieval_evidence[0]["results"][0]["chunk_id"] == "chunk-a"
    assert "search_repository" in model.calls[0][1]


def test_composite_provider_routes_mcp_and_retrieval_and_separates_timing(monkeypatch):
    monkeypatch.setattr("flagship.repomind.urlopen", lambda *_args, **_kwargs: Response(payload()))
    class MCPProvider:
        provider_name = "mcp"
        actions = ("list_files",)
        def execute(self, action, arguments): return ToolResult(action, True, "listed", {})
    composite = CompositeToolProvider([MCPProvider(), RepoMindToolProvider(RepoMindRetriever("http://repomind"))])
    executor = ToolExecutor(composite, 4)
    evidence = executor.execute("search_repository", {"repository_id": REPO_A, "query": "find parser"}, ("search_repository",))
    listed = executor.execute("list_files", {}, ("list_files",))
    assert evidence.success and listed.success
    assert executor.retrieval_latency_ms == 12.5
    assert executor.tool_latency_ms >= 0
    assert executor.audit[0].provider == "repomind" and executor.audit[1].provider == "mcp"
