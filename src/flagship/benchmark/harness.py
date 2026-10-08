"""Deterministic, isolated runner primitives for the agent benchmark.

This module prepares/exercises the harness only. The actual frozen task manifest
will be supplied separately after repository candidates and tasks are reviewed.
"""

from __future__ import annotations

import hashlib
import json
import os
import itertools
import random
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    repository_id: str
    repository_source: str
    repository_revision: str
    task_category: str
    task_description: str
    test_command: str
    timeout_seconds: int
    expected_evaluation_method: str = "pytest_exit_code_zero"
    setup_requirements: tuple[str, ...] = ()
    difficulty: str | None = None
    evaluator_id: str | None = None
    evaluator_command: str | None = None
    retrieval_relevance: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BenchmarkTask":
        required = (
            "task_id", "repository_id", "repository_source", "repository_revision",
            "task_category", "task_description", "test_command", "timeout_seconds",
        )
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"Task is missing required fields: {', '.join(missing)}")
        if not str(value["task_id"]).strip() or not str(value["repository_revision"]).strip():
            raise ValueError("task_id and repository_revision must be non-empty")
        if not str(value["test_command"]).strip().startswith(("pytest", "python -m pytest")):
            raise ValueError("Benchmark test_command must invoke pytest")
        if isinstance(value["timeout_seconds"], bool) or int(value["timeout_seconds"]) < 1:
            raise ValueError("timeout_seconds must be positive")
        evaluator_id = value.get("evaluator_id")
        evaluator_command = value.get("evaluator_command")
        if evaluator_id is not None and (
            not isinstance(evaluator_id, str) or not evaluator_id.replace("-", "").replace("_", "").isalnum()
        ):
            raise ValueError("evaluator_id must contain only letters, digits, dashes, and underscores")
        if evaluator_id and (not isinstance(evaluator_command, str) or not evaluator_command.startswith("python -m pytest ")):
            raise ValueError("evaluator_command must invoke pytest")
        if value.get("retrieval_relevance") not in (None, "low", "medium", "high"):
            raise ValueError("retrieval_relevance must be low, medium, or high")
        return cls(
            **{key: value[key] for key in required},
            expected_evaluation_method=value.get("expected_evaluation_method", "pytest_exit_code_zero"),
            setup_requirements=tuple(value.get("setup_requirements", ())),
            difficulty=value.get("difficulty"),
            evaluator_id=evaluator_id,
            evaluator_command=evaluator_command,
            retrieval_relevance=value.get("retrieval_relevance"),
        )


@dataclass(frozen=True)
class Variant:
    variant_id: str
    cli_mode: str
    uses_repomind: bool = False


VARIANTS: tuple[Variant, ...] = (
    Variant("single", "single"),
    Variant("multi_agent", "multi"),
    Variant("multi_agent_mcp", "multi-mcp"),
    Variant("multi_agent_mcp_repomind", "multi-mcp-repomind", True),
)
DEFAULT_ORDER_SEED = 20261008
ORDER_STRATEGY = "seeded_counterbalanced_permutations_v1"


@dataclass(frozen=True)
class ScheduledRun:
    task: BenchmarkTask
    variant: Variant
    repetition: int
    order_seed: int
    order_index: int


@dataclass(frozen=True)
class RunRecord:
    task_id: str
    repository_id: str
    repository_revision: str
    variant: str
    status: str
    success: bool
    final_test_status: str
    repair_attempts: int | None
    tool_calls: int | None
    wall_clock_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    failure_reason: str | None = None
    retrieval_calls: int | None = None
    retrieval_latency_ms: float | None = None
    retrieved_evidence_count: int | None = None
    retrieved_source_ids: tuple[str, ...] | None = None
    retrieval_errors: int | None = None
    task_manifest_sha256: str = ""
    raw_return_code: int | None = None
    raw_stdout: str = ""
    raw_stderr: str = ""
    final_evaluator_status: str = "not_configured"
    evaluator_return_code: int | None = None
    evaluator_stdout: str = ""
    evaluator_stderr: str = ""
    mcp_tool_latency_ms: float | None = None
    retrieval_call_latency_ms: float | None = None
    retrieval_status: str | None = None
    mcp_tool_calls: int | None = None
    run_id: str = ""
    repetition: int = 1
    order_seed: int | None = None
    order_index: int | None = None


