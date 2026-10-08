"""Validate local repository baselines and hidden task evaluators without agents."""

from __future__ import annotations

import json
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOS = ROOT / "repositories"
EVALUATORS = ROOT / "evaluators"
REFERENCES = ROOT / "reference_fixes"
MANIFEST = ROOT / "tasks" / "manifest.draft.json"
OUT = ROOT / "validation-results.json"


def invoke(args: list[str], cwd: Path, env: dict[str, str], timeout: int = 90) -> dict:
    start = time.perf_counter()
    try:
        completed = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                                   timeout=timeout, check=False)
        return {"returncode": completed.returncode, "seconds": round(time.perf_counter() - start, 4),
                "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:],
                "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        return {"returncode": None, "seconds": round(time.perf_counter() - start, 4),
                "stdout": str(exc.stdout or "")[-4000:], "stderr": str(exc.stderr or "")[-4000:],
                "timed_out": True}


def environment_for(source_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(source_root) + (os.pathsep + existing if existing else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tasks = manifest["tasks"]
    outcomes = []
    repo_results = {}
    with tempfile.TemporaryDirectory(prefix=".validation-", dir=ROOT) as tmp:
        temporary_root = Path(tmp)
        for repo_id, metadata in manifest["repositories"].items():
            repo = REPOS / repo_id
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
            status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
            tracked_files = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True).stdout.splitlines()
            source_files = [path for path in tracked_files if path.endswith(".py") and path.startswith("src/")]
            line_count = sum(len((repo / path).read_text(encoding="utf-8").splitlines()) for path in tracked_files
                             if path.endswith(".py") and path.startswith("src/"))
            test_files = [path for path in tracked_files if path.endswith(".py") and path.startswith("tests/")]
            test_line_count = sum(len((repo / path).read_text(encoding="utf-8").splitlines()) for path in test_files)
            all_python_files = [path for path in tracked_files if path.endswith(".py")]
            total_python_lines = sum(len((repo / path).read_text(encoding="utf-8").splitlines()) for path in all_python_files)
            network_modules = {"requests", "httpx", "aiohttp", "urllib", "socket", "ftplib", "smtplib"}
            network_imports = []
            for relative in all_python_files:
                tree = ast.parse((repo / relative).read_text(encoding="utf-8"), filename=relative)
                for node in ast.walk(tree):
                    names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                             else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                    for name in names:
                        if name.split(".")[0] in network_modules:
                            network_imports.append(f"{relative}:{name}")
            env = environment_for(repo / "src")
            run1 = invoke([sys.executable, "-m", "pytest", "-q"], repo, env)
            run2 = invoke([sys.executable, "-m", "pytest", "-q"], repo, env)
            repo_results[repo_id] = {
                "expected_revision": metadata["revision"], "observed_revision": head,
                "clean": status == "", "tracked_file_count": len(tracked_files),
                "python_source_file_count": len(source_files), "python_source_lines": line_count,
                "python_test_file_count": len(test_files), "python_test_lines": test_line_count,
                "total_tracked_python_lines": total_python_lines,
                "network_imports_found": network_imports,
                "public_test_command": "python -m pytest -q", "first_baseline_run": run1,
                "second_baseline_run": run2,
                "public_tests_pass_twice": run1["returncode"] == run2["returncode"] == 0,
                "deterministic_exit_status": run1["returncode"] == run2["returncode"],
            }
        for task in tasks:
            repo = REPOS / task["repository_id"]
            evaluator = EVALUATORS / task["evaluator_id"] / "test_acceptance.py"
            reference = ROOT / task["reference_path"] if task.get("reference_path") else REFERENCES / task["task_id"]
            # Private reference path is resolved by task ID, never from the agent task payload.
            reference = REFERENCES / task["task_id"]
            fixed_files = list(reference.rglob("*.py"))
            source_relatives = [path.relative_to(reference) for path in fixed_files
                                if path.relative_to(reference).as_posix().startswith("src/")]
            if len(source_relatives) != 1:
                raise AssertionError(f"Expected one private reference source for {task['task_id']}")
            repo_rel = source_relatives[0]
            evaluator_path = EVALUATORS / task["evaluator_id"] / "test_acceptance.py"
            # Each task evaluator is controller-owned and dedicated to one task.
            # Run the entire file so expanded multi-case evaluators are validated,
            # rather than filtering to a legacy single-test name.
            cmd = [sys.executable, "-m", "pytest", "-q", str(evaluator_path)]
            baseline_env = environment_for(repo / "src")
            baseline = invoke(cmd, repo, baseline_env, task["timeout_seconds"])
            task_tmp = temporary_root / task["task_id"]
            task_tmp.mkdir()
            try:
                fixed_root = task_tmp / "repo"
                shutil.copytree(repo, fixed_root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
                shutil.copy2(fixed_files[0], fixed_root / repo_rel)
                reference_env = environment_for(fixed_root / "src")
                reference_pass = invoke(cmd, fixed_root, reference_env, task["timeout_seconds"])
                reference_repeat = invoke(cmd, fixed_root, reference_env, task["timeout_seconds"])
            finally:
                shutil.rmtree(task_tmp, ignore_errors=True)
            outcomes.append({
                "task_id": task["task_id"], "repository_id": task["repository_id"],
                "evaluator_id": task["evaluator_id"], "baseline_exit": baseline["returncode"],
                "baseline_failed": baseline["returncode"] not in (0, None),
                "baseline_failed_in_test_body": bool(re.search(
                    r"^FAILED .+::", baseline["stdout"] + baseline["stderr"], re.MULTILINE
                )),
                "baseline_timed_out": baseline["timed_out"],
                "reference_exit": reference_pass["returncode"], "reference_passed": reference_pass["returncode"] == 0,
                "reference_repeat_exit": reference_repeat["returncode"],
                "reference_deterministic_exit": reference_pass["returncode"] == reference_repeat["returncode"],
                "baseline_seconds": baseline["seconds"], "reference_seconds": reference_pass["seconds"],
                "baseline_output": baseline["stdout"] + baseline["stderr"],
                "reference_output": reference_pass["stdout"] + reference_pass["stderr"],
            })
    result = {
        "status": "draft_validation_not_frozen", "python": sys.version,
        "platform": sys.platform, "repositories": repo_results, "tasks": outcomes,
        "counts": {
            "repositories": len(repo_results), "tasks": len(outcomes),
            "valid_oracle_pairs": sum(r["baseline_failed"] and r["reference_passed"] and r["reference_deterministic_exit"] for r in outcomes),
            "baseline_evaluator_failures": sum(r["baseline_failed"] for r in outcomes),
            "reference_evaluator_passes": sum(r["reference_passed"] for r in outcomes),
            "baseline_failures_in_test_body": sum(r["baseline_failed_in_test_body"] for r in outcomes),
            "public_repositories_passing_twice": sum(r["public_tests_pass_twice"] for r in repo_results.values()),
        },
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["counts"], indent=2))
    return 0 if result["counts"]["valid_oracle_pairs"] == len(outcomes) and result["counts"]["public_repositories_passing_twice"] == len(repo_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
