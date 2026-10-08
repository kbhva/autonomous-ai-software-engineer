"""Thin client and ToolProvider adapter for RepoMind's existing HTTP API."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from flagship.types import ToolResult


@dataclass(frozen=True)
class Evidence:
    repository_id: str
    document_id: str
    chunk_id: str
    source_id: str | None
    path: str | None
    metadata: dict[str, Any]
    source_type: str
    text: str
    score: float
    source_range: dict[str, int] | None = None


@dataclass(frozen=True)
class RetrievalResponse:
    repository_id: str
    query: str
    top_k: int
    results: tuple[Evidence, ...]
    retrieval_latency_ms: float


class RepoMindError(Exception):
    """Safe, structured error at the RepoMind adapter boundary."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class RepoMindRetriever:
    """Calls RepoMind's repository-scoped POST /query endpoint."""

    def __init__(self, base_url: str, timeout_seconds: float = 15.0):
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("RepoMind base URL is required")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("RepoMind timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def search(self, repository_id: str, query: str, top_k: int = 5) -> RetrievalResponse:
        repo_id = _validate_repository_id(repository_id)
        if not isinstance(query, str) or not query.strip():
            raise RepoMindError("invalid_query", "query must not be empty")
        query = query.strip()
        if len(query) < 3:
            raise RepoMindError("invalid_query", "query must contain at least 3 characters")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 50:
            raise RepoMindError("invalid_top_k", "top_k must be an integer from 1 to 50")

        request = Request(
            f"{self.base_url}/query",
            data=json.dumps({"repository_id": repo_id, "query": query, "top_k": top_k}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # RepoMind currently represents a valid empty retrieval as HTTP 404.
            if exc.code == 404:
                payload = {"repository_id": repo_id, "query": query, "evidence": [], "metrics": {}}
            elif exc.code in (502, 503, 504):
                raise RepoMindError("repository_unavailable", "RepoMind retrieval service is unavailable", retryable=True) from None
            elif exc.code == 422:
                raise RepoMindError("invalid_request", "RepoMind rejected the retrieval request") from None
            else:
                raise RepoMindError("embedding_or_retrieval_failed", "RepoMind could not complete retrieval", retryable=exc.code >= 500) from None
        except (URLError, TimeoutError, OSError):
            raise RepoMindError("repomind_unavailable", "Could not connect to RepoMind", retryable=True) from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RepoMindError("invalid_response", "RepoMind returned an invalid response", retryable=True) from None

        if not isinstance(payload, dict):
            raise RepoMindError("invalid_response", "RepoMind returned an invalid response")
        response_repo_id = payload.get("repository_id")
        if response_repo_id is not None and _validate_repository_id(response_repo_id) != repo_id:
            raise RepoMindError("repository_scope_mismatch", "RepoMind response did not match the requested repository")
        raw_evidence = payload.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raise RepoMindError("invalid_response", "RepoMind returned invalid evidence")
        evidence = tuple(_convert_evidence(item, repo_id) for item in raw_evidence)
        # Stable local ordering for equal scores; repository filtering and ranking
        # themselves remain inside RepoMind's existing retrieval implementation.
        evidence = tuple(sorted(evidence, key=lambda item: (-item.score, item.chunk_id))[:top_k])
        metrics = payload.get("metrics") or {}
        latency = metrics.get("retrieval_latency_ms", 0.0) if isinstance(metrics, dict) else 0.0
        if isinstance(latency, bool) or not isinstance(latency, (int, float)) or not math.isfinite(latency) or latency < 0:
            raise RepoMindError("invalid_response", "RepoMind returned invalid retrieval timing")
        return RetrievalResponse(repo_id, query, top_k, evidence, float(latency))


class RepoMindToolProvider:
    """Expose RepoMind search through the flagship's provider protocol."""

    provider_name = "repomind"
    actions = ("search_repository",)

    def __init__(self, retriever: RepoMindRetriever, expected_repository_id: str | None = None):
        self.retriever = retriever
        self.expected_repository_id = (
            _validate_repository_id(expected_repository_id) if expected_repository_id is not None else None
        )

    def execute(self, action: str, arguments: dict[str, Any]) -> ToolResult:
        if action != "search_repository":
            return ToolResult(action, False, "Unsupported RepoMind action", error=f"Unknown action: {action}")
        try:
            if not isinstance(arguments, dict):
                raise RepoMindError("invalid_request", "Tool arguments must be an object")
            # Never infer scope from provider configuration, process state, or prior calls.
            repository_id = _validate_repository_id(arguments.get("repository_id"))
            if self.expected_repository_id and repository_id != self.expected_repository_id:
                raise RepoMindError("repository_scope_mismatch", "repository_id does not match the explicitly configured scope")
            response = self.retriever.search(repository_id, arguments.get("query"), arguments.get("top_k", 5))
            data = {
                "repository_id": response.repository_id,
                "query": response.query,
                "top_k": response.top_k,
                "results": [item.__dict__ for item in response.results],
                "retrieval_latency_ms": response.retrieval_latency_ms,
            }
            return ToolResult(action, True, f"Retrieved {len(response.results)} evidence item(s)", data)
        except RepoMindError as exc:
            return ToolResult(action, False, "RepoMind retrieval failed",
                              {"error_code": exc.code, "retryable": exc.retryable}, str(exc))
        except Exception:
            # Keep provider-specific transport/parser failures safe for model history
            # and audit output; never serialize URLs, response bodies, or credentials.
            return ToolResult(action, False, "RepoMind retrieval failed",
                              {"error_code": "embedding_or_retrieval_failed", "retryable": True},
                              "RepoMind could not complete retrieval")


def _validate_repository_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RepoMindError("missing_repository_id", "repository_id is required")
    try:
        return str(UUID(value.strip()))
    except (ValueError, AttributeError):
        raise RepoMindError("invalid_repository_id", "repository_id must be a valid UUID") from None


def _convert_evidence(item: Any, expected_repository_id: str) -> Evidence:
    if not isinstance(item, dict):
        raise RepoMindError("invalid_response", "RepoMind returned invalid evidence")
    repo_id = _validate_repository_id(item.get("repository_id", expected_repository_id))
    if repo_id != expected_repository_id:
        raise RepoMindError("repository_scope_mismatch", "RepoMind returned evidence outside the requested repository")
    metadata = item.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise RepoMindError("invalid_response", "RepoMind returned invalid evidence metadata")
    score = item.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
        raise RepoMindError("invalid_response", "RepoMind returned an invalid evidence score")
    chunk_id, document_id = item.get("id", item.get("chunk_id")), item.get("document_id")
    source_type, text = item.get("source_type"), item.get("content", item.get("text"))
    if not all(isinstance(value, str) and value for value in (chunk_id, document_id, source_type)) or not isinstance(text, str):
        raise RepoMindError("invalid_response", "RepoMind returned incomplete evidence")
    path = metadata.get("path")
    source_id = metadata.get("source_id")
    if path is not None and not isinstance(path, str) or source_id is not None and not isinstance(source_id, str):
        raise RepoMindError("invalid_response", "RepoMind returned invalid source metadata")
    return Evidence(repo_id, document_id, chunk_id, source_id, path, dict(metadata), source_type, text, float(score), None)
