"""Tester role: run only the configured pytest verifier."""

from typing import Any

from flagship.agents.messages import TestResult
from flagship.agents.runtime import ToolBudgetExceeded, ToolExecutor


class Tester:
    __test__ = False

    def __init__(self, executor: ToolExecutor):
        self.executor = executor

    def run(self) -> TestResult:
        try:
            result = self.executor.execute("run_tests", {}, ("run_tests",))
            data: dict[str, Any] = result.data
            return TestResult(result.success, result.summary, data.get("returncode"),
                              data.get("stdout", ""), data.get("stderr", ""),
                              data.get("timed_out", False), result.error)
        except ToolBudgetExceeded as exc:
            return TestResult(False, "Test run skipped: tool-call budget exhausted", error=str(exc))
        except Exception as exc:
            return TestResult(False, "Tester failed", error=str(exc))