def manifest_sha256(path: str | Path) -> str:
    """Hash the exact frozen manifest bytes (including line endings)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_tasks(path: str | Path) -> tuple[list[BenchmarkTask], str]:
    raw = Path(path).read_bytes()
    payload = json.loads(raw)
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Task manifest must contain a non-empty tasks array")
    parsed = [BenchmarkTask.from_dict(task) for task in tasks]
    ids = [task.task_id for task in parsed]
    if len(set(ids)) != len(ids):
        raise ValueError("task_id values must be unique")
    return parsed, hashlib.sha256(raw).hexdigest()


def materialize_clean_workspace(
    task: BenchmarkTask,
    destination: str | Path,
    *,
    git_runner: Callable[..., Any] = subprocess.run,
) -> Path:
    """Create a new independent clone checked out at the task's exact revision."""
    target = Path(destination).resolve()
    if target.exists():
        raise FileExistsError(f"Benchmark workspace already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    source = task.repository_source
    if "://" not in source and not Path(source).is_absolute():
        source = str((Path(__file__).resolve().parents[3] / source).resolve())
    local_source = Path(source) if "://" not in source else None
    if local_source is not None and local_source.is_dir() and (local_source / ".git").exists():
        # Windows Git's local clone path may require launching bundled sh.exe.
        # A full copy preserves a fresh independent checkout and avoids hardlinks.
        shutil.copytree(local_source, target, copy_function=shutil.copy2)
    else:
        git_runner(
            ["git", "clone", "--no-hardlinks", "--no-checkout", source, str(target)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    git_runner(
        ["git", "-C", str(target), "checkout", "--detach", task.repository_revision],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    head = git_runner(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    if head != task.repository_revision:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError(f"Workspace revision mismatch: expected {task.repository_revision}, got {head}")
    status = git_runner(
        ["git", "-C", str(target), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    if status:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("New benchmark workspace is not clean")
    return target


class BenchmarkHarness:
    """Runs one existing CLI variant in one isolated task workspace."""

    def __init__(
        self,
        *,
        model_name: str,
        max_tool_calls: int,
        max_repair_attempts: int,
        test_timeout_seconds: int,
        repomind_base_url: str | None = None,
        repository_uuid_by_id: dict[str, str] | None = None,
        evaluator_root: str | Path | None = None,
        process_runner: Callable[..., Any] = subprocess.run,
    ):
        if max_tool_calls < 1 or max_repair_attempts < 0 or test_timeout_seconds < 1:
            raise ValueError("Tool budget, repair budget, or test timeout is invalid")
        self.model_name = model_name
        self.max_tool_calls = max_tool_calls
        self.max_repair_attempts = max_repair_attempts
        self.test_timeout_seconds = test_timeout_seconds
        self.repomind_base_url = repomind_base_url
        self.repository_uuid_by_id = repository_uuid_by_id or {}
        self.evaluator_root = (
            Path(evaluator_root).resolve() if evaluator_root
            else Path(__file__).resolve().parents[3] / "benchmark" / "evaluators"
        )
        self.process_runner = process_runner

    def run(
        self,
        task: BenchmarkTask,
        variant: Variant,
        workspace: str | Path,
        *,
        task_manifest_hash: str,
        api_key: str | None,
        run_id: str | None = None,
        repetition: int = 1,
        order_seed: int | None = None,
        order_index: int | None = None,
    ) -> RunRecord:
        started = time.perf_counter()
        run_id = run_id or str(uuid.uuid4())
        command = [
            sys.executable, "-m", "flagship.cli", "run",
            "--mode", variant.cli_mode,
            "--task", task.task_description,
            "--repo", str(Path(workspace).resolve()),
            "--test-command", task.test_command,
        ]
        env = os.environ.copy()
        env.update({
            "FLAGSHIP_MODEL": self.model_name,
            "FLAGSHIP_MAX_TOOL_CALLS": str(self.max_tool_calls),
            "FLAGSHIP_MAX_REPAIR_ATTEMPTS": str(self.max_repair_attempts),
            "FLAGSHIP_MAX_CODING_ATTEMPTS": str(self.max_repair_attempts + 1),
            "FLAGSHIP_TEST_TIMEOUT_SECONDS": str(min(self.test_timeout_seconds, task.timeout_seconds)),
        })
        flagship_src = str(Path(__file__).resolve().parents[2])
        prior_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = flagship_src + (os.pathsep + prior_pythonpath if prior_pythonpath else "")
        if api_key:
            env["OPENAI_API_KEY"] = api_key
        else:
            env.pop("OPENAI_API_KEY", None)
        if variant.uses_repomind:
            repo_uuid = self.repository_uuid_by_id.get(task.repository_id)
            if not self.repomind_base_url or not repo_uuid:
                return self._failure(task, variant, started, task_manifest_hash,
                                     "configuration_error", "RepoMind URL/UUID missing", run_id,
                                     repetition, order_seed, order_index)
            command.extend(["--repository-id", repo_uuid, "--repomind-base-url", self.repomind_base_url])
            env["REPOMIND_BASE_URL"] = self.repomind_base_url
            env["REPOMIND_REPOSITORY_ID"] = repo_uuid
        try:
            completed = self.process_runner(
                command,
                cwd=str(Path(workspace).resolve()),
                env=env,
                capture_output=True,
                text=True,
                timeout=task.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return RunRecord(
                task.task_id, task.repository_id, task.repository_revision, variant.variant_id,
                "timeout", False, "timeout", None, None, time.perf_counter() - started,
                failure_reason=f"Task exceeded {task.timeout_seconds}s wall-clock timeout",
                task_manifest_sha256=task_manifest_hash,
                raw_stdout=_text(exc.stdout), raw_stderr=_text(exc.stderr),
                run_id=run_id, repetition=repetition, order_seed=order_seed, order_index=order_index,
            )
        except Exception as exc:  # Keep infrastructure/model failures in the result set.
            return self._failure(task, variant, started, task_manifest_hash,
                                 "harness_error", f"{type(exc).__name__}: {exc}", run_id,
                                 repetition, order_seed, order_index)
        elapsed = time.perf_counter() - started
        record = self._record_completed(task, variant, completed, elapsed, task_manifest_hash)
        record = replace(record, run_id=run_id, repetition=repetition,
                         order_seed=order_seed, order_index=order_index)
        if not task.evaluator_id:
            return record
        return self._run_hidden_evaluator(task, variant, workspace, env, record, started)

    def _run_hidden_evaluator(self, task, variant, workspace, env, record, started):
        evaluator = (self.evaluator_root / task.evaluator_id / "test_acceptance.py").resolve()
        if not evaluator.is_relative_to(self.evaluator_root) or not evaluator.is_file():
            return replace(record, status="evaluator_unavailable", success=False,
                           final_evaluator_status="unavailable",
                           failure_reason=f"Hidden evaluator {task.evaluator_id!r} is unavailable")
        workspace_path = Path(workspace).resolve()
        if evaluator.is_relative_to(workspace_path):
            return replace(record, status="evaluator_exposed", success=False,
                           final_evaluator_status="isolation_error",
                           failure_reason="Hidden evaluator must be outside the agent workspace")
        evaluator_env = env.copy()
        source_path = str(workspace_path / "src")
        old_path = evaluator_env.get("PYTHONPATH", "")
        evaluator_env["PYTHONPATH"] = source_path + (os.pathsep + old_path if old_path else "")
        evaluator_env["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, "-m", "pytest", "-q", str(evaluator)]
        try:
            evaluated = self.process_runner(
                command, cwd=str(workspace_path), env=evaluator_env,
                capture_output=True, text=True, timeout=task.timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return replace(record, status="evaluator_timeout", success=False,
                           wall_clock_seconds=time.perf_counter() - started,
                           final_evaluator_status="timeout", failure_reason="Hidden evaluator timed out",
                           evaluator_stdout=_text(exc.stdout)[-12000:],
                           evaluator_stderr=_text(exc.stderr)[-12000:])
        except Exception as exc:
            return replace(record, status="evaluator_error", success=False,
                           wall_clock_seconds=time.perf_counter() - started,
                           final_evaluator_status="error", failure_reason=f"{type(exc).__name__}: {exc}")
        evaluator_stdout, evaluator_stderr = _text(evaluated.stdout), _text(evaluated.stderr)
        passed = evaluated.returncode == 0
        return replace(
            record,
            status=("completed" if record.raw_return_code == 0 else "agent_failed") if passed else "evaluator_failed",
            success=passed,
            final_evaluator_status="passed" if passed else "failed",
            evaluator_return_code=evaluated.returncode,
            evaluator_stdout=evaluator_stdout[-12000:],
            evaluator_stderr=evaluator_stderr[-12000:],
            wall_clock_seconds=time.perf_counter() - started,
            failure_reason=None if passed else "Hidden evaluator failed",
        )

    @staticmethod
    def _failure(task, variant, started, manifest_hash, status, reason,
                 run_id="", repetition=1, order_seed=None, order_index=None):
        return RunRecord(
            task.task_id, task.repository_id, task.repository_revision, variant.variant_id,
            status, False, status, None, None, time.perf_counter() - started,
            failure_reason=reason, task_manifest_sha256=manifest_hash, run_id=run_id,
            repetition=repetition, order_seed=order_seed, order_index=order_index,
        )

    @staticmethod
    def _record_completed(task, variant, completed, elapsed, manifest_hash):
        stdout = _text(completed.stdout)
        stderr = _text(completed.stderr)
        try:
            payload = json.loads(stdout)
        except (json.JSONDecodeError, TypeError):
            return RunRecord(
                task.task_id, task.repository_id, task.repository_revision, variant.variant_id,
                "invalid_agent_result", False, "invalid_agent_result", None, None, elapsed,
                failure_reason="CLI did not return a JSON run result",
                task_manifest_sha256=manifest_hash, raw_return_code=completed.returncode,
                raw_stdout=stdout[-12000:], raw_stderr=stderr[-12000:],
            )
        if not isinstance(payload, dict) or not {"mode", "status", "success"}.issubset(payload):
            return RunRecord(
                task.task_id, task.repository_id, task.repository_revision, variant.variant_id,
                "invalid_agent_result", False, "invalid_agent_result", None, None, elapsed,
                failure_reason="CLI JSON omitted required run-result fields",
                task_manifest_sha256=manifest_hash, raw_return_code=completed.returncode,
                raw_stdout=stdout[-12000:], raw_stderr=stderr[-12000:],
            )
        test_states = []
        for test in payload.get("tests", ()):
            test_states.append(bool(test.get("success")))
        single = payload.get("single_agent")
        if isinstance(single, dict):
            # Single-agent run success is gated on its final pytest call in CodingAgent.
            test_states.append(bool(payload.get("success")))
        latest_test_passed = test_states[-1] if test_states else False
        status = payload.get("status", "unknown")
        success = latest_test_passed and completed.returncode == 0
        retrieval_entries = [entry for entry in payload.get("audit", ()) if entry.get("provider") == "repomind"]
        retrieval_errors = sum(not entry.get("success", False) for entry in retrieval_entries)
        retrieval_wall_latency = sum(float(entry.get("latency_ms", 0.0) or 0.0) for entry in retrieval_entries)
        mcp_latency = sum(float(entry.get("latency_ms", 0.0) or 0.0)
                          for entry in payload.get("audit", ()) if entry.get("provider") == "mcp")
        retrieval_latency = payload.get("retrieval_latency_ms")
        planner = payload.get("planner")
        evidence_batches = planner.get("retrieval_evidence", ()) if isinstance(planner, dict) else ()
        evidence_rows = [
            row
            for batch in evidence_batches if isinstance(batch, dict)
            for row in batch.get("results", ()) if isinstance(row, dict)
        ]
        source_ids = tuple(dict.fromkeys(
            row["source_id"] for row in evidence_rows
            if isinstance(row.get("source_id"), str) and row["source_id"]
        ))
        return RunRecord(
            task.task_id, task.repository_id, task.repository_revision, variant.variant_id,
            "completed" if completed.returncode == 0 else "agent_failed",
            success,
            "passed" if latest_test_passed else ("failed" if test_states else "not_run"),
            payload.get("repair_attempts"), payload.get("tool_calls"), elapsed,
            input_tokens=payload.get("input_tokens"), output_tokens=payload.get("output_tokens"),
            total_tokens=payload.get("total_tokens"),
            failure_reason=None if success else str(payload.get("message") or status),
            retrieval_calls=len(retrieval_entries) if variant.uses_repomind else None,
            retrieval_latency_ms=retrieval_latency if variant.uses_repomind else None,
            retrieved_evidence_count=len(evidence_rows) if variant.uses_repomind else None,
            retrieved_source_ids=source_ids if variant.uses_repomind else None,
            retrieval_errors=retrieval_errors if variant.uses_repomind else None,
            mcp_tool_latency_ms=mcp_latency,
            mcp_tool_calls=sum(entry.get("provider") == "mcp" for entry in payload.get("audit", ())),
            retrieval_call_latency_ms=retrieval_wall_latency if variant.uses_repomind else None,
            retrieval_status=("not_attempted" if not retrieval_entries else
                              "error" if retrieval_errors == len(retrieval_entries) else
                              "partial_error" if retrieval_errors else
                              "empty" if not evidence_rows else "success") if variant.uses_repomind else None,
            task_manifest_sha256=manifest_hash,
            raw_return_code=completed.returncode,
            raw_stdout=stdout[-12000:], raw_stderr=stderr[-12000:],
        )

    @staticmethod
    def write_record(path: str | Path, record: RunRecord) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def deterministic_run_order(tasks: list[BenchmarkTask]) -> list[tuple[BenchmarkTask, Variant]]:
    """Return a seeded, position-counterbalanced schedule for one repetition."""
    return [(item.task, item.variant) for item in deterministic_run_schedule(tasks)]


def deterministic_run_schedule(
    tasks: list[BenchmarkTask], *, seed: int = DEFAULT_ORDER_SEED, repetitions: int = 1,
) -> list[ScheduledRun]:
    """Schedule all variants once per task/repetition with balanced positions.

    A seeded permutation of all variant orderings guarantees that, for each
    complete block of ``len(VARIANTS)!`` tasks, every variant occupies every
    position equally often. Task order and permutation selection are repeatable.
    The returned order_index is one-based across the complete schedule.
    """
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    rng = random.Random(seed)
    permutations = list(itertools.permutations(VARIANTS))
    ordered_tasks = list(tasks)
    rng.shuffle(ordered_tasks)
    schedule = []
    for repetition in range(1, repetitions + 1):
        orderings = list(permutations)
        rng.shuffle(orderings)
        for task_index, task in enumerate(ordered_tasks):
            ordering = orderings[task_index % len(orderings)]
            for variant in ordering:
                schedule.append(ScheduledRun(task, variant, repetition, seed, len(schedule) + 1))
    return schedule


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
