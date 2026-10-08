"""Consistency checks for the draft local benchmark artifacts; no agent calls."""

import hashlib
import json
import subprocess
from pathlib import Path

from flagship.benchmark.harness import load_tasks

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmark"
MANIFEST_PATH = BENCHMARK / "tasks" / "manifest.draft.json"
RESULTS_PATH = BENCHMARK / "validation-results.json"


def corpus():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def outcomes():
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def test_draft_has_unique_task_ids_and_four_variants():
    manifest = corpus()
    tasks = manifest["tasks"]
    assert manifest["status"] == "draft_not_frozen"
    assert len(tasks) == 24
    assert len({task["task_id"] for task in tasks}) == len(tasks)
    assert manifest["run_configuration"]["variants"] == [
        "single", "multi", "multi-mcp", "multi-mcp-repomind"
    ]


def test_draft_task_records_load_through_the_real_harness_schema():
    tasks, digest = load_tasks(MANIFEST_PATH)
    assert len(tasks) == 24 and len(digest) == 64
    assert all(task.evaluator_id and task.evaluator_command for task in tasks)


def test_every_task_uses_its_repository_baseline_and_a_hidden_evaluator():
    manifest = corpus()
    for task in manifest["tasks"]:
        repo = ROOT / task["repository_source"]
        assert task["repository_revision"] == manifest["repositories"][task["repository_id"]]["revision"]
        assert task["evaluator_id"] == task["task_id"]
        evaluator = BENCHMARK / "evaluators" / task["evaluator_id"] / "test_acceptance.py"
        assert evaluator.is_file()
        assert not evaluator.is_relative_to(repo.resolve())
        assert task["test_command"] == "python -m pytest -q"
        assert task["network_required"] is False
        assert task["independent_from_other_tasks"] is True


def test_repositories_are_clean_at_the_exact_baseline_commits():
    manifest = corpus()
    for repo_id, metadata in manifest["repositories"].items():
        repo = ROOT / metadata["source"]
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True).stdout
        assert head == metadata["revision"], repo_id
        assert status == "", repo_id


def test_all_task_oracles_fail_on_baseline_and_pass_on_private_reference():
    results = outcomes()
    tasks = results["tasks"]
    assert len(tasks) == 24
    assert all(row["baseline_failed"] and row["reference_passed"] for row in tasks)
    assert all(row["reference_deterministic_exit"] for row in tasks)
    assert all(row["baseline_exit"] == 1 for row in tasks)
    assert all(row["reference_exit"] == 0 for row in tasks)
    assert results["counts"]["valid_oracle_pairs"] == 24


def test_public_repository_suites_pass_twice_with_deterministic_exit_status():
    results = outcomes()
    assert results["counts"]["public_repositories_passing_twice"] == 4
    assert all(row["public_tests_pass_twice"] and row["deterministic_exit_status"]
               for row in results["repositories"].values())


def test_evaluators_and_reference_fixes_never_appear_in_task_prompts():
    manifest = corpus()
    for task in manifest["tasks"]:
        prompt = task["task_description"].lower()
        assert task["evaluator_id"].lower() not in prompt
        assert "reference fix" not in prompt and "test_task_" not in prompt
        assert "benchmark/reference_fixes" not in prompt
    serialized = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "reference_path" not in serialized
    assert "reference_patch_path" not in serialized


def test_repository_source_contains_no_seed_comments_that_give_away_defects():
    for repo_id in corpus()["repositories"]:
        package = BENCHMARK / "repositories" / repo_id / "src"
        for source in package.rglob("*.py"):
            assert "# BUG:" not in source.read_text(encoding="utf-8")


def test_manifest_sha_is_exact_and_repeatable():
    first = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    second = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert first == second


def test_category_difficulty_and_retrieval_labels_are_valid():
    tasks = corpus()["tasks"]
    assert all(task["difficulty"] in {"easy", "medium", "hard"} for task in tasks)
    assert all(task["retrieval_relevance"] in {"low", "medium", "high"} for task in tasks)
    assert len({task["task_category"] for task in tasks}) >= 7
