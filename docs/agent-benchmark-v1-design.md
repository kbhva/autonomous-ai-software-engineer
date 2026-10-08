# End-to-end agent benchmark v1 — preparation design

**Status: preparation only. No agent benchmark tasks have been run.** This document does not freeze the task set; repository candidates and tasks still require review and revision pinning before a manifest can be frozen.

## Question and scope

Measure whether repository-aware retrieval changes objective coding-task success for the existing flagship. Compare four existing CLI modes while holding task text, repository revision, model, model parameters, tool-call budget, repair budget, test timeout, setup, and test command fixed. The evaluator is the task's specified pytest command and its exit status; Reviewer approval is recorded but is not success evidence.

The completed retrieval benchmark is background only. Its results are not used to select tasks, tune prompts, or tune RepoMind.

## Repository candidates (not cloned or pinned by this preparation)

The following public, Python-first projects are candidate snapshots. They have `pyproject.toml`-based configuration and local pytest suites. Their revisions, exact tracked-file counts, test dependency closure, and clean baseline test results must be measured after the candidate set is approved. Do not use floating branches in the frozen manifest.

| Candidate | Source | Language / framework | Approximate tracked size | Test command / setup | Why it may fit |
|---|---|---|---:|---|---|
| Click | [pallets/click](https://github.com/pallets/click) | Python; CLI framework | Small/medium, roughly a few hundred project files | `python -m pytest`; install the pinned snapshot with its test dependency group | Focused modules, CLI behavior, decorators, parsing and formatting offer objective single-/multi-file changes. Its pytest configuration excludes stress tests by default. |
| ItsDangerous | [pallets/itsdangerous](https://github.com/pallets/itsdangerous) | Python; signing/serialization library | Small, roughly under 100 project files | `python -m pytest`; install snapshot and its test extra | Compact source/test tree and deterministic signing, serialization, and compatibility behavior. |
| attrs | [python-attrs/attrs](https://github.com/python-attrs/attrs) | Python; data-class/validation library | Medium, roughly a few hundred project files | `python -m pytest`; install test dependency group (notably Hypothesis) | Cross-file API and validation behavior with a substantial local test suite and no runtime service. |
| Packaging | [pypa/packaging](https://github.com/pypa/packaging) | Python; packaging specification library | Small/medium, roughly a few hundred project files | `python -m pytest`; install pinned test extras | Version/specifier/marker parsing and normalization are deterministic and well suited to regression and missing-function tasks. |

These file-count bands are planning estimates, not measured counts. Source references support the existence/configuration and pytest basis of these candidates: [Click project configuration](https://github.com/pallets/click/blob/main/pyproject.toml), [ItsDangerous repository](https://github.com/pallets/itsdangerous), [attrs project configuration](https://github.com/python-attrs/attrs/blob/main/pyproject.toml), and [Packaging project](https://github.com/pypa/packaging). Exact metadata belongs in the frozen repository manifest after checkout inspection.

### Candidate selection risks

- Click and ItsDangerous share the Pallets ecosystem; include both only if candidate tasks remain distinct and do not rely on cross-repository knowledge.
- attrs tests use Hypothesis and other test tools; pin a known dependency lock/setup and cache it outside run workspaces.
- Requests was considered but not shortlisted because its suite includes HTTP/server and certificate-related test dependencies that increase setup variability.
- No repository has been cloned for this preparation, and no candidate suitability claim is based on running its tests.

## Proposed task corpus

Propose **24 tasks across four repositories, six tasks per repository** after candidates are selected and baseline tests are verified. Balance these categories across repositories rather than allocating one category to one repository:

1. single-file bug fix
2. multi-file bug fix
3. missing function implementation
4. API or behavior change
5. configuration/dependency change
6. cross-file dependency change
7. test-driven regression fix
8. small feature addition
9. repository-understanding task with testable output

Tasks must be phrased from observable requirements and checked against tests added outside the agent workspace or existing required tests. Do not put a patch outline or expected solution in prompts. A task whose only success signal is Reviewer judgement is ineligible. At least one baseline test should fail for each code-changing task; no-op/understanding tasks need an explicit deterministic assertion instead.

Before freeze, each candidate snapshot needs: exact commit, clean initial checkout, Python/runtime version, install command and resolved dependencies, baseline test command/result, file count, test count, and test timeout. The 24 task descriptions and all setup/test commands are then written to one immutable JSON manifest and hashed by exact file bytes.

## Variants

The current CLI already exposes all four variants; no agent architecture change is proposed.

| Variant | Existing CLI mode | Intended capability |
|---|---|---|
| A — Single agent | `single` | One coding agent, direct repository tools, pytest and its existing repair loop. |
| B — Multi-agent | `multi` | Planner, Coder, Tester, Reviewer with direct repository tools. |
| C — Multi-agent + MCP | `multi-mcp` | Same multi-agent flow, with repository tools accessed through the local MCP client/server. |
| D — Multi-agent + MCP + RepoMind | `multi-mcp-repomind` | Same as C with repository-scoped RepoMind retrieval available to Planner. |

Model name/provider/API settings, task prompt, initial commit, dependency environment, top-level wall timeout, pytest timeout, `FLAGSHIP_MAX_TOOL_CALLS`, and repair/coding-attempt budget are common and stored in the frozen run manifest. Only mode/capability differs. Variant D is indexed once per repository snapshot before task execution; every task run still receives its own isolated working checkout. The RepoMind corpus revision and ingestion identity are recorded.

## Task manifest schema

One JSON object with schema version, frozen timestamp, repository table, run configuration, and ordered `tasks` array. A task entry contains:

```json
{
  "task_id": "CLICK-001",
  "repository_id": "click",
  "repository_revision": "<full immutable commit SHA>",
  "task_category": "single_file_bug_fix",
  "task_description": "Observable requirement only; no expected patch or implementation hint.",
  "test_command": "python -m pytest -q tests/...",
  "timeout_seconds": 600,
  "expected_evaluation_method": "pytest_exit_code_zero",
  "setup_requirements": ["install the frozen environment identified in repository metadata"],
  "difficulty": "medium"
}
```

`repository_source` is recorded in the repository table and resolved to a local immutable mirror for execution. Task ordering is the manifest order. Duplicate task IDs, floating revisions, non-pytest commands, and missing required fields are rejected.

## Metrics and result record

The harness records one row for every `(task_id, variant)` even if checkout, model invocation, timeout, test, or retrieval fails:

- identity: task, repo, exact revision, variant, and task-manifest SHA-256
- outcome: status, objective success, final required-test status, failure class/reason
- effort: repair attempts, tool calls, wall-clock seconds
- usage: input/output/total tokens when returned by provider; otherwise JSON `null`
- D-only retrieval: retrieval calls, aggregate retrieval latency, errors, and evidence count/source IDs when exposed by the existing result contract
- subprocess exit code and bounded stdout/stderr excerpt for diagnosis

Primary success is `final required pytest command exit code == 0` after the agent finishes. Separate statuses include pass, targeted-only pass (if a task explicitly distinguishes target vs required suite), test failure, invalid/no agent result, timeout, tool error, retrieval error, and model/API error. Review output does not override tests.

Current CLI JSON does not expose model token usage, so token counts remain JSON `null`. The multi-agent RepoMind result does serialize Planner retrieval evidence; the harness extracts evidence-row count and distinct source IDs from that existing result. Token accounting remains an explicit pre-benchmark telemetry gap; resolving it must not change agent decisions or retrieval behavior.

## Isolation and order

Use a read-only local bare mirror per selected upstream repository. For each `(task, variant)`, clone independently with hardlink sharing disabled, checkout the full pinned SHA detached, verify the SHA and clean status, install from a prebuilt immutable environment/cache, and execute only in that workspace. Never reuse a variant workspace, use successful output as a starting point, or cherry-pick/copy files between variants. The same task object/string and test command are passed to all four variants.

Run order is deterministic: manifest task order, then A/B/C/D. Store every run row append-only immediately after completion; an interrupted experiment is marked incomplete and is not silently resumed as though it were a fresh run. Each variant gets the same total wall timeout and agent budgets. The model provider API key is inherited from a secret environment and never written to manifests, logs, command lines, or results.

For D, ingest each pinned repository revision once into a fresh isolated RepoMind corpus before tasks; record identity key/UUID, index statistics and configuration. Retrieval is available only in D. Do not use the FastAPI retrieval benchmark corpus. Retrieval service latency is included in D wall time and separately recorded if exposed.

## Harness implementation and deterministic checks

`src/flagship/benchmark/harness.py` implements task validation and exact manifest hashing, fixed variant definitions/order, fresh detached clone creation with revision/clean-state checks, subprocess wall timeouts, common model/tool/repair/test configuration, structured failure records, usage/retrieval fields (null when unavailable), and append-only JSONL output. `tests/test_benchmark_harness.py` exercises it with fake process and Git runners; these are harness-only tests and do not call OpenAI or run benchmark tasks.

The manifest is **not frozen**. Before actual execution, select/reject candidates, measure exact revisions/file and test counts, create the 24 task records and objective assertions, pin setup/runtime, close telemetry gaps, review all prompts/labels, and hash the finalized manifest. No agent benchmark is authorized by this preparation.
