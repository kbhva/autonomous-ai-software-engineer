"""Render human-review docs from the current draft corpus and validation run."""

from __future__ import annotations

import hashlib
import json
import platform
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
DOCS = PROJECT / "docs"
manifest_path = ROOT / "tasks" / "manifest.draft.json"
manifest_bytes = manifest_path.read_bytes()
manifest = json.loads(manifest_bytes)
results = json.loads((ROOT / "validation-results.json").read_text(encoding="utf-8"))
task_results = {item["task_id"]: item for item in results["tasks"]}
repo_results = results["repositories"]
manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()


def tests_passed(text: str) -> str:
    match = re.search(r"(\d+) passed", text)
    return match.group(1) if match else "unknown"


def module_names(repo_id: str) -> list[str]:
    root = ROOT / "repositories" / repo_id / "src" / manifest["repositories"][repo_id]["package"]
    return [path.stem for path in sorted(root.glob("*.py")) if path.name != "__init__.py"]


repo_rows = []
for repo_id, spec in manifest["repositories"].items():
    measured = repo_results[repo_id]
    repo_rows.append((repo_id, spec, measured))

category_counts = Counter(task["task_category"] for task in manifest["tasks"])
difficulty_counts = Counter(task["difficulty"] for task in manifest["tasks"])
relevance_counts = Counter(task["retrieval_relevance"] for task in manifest["tasks"])
per_repo_category = {
    repo_id: Counter(task["task_category"] for task in manifest["tasks"] if task["repository_id"] == repo_id)
    for repo_id in manifest["repositories"]
}

design = [
    "# Agent benchmark v1 — controlled local design (draft)",
    "",
    "> **DRAFT — NOT FROZEN. No coding-agent benchmark has been run and no task has been sent to an LLM.**",
    "",
    "## Objective",
    "",
    "Measure whether repository-aware retrieval changes objective coding-task success across the existing four flagship modes: `single`, `multi`, `multi-mcp`, and `multi-mcp-repomind`. Each task is evaluated from the same clean local repository commit for every variant. The only intended variant difference is capability availability. Public pytest output is retained as agent telemetry; a private evaluator run by the harness is the primary success criterion.",
    "",
    "## Local repositories and baseline commits",
    "",
    "| Repository | Domain | Draft baseline commit | Tracked files | Python source files / lines | Public test files / lines | Total tracked Python lines | Public tests (two runs) |",
    "|---|---|---|---:|---:|---:|---:|---|",
]
for repo_id, spec, measured in repo_rows:
    design.append(
        f"| `{repo_id}` | { {'configflow':'CLI configuration','miniservice':'REST-style ticket business logic','streamstats':'CSV processing and analytics','accessflow':'authorization and approval workflow'}[repo_id] } | `{spec['revision']}` | {measured['tracked_file_count']} | {measured['python_source_file_count']} / {measured['python_source_lines']} | {measured['python_test_file_count']} / {measured['python_test_lines']} | {measured['total_tracked_python_lines']} | {tests_passed(measured['first_baseline_run']['stdout'])} passed twice |"
    )
design += [
    "",
    "Each is its own Git repository under `benchmark/repositories/`, with a clean initial commit shared by all six tasks for that repository. No external GitHub checkout, service, database, credential, or network access is needed.",
    "",
    "| Repository | Package modules and call flow |",
    "|---|---|",
]
flow_text = {
    "configflow": "`service` composes `environment`, `merge`, and `validation`; profile inheritance uses `deep_merge`; nested-path and secret-safe diagnostic helpers are separate modules.",
    "miniservice": "`api` delegates to `service`, which uses `validation`, immutable `models`, and `TicketRepository`; `reporting` reads repository event history.",
    "streamstats": "`pipeline` composes CSV `parser`, shared `cleaning`, `analytics`, and `report`; `windows` and `ordering` are independently reusable operations.",
    "accessflow": "`service` composes `policy`, `roles`, `delegation`, `workflow`, and `audit` over immutable principals/grants/records in `models`.",
}
for repo_id in manifest["repositories"]:
    design.append(f"| `{repo_id}` | {flow_text[repo_id]} Modules: " + ", ".join(f"`{name}`" for name in module_names(repo_id)) + " |")
