import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from flagship.benchmark.harness import (
    VARIANTS,
    BenchmarkHarness,
    BenchmarkTask,
    deterministic_run_order,
    deterministic_run_schedule,
    load_tasks,
    manifest_sha256,
    materialize_clean_workspace,
)


def task(**overrides):
    values = {
        "task_id": "T001",
        "repository_id": "click",
        "repository_source": "source-repo",
        "repository_revision": "abc123",
        "task_category": "single_file_bug_fix",
        "task_description": "Fix a deterministic behavior regression.",
        "test_command": "pytest -q",
        "timeout_seconds": 30,
    }
    values.update(overrides)
    return BenchmarkTask.from_dict(values)


def fake_process(payload, returncode=0):
    return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=returncode)


def result_payload(**overrides):
    result = {
        "mode": "single",
        "success": True,
        "status": "DONE",
        "message": "done",
        "repair_attempts": 1,
        "tool_calls": 6,
        "tests": [{"success": True}],
        "audit": [],
        "single_agent": {"success": True},
        "retrieval_latency_ms": 0.0,
    }
    result.update(overrides)
    return result


def harness(process_runner=lambda *a, **kw: fake_process(result_payload()), **kwargs):
    defaults = {
        "model_name": "fixed-model",
        "max_tool_calls": 17,
        "max_repair_attempts": 2,
        "test_timeout_seconds": 91,
        "process_runner": process_runner,
    }
    defaults.update(kwargs)
    return BenchmarkHarness(**defaults)


def test_all_variants_receive_same_task_description_and_configuration(tmp_path):
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return fake_process(result_payload(mode=command[command.index("--mode") + 1]))
    h = harness(run, repomind_base_url="http://repomind", repository_uuid_by_id={
        "click": "00000000-0000-0000-0000-000000000001"
    })
    target = task()
    for variant in VARIANTS:
        h.run(target, variant, tmp_path, task_manifest_hash="hash", api_key="secret")

    assert len(calls) == 4
    for command, options in calls:
        assert command[command.index("--task") + 1] == target.task_description
        assert command[command.index("--test-command") + 1] == target.test_command
        assert options["env"]["FLAGSHIP_MODEL"] == "fixed-model"
        assert options["env"]["FLAGSHIP_MAX_TOOL_CALLS"] == "17"
        assert options["env"]["FLAGSHIP_MAX_REPAIR_ATTEMPTS"] == "2"
        assert options["env"]["FLAGSHIP_MAX_CODING_ATTEMPTS"] == "3"
        assert options["env"]["FLAGSHIP_TEST_TIMEOUT_SECONDS"] == "30"
        assert options["timeout"] == 30


