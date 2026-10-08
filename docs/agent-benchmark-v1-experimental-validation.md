# Experimental machinery validation (draft; not a benchmark run)

## Scope and outcome

No benchmark task was sent to an LLM, no benchmark run was executed, no RepoMind experiment or implementation was changed, and no task, evaluator, repository revision, reference fix, or corpus file was changed. This is infrastructure validation only. The benchmark remains **DRAFT / NOT FROZEN**.

The deterministic runner tests pass after accepting the manifest's `python -m pytest -q` command and adding schedule/run metadata. The end-to-end C/D orchestration smoke uses a scripted model, a fake MCP client-shaped transport, a real local pytest tool in a temporary repository, and a fake scoped RepoMind retriever. The actual MCP SDK transport could not be validated in this Windows host: constructing its synchronous facade hangs while `asyncio.run` creates the Proactor loop socketpair. The benchmark RepoMind corpus cannot be live-validated because no benchmark repository identity/UUID/pinned ingestion is configured. The only documented live identity is an unrelated FastAPI corpus and was not used.

## C and D execution paths

Both paths start in `BenchmarkHarness.run`: the selected `Variant` supplies the CLI mode; the harness supplies task text, workspace path, test command, model name, shared tool/repair/coding budgets, and timeout. It invokes `python -m flagship.cli run` in the task workspace. CLI creates `RepositoryFileTools`, `PytestTool`, and `OpenAIResponsesModel`; both variants use `Orchestrator` with the same max tool calls and coding attempts.

- **C (`multi-mcp`)**: `Orchestrator` → Planner/Coder/Tester/Reviewer → shared `ToolExecutor` → `MCPToolProvider` → `MCPClient.for_repository` → MCP server wrapping repository file tools and pytest. Planner may list/read; Coder may list/read/write; Tester invokes `run_tests`; Reviewer may inspect. RepoMind is absent.
- **D (`multi-mcp-repomind`)**: same route and role classes, MCP client/server, repository tools, budgets, test command, and model. CLI adds `RepoMindRetriever` and a repository-scoped `RepoMindToolProvider` in a `CompositeToolProvider`; Planner receives the configured repository UUID, an added `search_repository` action, and explicit retrieval instructions. Successful result evidence is serialized in the Planner result passed to Coder. No other role prompt changes.

| Capability/config | C | D | Should differ? |
|---|---|---|---|
| CLI architecture | `multi-mcp` | `multi-mcp-repomind` | Yes, enables RepoMind provider |
| Model class/name and API parameters | `OpenAIResponsesModel`, same configured model | Same | No |
| Task text/workspace/revision/public tests | Harness values | Same | No |
| Planner base instructions | Planner instructions | Same base plus required retrieval instruction | Yes, retrieval capability requires it |
| Planner allowed actions/schema | list/read | list/read/search_repository | Yes, retrieval action |
| Coder/Tester/Reviewer prompts and actions | Shared classes | Same | No |
| MCP server/tools/file and output limits | Same configured server/tool implementations | Same | No |
| Repair/coding/tool budgets and timeout | Shared harness settings | Same | No |
| RepoMind URL and repository UUID | Not passed/used | Required CLI args and environment | Yes |
| Result/telemetry format | Shared | Shared plus retrieval-specific values | No behavior difference intended |

## RepoMind and retrieval semantics

`RepoMindRetriever` calls `POST /query`, explicitly sends repository UUID/query/top-k, validates response and evidence scope/metadata, and records server-reported retrieval latency. `RepoMindToolProvider` rejects missing/invalid/mismatched UUIDs and returns structured failures. HTTP 404 is deliberately interpreted as a successful empty retrieval; transport/timeouts, malformed payloads, invalid metadata, and scope mismatch return failures. Planner evidence is taken only from successful retrieval calls.

The harness distinguishes `not_attempted`, `error`, `partial_error`, `empty`, and `success`; it records retrieval call count, errors, evidence/source IDs, service latency, and per-call wall latency. A successful empty result is distinct from an infrastructure error. MCP call count and wall latency are also recorded.

There is no benchmark RepoMind identity/UUID/pinned revision in the checked-in benchmark config and no `REPOMIND_BASE_URL` or `REPOMIND_REPOSITORY_ID` set in this execution environment. `docs/repomind-live-smoke-test.md` documents UUID `b9e734ef-1538-579f-afce-520e5007a1cc`, identity `repomind-fastapi-clean-v1`, revision `c3f316b7e814667e8ee81e03a7330d00ee61e45c`; that is a FastAPI corpus, not one of the four benchmark repositories. It is not an acceptable substitute. Therefore no live retrieval, benchmark repository UUID/revision match, or evidence quality claim is made.

