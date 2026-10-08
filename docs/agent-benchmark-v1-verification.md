# Agent benchmark v1 — curation and verification report

> **Superseded strategy note:** This earlier candidate-repository verification is retained as project history. The benchmark strategy has since changed to a controlled local corpus; see the current [draft design](agent-benchmark-v1-local-design.md) and [task catalog](agent-benchmark-v1-task-catalog.md). The findings below do not describe the current benchmark corpus.

**Status: blocked before task-level verification. The actual agent benchmark was not run, no task was sent to an LLM, no candidate checkout was retained, and no final benchmark manifest was created or frozen.**

## Executive outcome

The design document describes four candidate repositories and proposes six tasks per repository, but there is no task manifest, no 24 natural-language task descriptions, and no evaluator/oracle definitions in the workspace. The nine category names in the design are a category inventory; they are not concrete task records. Therefore no individual task can truthfully be marked valid, tested at baseline, repaired with a reference implementation, or checked for leakage, difficulty, overlap, or retrieval relevance.

In addition, Git could not resolve network hosts in this environment (`git ls-remote` failed for all four official GitHub remotes with `getaddrinfo() thread failed to start`). No isolated repository checkout, file count, dependency installation, or candidate baseline test could be performed. GitHub's official repository pages were consulted for source identity and current project metadata, but their moving `main` pages are not immutable revisions and do not substitute for checkout verification.

**Disposition of the 24 proposed slots:** 0 VALID, 24 REVISE, 0 REJECT. “REVISE” means each slot must first be supplied as a concrete, independently testable task record; it does not mean the task idea itself was examined and found defective. No replacement tasks were authored.

## Repository verification

The four sources are the official project repositories. The public metadata pages identify them as Python projects and show pytest test groups/configuration. Their declared Python minimums on the inspected current project metadata are >=3.10 for Click, ItsDangerous, and attrs; the inspected Packaging metadata also declares >=3.10. The workspace runtime is Python 3.12.4 on Windows. The candidate test suites were **not run** here.