def test_each_variant_gets_a_separate_clean_revision_checkout(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    workspaces = []
    def git_runner(command, **kwargs):
        if command[1] == "clone":
            destination = Path(command[-1])
            destination.mkdir()
            (destination / "baseline.txt").write_text("baseline", encoding="utf-8")
            workspaces.append(destination)
            return SimpleNamespace(stdout="")
        if "rev-parse" in command:
            return SimpleNamespace(stdout="abc123\n")
        return SimpleNamespace(stdout="")

    spec = task()
    first = materialize_clean_workspace(spec, tmp_path / "run-a", git_runner=git_runner)
    second = materialize_clean_workspace(spec, tmp_path / "run-b", git_runner=git_runner)
    (first / "baseline.txt").write_text("variant A mutation", encoding="utf-8")

    assert first != second
    assert (second / "baseline.txt").read_text(encoding="utf-8") == "baseline"
    assert len(workspaces) == 2


def test_existing_workspace_is_rejected_to_prevent_contamination(tmp_path):
    target = tmp_path / "exists"
    target.mkdir()
    with pytest.raises(FileExistsError):
        materialize_clean_workspace(task(), target, git_runner=lambda *_a, **_k: pytest.fail())


def test_task_timeout_is_captured_as_a_run_record(tmp_path):
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("flagship", 30, output="partial", stderr="still running")
    record = harness(timeout).run(task(), VARIANTS[0], tmp_path, task_manifest_hash="hash", api_key=None)
    assert record.status == "timeout"
    assert record.final_test_status == "timeout"
    assert record.success is False
    assert record.failure_reason == "Task exceeded 30s wall-clock timeout"


def test_tool_and_repair_budgets_are_fixed_in_child_environment(tmp_path):
    seen = {}
    def run(command, **kwargs):
        seen.update(kwargs["env"])
        return fake_process(result_payload())
    harness(run, max_tool_calls=11, max_repair_attempts=3, test_timeout_seconds=77).run(
        task(timeout_seconds=120), VARIANTS[1], tmp_path, task_manifest_hash="h", api_key=None
    )
    assert seen["FLAGSHIP_MAX_TOOL_CALLS"] == "11"
    assert seen["FLAGSHIP_MAX_REPAIR_ATTEMPTS"] == "3"
    assert seen["FLAGSHIP_MAX_CODING_ATTEMPTS"] == "4"
    assert seen["FLAGSHIP_TEST_TIMEOUT_SECONDS"] == "77"


def test_test_result_is_captured_as_objective_success(tmp_path):
    record = harness().run(task(), VARIANTS[0], tmp_path, task_manifest_hash="h", api_key=None)
    assert record.success is True
    assert record.final_test_status == "passed"


def test_token_usage_is_captured_when_provider_supplies_it(tmp_path):
    # The current flagship result does not expose usage; null is required rather than fabricated.
    record = harness().run(task(), VARIANTS[0], tmp_path, task_manifest_hash="h", api_key=None)
    assert record.input_tokens is None
    assert record.output_tokens is None
    assert record.total_tokens is None


def test_repomind_metrics_and_planner_evidence_are_captured_when_available(tmp_path):
    payload = result_payload(
        retrieval_latency_ms=42.5,
        audit=[
            {"provider": "repomind", "success": True, "tool": "search_repository"},
            {"provider": "mcp", "success": True, "tool": "read_file"},
        ],
        planner={"retrieval_evidence": [{"results": [
            {"source_id": "src/a.py", "chunk_id": "a"},
            {"source_id": "src/a.py", "chunk_id": "a2"},
            {"source_id": "README.md", "chunk_id": "b"},
        ]}]},
    )
    h = harness(lambda *_a, **_k: fake_process(payload), repomind_base_url="http://local",
                repository_uuid_by_id={"click": "00000000-0000-0000-0000-000000000001"})
    record = h.run(task(), VARIANTS[3], tmp_path, task_manifest_hash="h", api_key="key")
    assert record.retrieval_calls == 1
    assert record.retrieval_latency_ms == 42.5
    assert record.retrieval_errors == 0
    assert record.retrieved_evidence_count == 3
    assert record.retrieved_source_ids == ("src/a.py", "README.md")


def test_failed_runs_are_returned_not_dropped(tmp_path):
    record = harness(lambda *_a, **_k: fake_process({"not": "a run result"}, returncode=1)).run(
        task(), VARIANTS[0], tmp_path, task_manifest_hash="h", api_key=None
    )
    assert record.status == "invalid_agent_result"
    assert record.success is False
    assert record.raw_return_code == 1
    assert record.failure_reason


def test_run_order_is_seeded_and_counterbalanced():
    tasks = [task(task_id=f"T{i:02}") for i in range(24)]
    first = deterministic_run_schedule(tasks, seed=20261008)
    second = deterministic_run_schedule(tasks, seed=20261008)
    assert first == second
    assert len(first) == 24 * len(VARIANTS)
    position_counts = [{variant.variant_id: 0 for variant in VARIANTS} for _ in VARIANTS]
    for start in range(0, len(first), len(VARIANTS)):
        group = first[start:start + len(VARIANTS)]
        assert len({row.task.task_id for row in group}) == 1
        for position, row in enumerate(group):
            position_counts[position][row.variant.variant_id] += 1
            assert row.repetition == 1
            assert row.order_seed == 20261008
            assert row.order_index == start + position + 1
    assert all(set(counts.values()) == {6} for counts in position_counts)
    assert len({variant.variant_id for _task, variant in deterministic_run_order(tasks)[:4]}) == 4


def test_schedule_supports_repetitions_and_validates_count():
    schedule = deterministic_run_schedule([task(task_id="T1")], seed=9, repetitions=3)
    assert [row.repetition for row in schedule] == [1] * 4 + [2] * 4 + [3] * 4
    assert {row.order_seed for row in schedule} == {9}
    with pytest.raises(ValueError, match="positive"):
        deterministic_run_schedule([], repetitions=0)


def test_manifest_hash_uses_exact_file_bytes(tmp_path):
    path = tmp_path / "tasks.json"
    raw = b'{"tasks": []}\r\n'
    path.write_bytes(raw)
    assert manifest_sha256(path) == __import__("hashlib").sha256(raw).hexdigest()


def test_task_manifest_hash_is_attached_to_run_record(tmp_path):
    record = harness().run(task(), VARIANTS[0], tmp_path, task_manifest_hash="frozen-hash", api_key=None)
    assert record.task_manifest_sha256 == "frozen-hash"
    assert record.run_id
    assert record.repetition == 1


def test_run_schedule_metadata_is_captured(tmp_path):
    record = harness().run(task(), VARIANTS[0], tmp_path, task_manifest_hash="h", api_key=None,
                           run_id="run-fixed", repetition=2, order_seed=17, order_index=23)
    assert (record.run_id, record.repetition, record.order_seed, record.order_index) == (
        "run-fixed", 2, 17, 23)


def test_variant_identity_is_attached_to_record():
    assert [variant.variant_id for variant in VARIANTS] == [
        "single", "multi_agent", "multi_agent_mcp", "multi_agent_mcp_repomind"
    ]


def test_output_record_is_append_only_jsonl(tmp_path):
    path = tmp_path / "runs.jsonl"
    h = harness()
    record = h.run(task(), VARIANTS[0], tmp_path, task_manifest_hash="hash", api_key=None)
    h.write_record(path, record)
    h.write_record(path, record)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert all(row["task_id"] == "T001" for row in rows)


def test_load_tasks_validates_unique_ids_and_hashes_exact_manifest(tmp_path):
    path = tmp_path / "tasks.json"
    row = {
        "task_id": "T1", "repository_id": "click", "repository_source": "src",
        "repository_revision": "abc123", "task_category": "regression",
        "task_description": "Fix behavior", "test_command": "python -m pytest -q",
        "timeout_seconds": 60,
    }
    raw = json.dumps({"tasks": [row]}, separators=(",", ":")).encode()
    path.write_bytes(raw)
    tasks, digest = load_tasks(path)
    assert len(tasks) == 1
    assert digest == __import__("hashlib").sha256(raw).hexdigest()
    path.write_text(json.dumps({"tasks": [row, row]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_tasks(path)


def test_external_evaluator_is_run_outside_agent_workspace_and_is_primary_success(tmp_path):
    workspace = tmp_path / "agent-repo"
    (workspace / "src").mkdir(parents=True)
    evaluator_root = tmp_path / "private-evaluators"
    evaluator_file = evaluator_root / "T001" / "test_acceptance.py"
    evaluator_file.parent.mkdir(parents=True)
    evaluator_file.write_text("def test_acceptance(): assert True\n", encoding="utf-8")
    invocations = []

    def runner(command, **options):
        invocations.append((command, options))
        if "flagship.cli" in command:
            return fake_process(result_payload())
        return SimpleNamespace(stdout="1 passed", stderr="", returncode=0)

    row = {
        "task_id": "T001", "repository_id": "click", "repository_source": "source",
        "repository_revision": "abc123", "task_category": "behavior",
        "task_description": "Fix behavior", "test_command": "python -m pytest -q",
        "timeout_seconds": 30, "evaluator_id": "T001",
        "evaluator_command": "python -m pytest -q <controller-evaluator-root>/<evaluator_id>/test_acceptance.py",
    }
    target = BenchmarkTask.from_dict(row)
    h = harness(runner, evaluator_root=evaluator_root)
    record = h.run(target, VARIANTS[0], workspace, task_manifest_hash="h", api_key=None)

    assert len(invocations) == 2
    evaluator_command, options = invocations[1]
    assert str(evaluator_file.resolve()) in evaluator_command
    assert Path(options["cwd"]).resolve() == workspace.resolve()
    assert not Path(evaluator_command[-1]).is_relative_to(workspace.resolve())
    assert str(workspace / "src") in options["env"]["PYTHONPATH"]
    assert record.success is True and record.final_evaluator_status == "passed"
    assert record.evaluator_return_code == 0


def test_external_evaluator_failure_overrides_agent_public_test_success(tmp_path):
    workspace = tmp_path / "agent-repo"
    workspace.mkdir()
    evaluator_root = tmp_path / "evaluators"
    evaluator_file = evaluator_root / "T001" / "test_acceptance.py"
    evaluator_file.parent.mkdir(parents=True)
    evaluator_file.write_text("def test_acceptance(): assert False\n", encoding="utf-8")
    calls = 0

    def runner(_command, **_options):
        nonlocal calls
        calls += 1
        return fake_process(result_payload()) if calls == 1 else SimpleNamespace(stdout="failed", stderr="", returncode=1)

    target = BenchmarkTask.from_dict({
        "task_id": "T001", "repository_id": "click", "repository_source": "source",
        "repository_revision": "abc123", "task_category": "behavior",
        "task_description": "Fix behavior", "test_command": "pytest -q", "timeout_seconds": 30,
        "evaluator_id": "T001", "evaluator_command": "python -m pytest -q evaluator",
    })
    record = harness(runner, evaluator_root=evaluator_root).run(
        target, VARIANTS[0], workspace, task_manifest_hash="h", api_key=None
    )
    assert record.final_test_status == "passed"
    assert record.final_evaluator_status == "failed"
    assert record.success is False and record.status == "evaluator_failed"


def test_task_manifest_rejects_evaluator_escape_or_bad_retrieval_label():
    row = {
        "task_id": "T001", "repository_id": "click", "repository_source": "source",
        "repository_revision": "abc123", "task_category": "behavior",
        "task_description": "Fix behavior", "test_command": "pytest -q", "timeout_seconds": 30,
        "evaluator_id": "../outside", "evaluator_command": "python -m pytest -q test.py",
    }
    with pytest.raises(ValueError, match="evaluator_id"):
        BenchmarkTask.from_dict(row)
    row["evaluator_id"] = "T001"
    row["retrieval_relevance"] = "extreme"
    with pytest.raises(ValueError, match="retrieval_relevance"):
        BenchmarkTask.from_dict(row)


def test_real_local_baseline_can_be_materialized_from_draft_manifest(tmp_path):
    manifest_path = Path(__file__).resolve().parents[1] / "benchmark" / "tasks" / "manifest.draft.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata = payload["repositories"]["configflow"]
    row = {
        "task_id": "LOCAL", "repository_id": "configflow", "repository_source": metadata["source"],
        "repository_revision": metadata["revision"], "task_category": "behavior",
        "task_description": "Local checkout mechanics", "test_command": "python -m pytest -q",
        "timeout_seconds": 30,
    }
    checkout = materialize_clean_workspace(BenchmarkTask.from_dict(row), tmp_path / "local-checkout")
    assert subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, capture_output=True,
                          text=True, check=True).stdout.strip() == metadata["revision"]
    assert subprocess.run(["git", "status", "--porcelain"], cwd=checkout, capture_output=True,
                          text=True, check=True).stdout == ""