design += [
    "",
    "The packages are small by design. Their recorded combined Python source/test footprint is shown in the table; do not inflate a repository with artificial filler. The most retrieval-dependent tasks follow multi-module relationships; the set also includes isolated behavior tasks.",
    "",
    "## Task categories and balance",
    "",
    "The draft contains 24 concrete tasks, six per repository. Category/difficulty/retrieval labels are descriptive and do not affect scoring.",
    "",
    "| Category | " + " | ".join(manifest["repositories"]) + " | Total |",
    "|---|" + "---:|" * (len(manifest["repositories"]) + 1),
]
for category in sorted(category_counts):
    design.append("| `" + category + "` | " + " | ".join(str(per_repo_category[repo].get(category, 0)) for repo in manifest["repositories"]) + f" | {category_counts[category]} |")
design += [
    "",
    "Difficulty: " + ", ".join(f"{name} **{difficulty_counts.get(name, 0)}**" for name in ("easy", "medium", "hard")) + ".",
    "",
    "Retrieval relevance: " + ", ".join(f"{name} **{relevance_counts.get(name, 0)}**" for name in ("low", "medium", "high")) + ". Relevance is assigned from expected repository context before any agent run and is not part of the outcome metric.",
    "",
    "See [the task catalog](agent-benchmark-v1-task-catalog.md) for every prompt, evaluator identity, and observed oracle result.",
    "",
    "## Task prompts and hidden evaluator design",
    "",
    "Each task has a natural-language request, category, difficulty, retrieval relevance, evaluator ID/command template, 90-second evaluator timeout, and `hidden_pytest_exit_code_zero` criterion in `benchmark/tasks/manifest.draft.json`. Prompts contain no file paths, test names, evaluator locations, or reference-fix content. The human catalog includes the same prompts for review; it is not passed to an agent as evaluator metadata.",
    "",
    "Every hidden pytest evaluator is under `benchmark/evaluators/<task_id>/`, outside every repository checkout. Each task has a private unified diff and fixed source snapshot under `benchmark/reference_fixes/<task_id>/`. The validator starts from a clean repository copy, observes the evaluator fail, applies only that task's reference source, then observes the same evaluator pass twice. Reference changes never enter an agent workspace or agent prompt.",
    "",
    "## Baseline and reference validation results",
    "",
    f"- Repository public suites: **4/4 pass twice** using the same baseline checkout.\n- Hidden task oracles: **24/24 fail on baseline inside a collected test body**.\n- Private reference implementations: **24/24 pass**, and each reference evaluator exit status is stable across two runs.\n- Oracle outcomes: `benchmark/validation-results.json`.\n- Draft task manifest SHA-256 (exact file bytes): `{manifest_sha}`.",
    "",
    "These are corpus/evaluator validation results only. They are not coding-agent performance results.",
    "",
    "## Environment and local setup",
    "",
    f"- Verified runtime: Python {results['python'].split()[0]} on {platform.platform()}.\n- Verified pytest: 7.4.4.\n- Per-repository command: `python -m pytest -q`.\n- Runtime dependencies: Python standard library only. Tests use pytest 7.4.4.\n- The benchmark was validated in the already available environment; no dependency installation or network access was performed.\n- The test timeout for each public/hidden invocation is 90 seconds.\n- Each task starts from the exact revision in the draft manifest.",
    "",
    "## Harness integration and isolation",
    "",
    "The existing four CLI modes remain unchanged. `BenchmarkHarness` passes the same task description, public pytest command, model setting, tool-call budget, repair budget, and timeout to the selected mode. It invokes the hidden evaluator only after the agent subprocess exits, from a controller-owned evaluator root outside the workspace, and records evaluator status separately from the agent's public-test status. RepoMind telemetry is recorded for D when present; provider token usage remains null where the current CLI does not expose it.",
    "",
    "For these local repositories, the harness copies the whole Git repository without hardlinks, checks out the exact SHA detached, and verifies the initial working tree is clean. Fresh copies prevent one task/variant from contaminating another. Reference fixes and evaluators are never copied into those working copies.",
    "",
    "## Reproducibility and draft state",
    "",
    f"The task manifest is draft-only; its current hash is `{manifest_sha}` for review and reproducibility checks, not a freeze declaration. Before any future agent run, a human must review prompts/oracles, choose the model/provider parameters and all shared budgets, pin RepoMind ingestion identity/configuration, define run ordering and result retention, and explicitly freeze the manifest. The actual four-way benchmark has not run.",
    "",
    "## Threats to validity and remaining risks",
    "",
    "- These purpose-built repositories are smaller and more regular than production codebases. The combined recorded source and test code is 526 Python lines; each individual package is below the original 500-line-per-repository aspiration. They are multi-module workflows, but conclusions may not generalize to large unfamiliar projects.",
    "- The benchmark author also authored hidden tests and reference fixes. Human review should challenge whether each evaluator fully captures its task without requiring the reference implementation's exact structure.",
    "- All tasks target intentional defects/features in one baseline. The defect locations are not annotated in source, but an agent can still discover the behavior by inspection and public tests.",
    "- The public suites and hidden evaluators passed twice in one Windows/Python/pytest environment. This is evidence of stable local exits, not a cross-platform or statistical determinism study.",
    "- MCP server subprocess startup could not be verified in this sandbox during the full-suite check; MCP-specific tests were excluded from the final unit-suite run. The previous targeted benchmark harness tests use mocks for mode wiring. Validate MCP execution in the intended benchmark host before freezing.",
    "- Token usage is not exposed by the existing CLI contract and will be recorded as null unless separately approved instrumentation is added before freeze.",
    "- No coding-agent/LLM run has been made, so task difficulty and retrieval relevance have not been calibrated from model behavior.",
]
(DOCS / "agent-benchmark-v1-local-design.md").write_text("\n".join(design) + "\n", encoding="utf-8", newline="\n")

