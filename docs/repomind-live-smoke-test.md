# RepoMind Live Smoke Test

## Environment

- RepoMind ran through its existing FastAPI application on `127.0.0.1:18765`.
- PostgreSQL `17.11` used the existing `pgvector/pgvector:pg17` image. RepoMind startup enabled the `vector` extension.
- The database ran in a temporary container bound only to localhost port `55432`, with tmpfs storage and no persistent volume.
- RepoMind used its configured `sentence-transformers/all-MiniLM-L6-v2` model, already cached locally. Ingestion loaded the model on CUDA.
- The server process used a process-local database URL override pointing to the isolated container. No database credentials or API keys are recorded here.

## Repository Snapshot

- Configured repository identity: `repomind-fastapi-clean-v1`
- Effective repository UUID: `b9e734ef-1538-579f-afce-520e5007a1cc`
- Snapshot commit: `c3f316b7e814667e8ee81e03a7330d00ee61e45c`
- The temporary checkout was made from that commit only. The existing FastAPI checkout, including its unrelated untracked file, was left untouched.
- Existing RepoMind AST ingestion completed with 2,877 files, 15,374 chunks created, 250 recent Git commits, zero failed items, and zero skipped items. RepoMind reported the same repository UUID and commit hash.

Smoke query used for the flagship provider check:

> Where is the FastAPIError class defined and what class does it inherit from?

The expected repository fact is `FastAPIError(RuntimeError)` in `fastapi/exceptions.py`.

## Direct RepoMind Check

Before calling the flagship provider, one direct `POST /query` returned HTTP 200 for the pinned repository UUID with three evidence items. The top result was `docs/en/docs/reference/index.md` (document `211ca209-c9fb-4e1d-90c8-9af661d38abb`, chunk `01632c99-cae8-559c-a358-d40fc2afb21e`, score `0.6962`). Other results included `fastapi/exceptions.py` and one commit source. RepoMind reported `6593.62 ms` retrieval latency for this direct call.

This confirms the live RepoMind HTTP, PostgreSQL, pgvector, and embedding/retrieval path. It is a single smoke query, not a benchmark.

## Flagship Provider Check

The existing opt-in test was updated to call `RepoMindToolProvider.execute("search_repository", ...)`. It does not call `RepoMindRetriever` directly. The request included the explicit repository UUID, the query above, and `top_k=3`. The returned `ToolResult` succeeded and preserved the query, repository UUID, top-k, service retrieval latency, source metadata, scores, document IDs, and chunk IDs. `source_range` remained null.

The top result was code evidence from `fastapi/exceptions.py`: document `55d0ae1d-2202-4bbf-8833-d8b14b1697a7`, chunk `e777c45c-e604-5815-87f6-a4ffe508031d`, score `0.7343`. Its retrieved text contained the expected `FastAPIError` class and `RuntimeError` base. RepoMind reported `66.81 ms` for this call; this is an observed smoke-test value, not a performance claim.

The live test command completed with **1 passed**.

## Negative Scope Check

The same provider was configured for the pinned FastAPI UUID, then called with `00000000-0000-4000-8000-000000000001`. It returned a structured `repository_scope_mismatch` failure and no evidence. The provider rejected the mismatched scope before making another HTTP request.

## Optional Agent Check

Skipped. `OPENAI_API_KEY` was not configured and the OpenAI SDK was not installed in the active environment. Setting up a model runtime and making a paid model call was beyond this provider smoke test.

## Test Suite

- Flagship complete suite: **58 passed, 1 skipped, 0 failed**. The skipped test is the opt-in live test when its environment variables are absent; it was then run separately against the live service and passed.
- RepoMind suite: **35 passed, 0 failed**.
- No benchmark, Recall@K/MRR/nDCG run, or agent comparison was performed.

## Cleanup

- Stopped and removed the temporary PostgreSQL container. It used tmpfs-only storage; no database volume was created or retained.
- Stopped the RepoMind server process.
- Removed the temporary FastAPI checkout, server logs, and pytest scratch directories created for this run.
- Left the original FastAPI checkout, RepoMind source/configuration, evaluation labels/results, and CodeAgent-MCP untouched.

## Limitations

- This validates one direct retrieval and one flagship provider retrieval against one indexed repository snapshot. It does not establish retrieval quality or benchmark performance.
- The optional Planner/Coder/Tester/Reviewer model-driven path was not run.
- The current RepoMind API does not expose source ranges, so the adapter correctly returns null ranges. The API also does not authenticate callers; this test bound it to loopback only.
- The negative scope check verifies the flagship provider's configured-scope enforcement before the HTTP boundary; it is not an independent database-level cross-repository penetration test.
