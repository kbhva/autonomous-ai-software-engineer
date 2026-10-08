"""Opt-in smoke test against a separately validated RepoMind service."""

import os
import json

import pytest

from flagship.repomind import RepoMindRetriever, RepoMindToolProvider


REQUIRED = ("REPOMIND_LIVE_TESTS", "REPOMIND_BASE_URL", "REPOMIND_REPOSITORY_ID", "REPOMIND_SMOKE_QUERY")
pytestmark = pytest.mark.skipif(
    not all(os.getenv(name) for name in REQUIRED) or os.getenv("REPOMIND_LIVE_TESTS") != "1",
    reason="Set REPOMIND_LIVE_TESTS=1 and all RepoMind smoke-test settings to run",
)


def test_live_repomind_scoped_query():
    repository_id = os.environ["REPOMIND_REPOSITORY_ID"].lower()
    query = os.environ["REPOMIND_SMOKE_QUERY"].strip()
    provider = RepoMindToolProvider(
        RepoMindRetriever(os.environ["REPOMIND_BASE_URL"]),
        expected_repository_id=repository_id,
    )
    result = provider.execute("search_repository", {
        "repository_id": repository_id,
        "query": query,
        "top_k": 3,
    })

    assert result.success, result.to_dict()
    assert result.tool == "search_repository"
    assert result.data["repository_id"] == repository_id
    assert result.data["query"] == query
    assert result.data["top_k"] == 3
    assert result.data["retrieval_latency_ms"] >= 0
    evidence = result.data["results"]
    assert evidence, "Expected indexed evidence for the pinned FastAPI repository"
    expected_source = [item for item in evidence
                       if (item["path"] or "").replace("\\", "/") == "fastapi/exceptions.py"]
    assert expected_source, "Expected FastAPIError evidence from fastapi/exceptions.py"
    assert any("class FastAPIError" in item["text"] and "RuntimeError" in item["text"]
               for item in expected_source)
    assert all(item["repository_id"] == repository_id for item in evidence)
    assert all(item["document_id"] and item["chunk_id"] for item in evidence)
    assert all(item["score"] is not None and item["source_range"] is None for item in evidence)

    # The configured provider scope rejects a second repository before making
    # any HTTP request, so evidence from the indexed FastAPI scope cannot leak.
    other_repository_id = "00000000-0000-4000-8000-000000000001"
    negative = provider.execute("search_repository", {
        "repository_id": other_repository_id,
        "query": query,
        "top_k": 3,
    })
    assert not negative.success
    assert negative.data["error_code"] == "repository_scope_mismatch"

    print(json.dumps({
        "repository_id": result.data["repository_id"],
        "query": result.data["query"],
        "top_k": result.data["top_k"],
        "retrieval_latency_ms": result.data["retrieval_latency_ms"],
        "evidence": [{key: item[key] for key in (
            "document_id", "chunk_id", "source_id", "path", "source_type", "score"
        )} for item in evidence],
        "negative_scope_error": negative.data["error_code"],
    }, sort_keys=True))