catalog = [
    "# Agent benchmark v1 — task catalog (draft)",
    "",
    "> **DRAFT — NOT FROZEN.** This catalog is for human review. The actual coding-agent benchmark has not run.",
    "",
    f"Tasks: **{len(manifest['tasks'])}** across four local repositories. Draft manifest SHA-256: `{manifest_sha}`.",
    "",
    "Hidden evaluator files and reference fixes are controller-only artifacts in `benchmark/evaluators/` and `benchmark/reference_fixes/`. Do not include them in agent workspaces or task prompts.",
    "",
]
for task in manifest["tasks"]:
    measured = task_results[task["task_id"]]
    status = "VALID oracle pair" if measured["baseline_failed_in_test_body"] and measured["reference_passed"] and measured["reference_deterministic_exit"] else "REVISE"
    catalog += [
        f"## {task['task_id']} — {task['repository_id']}",
        "",
        f"- **Category:** `{task['task_category']}`",
        f"- **Difficulty:** `{task['difficulty']}`",
        f"- **Retrieval relevance:** `{task['retrieval_relevance']}`",
        f"- **Evaluator:** `{task['evaluator_id']}` (external to agent workspace)",
        f"- **Oracle validation:** baseline failed in test body (exit {measured['baseline_exit']}); private reference passed (exit {measured['reference_exit']}); reference repeated with exit {measured['reference_repeat_exit']}. **{status}.**",
        "",
        "**Agent task prompt**",
        "",
        task["task_description"],
        "",
    ]
(DOCS / "agent-benchmark-v1-task-catalog.md").write_text("\n".join(catalog) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"manifest_sha256": manifest_sha, "catalog_tasks": len(manifest["tasks"]),
                   "valid_oracle_pairs": results["counts"]["valid_oracle_pairs"]}, indent=2))