## MCP and deterministic smoke results

The intended-host command attempted was:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Join-Path (Get-Location).Path 'src')
python -m pytest tests/test_mcp.py -vv --basetemp='<writable-temp>\pytest-validation-mcp'
```

It stalled on the first test, `test_mcp_server_initializes_and_registers_only_expected_tools`. A faulthandler snapshot placed the main thread in Windows `asyncio.ProactorEventLoop._make_self_pipe` → `socket.socketpair` during `asyncio.run` from `MCPClient._run`; it did not reach MCP tool discovery. The run was interrupted. Thus actual SDK startup/discovery/list/read/write/test/path/timeout/error behavior is **not validated in this host**, despite existing tests for those cases. A C-only SDK smoke is likewise blocked at startup.

The deterministic machinery smoke is:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Join-Path (Get-Location).Path 'src')
python -m pytest tests/test_benchmark_smoke.py -q --basetemp='<writable-temp>\pytest-validation-final'
```

It passes. The scripted model drives Orchestrator for C and D; both invoke the same MCP provider-shaped tool route and execute a real passing pytest file in a temporary repository. C makes no retrieval call; D makes one scoped call; D evidence reaches Coder context; both finish the same orchestration path. The fake MCP transport validates adapter/orchestrator composition, **not** actual SDK transport startup.

Focused suite command (54 passed):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Join-Path (Get-Location).Path 'src')
python -m pytest tests/test_benchmark_smoke.py tests/test_shell_tools.py tests/test_benchmark_harness.py tests/test_model.py tests/test_repomind.py tests/test_multi_agent.py -q --basetemp='<writable-temp>\pytest-validation-final'
```

Result: **54 passed**. This suite excludes `tests/test_mcp.py` because its first test stalls as described. It uses no LLM and does not launch any benchmark task.

## Scheduling, repetition, and telemetry

`deterministic_run_schedule(tasks, seed=20261008, repetitions=1)` shuffles task order and uses a seeded permutation of all 24 variant orderings. Each complete 24-task block has every variant at each of the four positions six times. It returns `ScheduledRun` records containing task, variant, repetition, seed, and one-based order index; schedule output is reproducible for the same task list, seed, and repetition count. `deterministic_run_order` remains a compatibility wrapper. Each `BenchmarkHarness.run` creates a UUID run ID unless the caller supplies a shared run ID for the sweep. JSONL writes remain append-only; one serialized record is written per line.

Run records include task/repository/revision/variant, run ID, repetition, seed/order, status/success, public test state, hidden evaluator state, runtime, tool calls, repair attempts, MCP latency/calls, retrieval count/latencies/errors/status/evidence/source IDs, token fields, and failure details. OpenAI Responses `usage` values are accumulated when the provider supplies them and are `null` otherwise; capturing them does not alter action decisions. Unit tests cover deterministic schedule balance/repeatability, repetition/order metadata, append-only JSONL, and mocked usage capture.

## Integrity boundary and blockers

Repository file tools reject path traversal and symlink escapes. Hidden evaluator files are controller-owned and outside task workspaces; they are not passed in CLI arguments or copied into the workspace. However, this is **not an OS sandbox**. The harness inherits the host environment, and `run_tests` launches Python pytest in the agent workspace under the same user. A modified test or package can execute arbitrary Python, inspect inherited environment, and attempt absolute filesystem reads (including controller-owned paths). Repository-root checks constrain the provided file tools, not arbitrary code executed by pytest. Therefore evaluator/reference confidentiality and isolation from host files are **not proven**, and the current arrangement is not ready for untrusted benchmark agent execution. Before any benchmark, run tasks in an OS/container/VM boundary with least-privilege environment and evaluator separation, or use an equivalent enforceable isolation design.

Before freeze: validate the MCP SDK in the actual intended host (including all listed tools and failure/timeout/budget paths); pin and verify a benchmark RepoMind identity, UUID, corpus snapshot revision, and endpoint; prove agent/evaluator filesystem and environment isolation; integrate the schedule metadata into the eventual sweep controller; choose/pin model/provider settings and all shared budgets; then review and explicitly freeze the unchanged corpus. Do not treat the smoke results here as benchmark outcomes.
