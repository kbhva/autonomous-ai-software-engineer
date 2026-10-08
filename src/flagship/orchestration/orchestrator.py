"""Deterministic PLAN → CODE → TEST → REVIEW state machine."""

from dataclasses import replace
from enum import Enum
from typing import Any

from flagship.agents import Coder, Planner, Reviewer, Tester
from flagship.agents.messages import (AgentMessage, CoderResult, PlannerResult,
                                      ReviewDecision, ReviewResult, TaskRunResult, TestResult)
from flagship.agents.runtime import ToolBudgetExceeded, ToolExecutor


class State(str, Enum):
    PLAN = "PLAN"
    CODE = "CODE"
    TEST = "TEST"
    REVIEW = "REVIEW"
    DONE = "DONE"
    FAILED = "FAILED"


class Orchestrator:
    def __init__(self, model: Any, tools: Any, max_tool_calls: int = 20,
                 max_coding_attempts: int = 3, mode: str = "multi", repository_id: str | None = None):
        if max_coding_attempts < 1:
            raise ValueError("max_coding_attempts must be positive")
        self.model = model
        self.executor = ToolExecutor(tools, max_tool_calls)
        self.max_coding_attempts = max_coding_attempts
        self.mode = mode
        self.repository_id = repository_id

    def run(self, task: str) -> TaskRunResult:
        states: list[str] = [State.PLAN.value]
        planner = Planner(self.model, self.executor, self.repository_id).run(AgentMessage("Planner", task))
        if not planner.success:
            return self._result(False, State.FAILED, f"Planning failed: {planner.error}", planner, states)
        coders: list[CoderResult] = []
        test_results: list[TestResult] = []
        review: ReviewResult | None = None
        feedback: list[dict[str, Any]] = []
        tester = Tester(self.executor)
        reviewer = Reviewer(self.model, self.executor)

        for attempt in range(1, self.max_coding_attempts + 1):
            states.append(State.CODE.value)
            before_writes = len(self.executor.written_files)
            coder = Coder(self.model, self.executor).run(AgentMessage(
                "Coder", task, {"plan": planner, "attempt": attempt, "previous_feedback": feedback}))
            actual_files = tuple(self.executor.written_files[before_writes:])
            if coder.success and actual_files:
                coder = replace(coder, changed_files=tuple(dict.fromkeys((*coder.changed_files, *actual_files))))
            coders.append(coder)

            states.append(State.TEST.value)
            test_result = tester.run()
            test_results.append(test_result)
            if not coder.success:
                feedback = [{"kind": "coder_error", "message": coder.error}]
                if attempt < self.max_coding_attempts and len(self.executor.audit) < self.executor.max_tool_calls:
                    continue
                return self._result(False, State.FAILED, f"Coding failed: {coder.error}", planner, states,
                                    coders, test_results, review)

            states.append(State.REVIEW.value)
            review = reviewer.run(AgentMessage("Reviewer", task, {
                "plan": planner, "coder": coder, "tests": test_result,
                "attempt": attempt,
            }))
            if review.decision is ReviewDecision.APPROVED and test_result.success:
                states.append(State.DONE.value)
                return self._result(True, State.DONE, review.summary, planner, states, coders, test_results, review)
            if review.decision is ReviewDecision.APPROVED and not test_result.success:
                feedback = [{"kind": "test_failure", "summary": test_result.summary,
                             "stdout": test_result.stdout, "stderr": test_result.stderr}]
            else:
                feedback = [{"kind": "review", "summary": review.summary, "issues": review.issues,
                             "tests": test_result}]
            if attempt == self.max_coding_attempts:
                return self._result(False, State.FAILED, "Maximum coding attempts reached with revisions still required.",
                                    planner, states, coders, test_results, review)
            if len(self.executor.audit) >= self.executor.max_tool_calls:
                return self._result(False, State.FAILED, "Total tool-call budget exhausted before another coding attempt.",
                                    planner, states, coders, test_results, review)

        return self._result(False, State.FAILED, "Workflow ended unexpectedly.", planner, states, coders, test_results, review)

    def _result(self, success: bool, state: State, message: str, planner: PlannerResult,
                states: list[str], coders: list[CoderResult] | None = None,
                tests: list[TestResult] | None = None, review: ReviewResult | None = None) -> TaskRunResult:
        return TaskRunResult(self.mode, success, state.value, message, planner,
                             coder_attempts=tuple(coders or ()), tests=tuple(tests or ()), review=review,
                             tool_calls=len(self.executor.audit), repair_attempts=max(0, len(coders or ()) - 1),
                             mcp_tool_calls=self.executor.mcp_tool_calls,
                             mcp_tool_latency_ms=self.executor.mcp_tool_latency_ms,
                             input_tokens=(self.model.input_tokens if getattr(self.model, "usage_available", False) else None),
                             output_tokens=(self.model.output_tokens if getattr(self.model, "usage_available", False) else None),
                             total_tokens=(self.model.total_tokens if getattr(self.model, "usage_available", False) else None),
                             tool_latency_ms=self.executor.tool_latency_ms,
                             retrieval_latency_ms=self.executor.retrieval_latency_ms,
                             tool_errors=self.executor.tool_errors,
                             audit=tuple(self.executor.audit),
                             transitions=tuple(states))
