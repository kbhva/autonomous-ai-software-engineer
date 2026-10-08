# Agent benchmark v1 — controlled local design (draft)

> **DRAFT — NOT FROZEN. No coding-agent benchmark has been run and no task has been sent to an LLM.**

> **Public release note:** The four synthetic repository fixtures are published as source/test directories without their nested Git histories. Hidden evaluators, reference fixes, and raw per-task validation output remain private. The draft task manifest is public, but the private oracle is not; this package does not reproduce hidden-evaluator outcomes.

## Objective

Measure whether repository-aware retrieval changes objective coding-task success across the existing four flagship modes: `single`, `multi`, `multi-mcp`, and `multi-mcp-repomind`. Each task is evaluated from the same clean local repository commit for every variant. The only intended variant difference is capability availability. Public pytest output is retained as agent telemetry; a private evaluator run by the harness is the primary success criterion.

## Local repositories and baseline commits

| Repository | Domain | Draft baseline commit | Tracked files | Python source files / lines | Public test files / lines | Total tracked Python lines | Public tests (two runs) |
|---|---|---|---:|---:|---:|---:|---|
| `configflow` | CLI configuration | `b6d25c9ed6c327953a43e656f55468339a842fdf` | 13 | 9 / 101 | 2 / 59 | 160 | 12 passed twice |
| `miniservice` | REST-style ticket business logic | `78a7b24547a29cfbf442129586ce28b9a5353f14` | 12 | 8 / 99 | 2 / 42 | 141 | 11 passed twice |
| `streamstats` | CSV processing and analytics | `1259e72a910ca23d64943be0f60bf03af7eba5d5` | 13 | 9 / 75 | 2 / 39 | 114 | 8 passed twice |
| `accessflow` | authorization and approval workflow | `554d82894b1fa095c7e6c52c2c77cf31133662d9` | 13 | 9 / 75 | 2 / 36 | 111 | 11 passed twice |

Each is its own Git repository under `benchmark/repositories/`, with a clean initial commit shared by all six tasks for that repository. No external GitHub checkout, service, database, credential, or network access is needed.

| Repository | Package modules and call flow |
|---|---|
| `configflow` | `service` composes `environment`, `merge`, and `validation`; profile inheritance uses `deep_merge`; nested-path and secret-safe diagnostic helpers are separate modules. Modules: `environment`, `errors`, `merge`, `paths`, `profiles`, `secrets`, `service`, `validation` |
| `miniservice` | `api` delegates to `service`, which uses `validation`, immutable `models`, and `TicketRepository`; `reporting` reads repository event history. Modules: `api`, `errors`, `models`, `reporting`, `repository`, `service`, `validation` |
| `streamstats` | `pipeline` composes CSV `parser`, shared `cleaning`, `analytics`, and `report`; `windows` and `ordering` are independently reusable operations. Modules: `analytics`, `cleaning`, `models`, `ordering`, `parser`, `pipeline`, `report`, `windows` |
| `accessflow` | `service` composes `policy`, `roles`, `delegation`, `workflow`, and `audit` over immutable principals/grants/records in `models`. Modules: `audit`, `delegation`, `errors`, `models`, `policy`, `roles`, `service`, `workflow` |

The packages are small by design. Their recorded combined Python source/test footprint is shown in the table; do not inflate a repository with artificial filler. The most retrieval-dependent tasks follow multi-module relationships; the set also includes isolated behavior tasks.

## Task categories and balance

The draft contains 24 concrete tasks, six per repository. Category/difficulty/retrieval labels are descriptive and do not affect scoring.

| Category | configflow | miniservice | streamstats | accessflow | Total |
|---|---:|---:|---:|---:|---:|
| `api_behavior_change` | 1 | 3 | 1 | 1 | 6 |
| `configuration_dependency_change` | 1 | 0 | 0 | 0 | 1 |
| `cross_file_change` | 1 | 1 | 1 | 1 | 4 |
| `cross_file_dependency_change` | 1 | 0 | 1 | 0 | 2 |
| `deterministic_regression` | 0 | 0 | 1 | 0 | 1 |
| `missing_function_implementation` | 0 | 0 | 1 | 0 | 1 |
| `multi_file_bug_fix` | 0 | 0 | 0 | 1 | 1 |
| `regression_fix` | 1 | 1 | 0 | 1 | 3 |
| `security_behavior` | 1 | 0 | 0 | 1 | 2 |
| `single_file_bug_fix` | 0 | 1 | 1 | 0 | 2 |
| `workflow_behavior_change` | 0 | 0 | 0 | 1 | 1 |

Difficulty after audit revision: easy **11**, medium **13**, hard **0**.

Retrieval relevance after audit revision: low **11**, medium **8**, high **5**. Relevance is assigned from expected repository context before any agent run and is not part of the outcome metric. Per-task label rationales are recorded in [the label review](agent-benchmark-v1-task-labels.md).

See [the task catalog](agent-benchmark-v1-task-catalog.md) for every prompt, evaluator identity, and observed oracle result.