| Candidate | Official source / project | Exact pinned revision | Tracked file count | Setup and test command from current metadata | Local baseline / runtime / determinism / external services | Current-environment suitability |
|---|---|---|---:|---|---|---|
| Click | [pallets/click](https://github.com/pallets/click), Python CLI library | Not established; moving `main` is not a pin | Not measured | Test dependency group includes pytest; `python -m pytest` (stress marker excluded by project config). Install the pinned source plus test group. | Not run. No network/credential dependency was verified. Runtime and determinism remain unknown locally. | **Unsuitable for verification in this environment** until Git/DNS access or an approved local immutable mirror is available. |
| ItsDangerous | [pallets/itsdangerous](https://github.com/pallets/itsdangerous), Python signing/serialization library | Not established | Not measured | Test dependency group includes pytest and freezegun; `python -m pytest`. | Not run. Local network/credential behavior, duration, and determinism unverified. | **Unsuitable for verification in this environment** for the same checkout limitation. |
| attrs | [python-attrs/attrs](https://github.com/python-attrs/attrs), Python class/validation library | Not established | Not measured | Tests dependency group includes Hypothesis, pympler, pytest, pytest-xdist, and cloudpickle on CPython; `python -m pytest`. | Not run. Property-based test settings/runtime and external-service use unverified. | **Unsuitable for verification in this environment** for the same checkout limitation. |
| Packaging | [pypa/packaging](https://github.com/pypa/packaging), Python packaging specification utilities | Not established | Not measured | Test dependency group includes coverage, Hypothesis, pip, pretend, pytest, tomli_w; `python -m pytest` (property-marked tests excluded by default). | Not run. Local network/credential behavior, duration, and determinism unverified. | **Unsuitable for verification in this environment** for the same checkout limitation. |

Metadata references: Click [pyproject.toml](https://github.com/pallets/click/blob/main/pyproject.toml), ItsDangerous [pyproject.toml](https://github.com/pallets/itsdangerous/blob/main/pyproject.toml), attrs [pyproject.toml](https://github.com/python-attrs/attrs/blob/main/pyproject.toml), Packaging [pyproject.toml](https://github.com/pypa/packaging/blob/main/pyproject.toml). These are branch URLs and were used only for project metadata; they are not benchmark pins.

The candidate set is **not rejected as intrinsically unsuitable**. It is unsuitable for a reproducible local verification run under the present network restriction. A later phase must acquire and record immutable full commit SHAs, then measure tracked files and run each baseline suite in an isolated environment. Do not use a floating branch, package release label, or short SHA as the final repository revision.

### Environment and reproducibility observations

- Current workspace runtime: Python 3.12.4, Windows (PowerShell host).
- Candidate checkouts: none; temporary clone attempts were not created because DNS resolution failed before Git could fetch.
- Dependency installs and candidate tests: not attempted without source checkout.
- Candidate-repository runtime, test repeatability, network access during tests, and external credential/service requirements: unknown until tests/configuration are inspected at pinned revisions.
- The likely local setup is an isolated environment per pinned repository snapshot, install its test dependency group from a pinned lock or resolved constraints, then run `python -m pytest`. This is a proposal only, not a verified install procedure.
- Approximate file counts and clean test baselines cannot be responsibly reported from branch-page snippets. The values in the earlier design were explicitly estimates and remain unverified.

## Task-by-task verification table

The following report-only slot labels are used to account for the stated 24 proposals. They are not task IDs and are not present in a manifest. The design gives no mapping of category to repository and no concrete prompt, test identity, or known-good patch for any slot.

| Slot | Proposed repository allocation | Concrete task/category | Baseline evaluator | Reference fix | Decision |
|---|---|---|---|---|---|
| P01 | Click, slot 1 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P02 | Click, slot 2 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P03 | Click, slot 3 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P04 | Click, slot 4 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P05 | Click, slot 5 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P06 | Click, slot 6 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P07 | ItsDangerous, slot 1 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P08 | ItsDangerous, slot 2 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P09 | ItsDangerous, slot 3 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P10 | ItsDangerous, slot 4 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P11 | ItsDangerous, slot 5 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P12 | ItsDangerous, slot 6 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P13 | attrs, slot 1 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P14 | attrs, slot 2 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P15 | attrs, slot 3 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P16 | attrs, slot 4 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P17 | attrs, slot 5 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P18 | attrs, slot 6 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P19 | Packaging, slot 1 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P20 | Packaging, slot 2 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P21 | Packaging, slot 3 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P22 | Packaging, slot 4 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P23 | Packaging, slot 5 of 6 | Not supplied | Not supplied | Not supplied | REVISE |
| P24 | Packaging, slot 6 of 6 | Not supplied | Not supplied | Not supplied | REVISE |

Because the actual tasks are missing, none of the required per-task checks can be answered: clarity, baseline behavior, tool solvability, test-only oracle, external access, nondeterminism, difficulty, repository knowledge, solution leakage, overlap, meaningfulness, or RepoMind relevance. No baseline-failing oracle or known-good patch validation exists. No test was added to an agent-visible workspace or hidden evaluator location.

## Oracle and task independence

The design's intended oracle is the required pytest command's final exit status, independent of Reviewer approval. That is a suitable top-level success criterion, but it is not yet an oracle for any task. Each task still needs a named existing regression test or a separately stored evaluator test, plus:

1. evaluator fails on the exact clean baseline;
2. evaluator passes after a known-good reference change;
3. evaluator is invoked consistently for every variant and cannot be modified or read by the agent;
4. task starts independently from the same pinned repository SHA.

The harness's isolated-workspace primitive and existing harness tests cover clean checkout mechanics with stubs. They do not establish the 24 task oracles, candidate commits, or repository baseline results.

## Difficulty, category, and repository balance

The proposal names nine categories: single-file bug fix, multi-file bug fix, missing function, API/behavior change, configuration/dependency change, cross-file dependency change, test-driven regression fix, small feature, and testable repository understanding. There are no per-task category assignments, so no category matrix or true distribution can be calculated. Difficulty counts are likewise **unknown**; the proposed six-per-repository allocation is only a quota, not evidence of balance.

The four candidates represent distinct code domains, but two are from the Pallets ecosystem (Click and ItsDangerous). Whether their tasks overlap or one repository dominates by baseline speed, documentation, or task simplicity cannot be measured before concrete tasks and baseline runs exist. Candidate balance should be assessed using per-task complexity, baseline runtime and task categories after verification, not forced equal difficulty labels.

## RepoMind relevance and information leakage

No specific task is currently available to score for repository-wide context. The category inventory could support retrieval-relevant tasks (cross-file dependencies, implementation/test relationships, configuration relationships, source/documentation relationships), but it does not prove any such opportunity exists in the candidates. Per-task retrieval relevance is therefore **not assessed**.

No task prompt exists to audit for file paths, symbol names, code snippets, test names, or solution hints. The design's policy—observable behavior without patch instructions—is appropriate but not yet validated against task text.

## Harness and existing implementation review

- The CLI exposes `single`, `multi`, `multi-mcp`, and `multi-mcp-repomind`; the harness maps its four fixed variants to those modes.
- Task records require repository ID/source/revision, task category/description, pytest command and timeout. The loader checks non-empty manifest tasks, unique task IDs, pytest-prefixed commands, and positive timeouts; exact-byte SHA-256 is recorded.
- The harness passes common model name, tool-call budget, repair/coding-attempt budget, and bounded test timeout to the CLI, enforces a subprocess wall timeout, records failed/invalid outputs, and appends structured JSONL rows.
- Each workspace is an independent clone checked out detached at the requested revision and checked for exact HEAD and clean status. The Git implementation itself has not been exercised against real repositories in this verification phase.
- D-only RepoMind telemetry includes audit-derived retrieval calls/errors and latency plus Planner evidence row count/distinct source IDs when present. Token usage remains `null`; current CLI output does not expose provider usage.
- Candidate installation, separate evaluator execution outside agent workspace, RepoMind one-time ingestion per pinned repository, cache immutability, and full run-manifest recording have not been demonstrated by the current harness tests and remain pre-freeze requirements.

Harness-only verification: `python -m pytest tests\\test_benchmark_harness.py -q` — **15 passed in 0.13s** on Python 3.12.4. These tests use fake process and Git runners; they are not candidate-repository tests and do not call an LLM.

## Counts and recommendation

- Valid tasks: **0**
- Tasks needing revision/concretization: **24**
- Rejected tasks: **0**
- Candidate repositories verified executable: **0**
- Candidates removed as intrinsically unsuitable: **0**
- Candidates suitable for verification in this current environment: **0** (source fetch unavailable)
- Final manifest frozen: **No**
- Actual coding-agent benchmark run: **No**

Twenty-four remains a reasonable *target* size, but it is not yet an evidenced task set. If task curation leaves fewer than about 20 tasks after oracle validation, propose and document replacements before the human freeze review. Do not generate replacement tasks or freeze a manifest in this phase.

## Blocking issues before human review can approve a freeze

1. Restore Git/DNS access or provide approved immutable local mirrors for the four official repositories.
2. Pin full commit SHAs and verify source, file counts, setup, test dependencies, baseline suite results, runtime, and network/service behavior in isolated environments.
3. Supply the actual 24 task prompts and task-to-repository/category mapping.
4. For every task, define a hidden evaluator, observe baseline failure, apply a private known-good fix, and observe evaluator pass; reject or revise failures.
5. Record measured difficulty/category/retrieval relevance and audit prompt leakage/overlap.
6. Test that evaluators cannot be accessed or altered from each agent workspace and test the runner against a real pinned local mirror.
7. Resolve token-usage telemetry if required; otherwise explicitly accept null token fields before freezing.

Until these checks pass, the evaluator is **not yet validated**, and there is no sound basis to claim any of the 24 tasks are benchmark-ready.