## Task prompts and hidden evaluator design

Each task has a natural-language request, category, difficulty, retrieval relevance, evaluator ID/command template, 90-second evaluator timeout, and `hidden_pytest_exit_code_zero` criterion in `benchmark/tasks/manifest.draft.json`. Prompts contain no file paths, test names, evaluator locations, or reference-fix content. The human catalog includes the same prompts for review; it is not passed to an agent as evaluator metadata.

Every hidden pytest evaluator is under `benchmark/evaluators/<task_id>/`, outside every repository checkout. Each task has a private unified diff and fixed source snapshot under `benchmark/reference_fixes/<task_id>/`. The validator starts from a clean repository copy, observes the evaluator fail, applies only that task's reference source, then observes the same evaluator pass twice. Reference changes never enter an agent workspace or agent prompt.

## Baseline and reference validation results

- Repository public suites: **4/4 pass twice** using the same baseline checkout.
- Hidden task oracles: **24/24 fail on baseline inside a collected test body**.
- Private reference implementations: **24/24 pass**, and each reference evaluator exit status is stable across two runs.
- Oracle outcomes: `benchmark/validation-results.json`.
- Draft task manifest SHA-256 (exact file bytes): `b087c4211c5ee9f0e0baa07581a3dc5d9fe8ffb473785fde474673c40ba8b3d2`.

These are corpus/evaluator validation results only. They are not coding-agent performance results.

## Human-audit revisions

The task-level audit retained all 24 tasks and kept `STREAMSTATS-04` as an intentional easy deterministic-ordering anchor because `ordering.chronological` documents timestamp ties ordered by group name. Its evaluator now covers three equal-timestamp groups. Other evaluators were expanded to cover their stated contracts and public integration paths where applicable. `CONFIGFLOW-06` and `STREAMSTATS-06` are medium rather than hard: each requires module integration, but the repository and task contracts remain small and explicit.

The three normalization tasks remain for distinct phenomena: local title normalization, API tag validation/normalization, and group normalization integrated into the analytics pipeline. `MINISERVICE-02` and `ACCESSFLOW-03` remain as cross-domain state-machine coverage. These are still draft judgments, not calibrated agent difficulty measurements.

## Environment and local setup

- Verified runtime: Python 3.12.4 on Windows-11-10.0.26200-SP0.
- Verified pytest: 7.4.4.
- Per-repository command: `python -m pytest -q`.
- Runtime dependencies: Python standard library only. Tests use pytest 7.4.4.
- The benchmark was validated in the already available environment; no dependency installation or network access was performed.
- The test timeout for each public/hidden invocation is 90 seconds.
- Each task starts from the exact revision in the draft manifest.

## Harness integration and isolation

The existing four CLI modes remain unchanged. `BenchmarkHarness` passes the same task description, public pytest command, model setting, tool-call budget, repair budget, and timeout to the selected mode. It invokes the hidden evaluator only after the agent subprocess exits, from a controller-owned evaluator root outside the workspace, and records evaluator status separately from the agent's public-test status. RepoMind telemetry is recorded for D when present; provider token usage remains null where the current CLI does not expose it.

For these local repositories, the harness copies the whole Git repository without hardlinks, checks out the exact SHA detached, and verifies the initial working tree is clean. Fresh copies prevent one task/variant from contaminating another. Reference fixes and evaluators are never copied into those working copies.

## Reproducibility and draft state

The task manifest is draft-only; its current hash is `b087c4211c5ee9f0e0baa07581a3dc5d9fe8ffb473785fde474673c40ba8b3d2` for review and reproducibility checks, not a freeze declaration. Before any future agent run, a human must review prompts/oracles, choose the model/provider parameters and all shared budgets, pin RepoMind ingestion identity/configuration, define run ordering and result retention, and explicitly freeze the manifest. The actual four-way benchmark has not run.

## Threats to validity and remaining risks

- These purpose-built repositories are smaller and more regular than production codebases. The combined recorded source and test code is 526 Python lines; each individual package is below the original 500-line-per-repository aspiration. They are multi-module workflows, but conclusions may not generalize to large unfamiliar projects.
- The benchmark author also authored hidden tests and reference fixes. Human review should challenge whether each evaluator fully captures its task without requiring the reference implementation's exact structure.
- All tasks target intentional defects/features in one baseline. The defect locations are not annotated in source, but an agent can still discover the behavior by inspection and public tests.
- The public suites and hidden evaluators passed twice in one Windows/Python/pytest environment. This is evidence of stable local exits, not a cross-platform or statistical determinism study.
- MCP server subprocess startup could not be verified in this sandbox during the full-suite check; MCP-specific tests were excluded from the final unit-suite run. The previous targeted benchmark harness tests use mocks for mode wiring. Validate MCP execution in the intended benchmark host before freezing.
- Token usage is not exposed by the existing CLI contract and will be recorded as null unless separately approved instrumentation is added before freeze.
- No coding-agent/LLM run has been made, so task difficulty and retrieval relevance have not been calibrated from model behavior.
