"""Typed inputs and outputs exchanged through the orchestrator."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from flagship.types import AgentResult


@dataclass(frozen=True)
class PlannerResult:
    success: bool
    summary: str
    steps: tuple[str, ...] = ()
    likely_files: tuple[str, ...] = ()
    error: str | None = None
    retrieval_evidence: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class CoderResult:
    success: bool
    summary: str
    changed_files: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class TestResult:
    success: bool
    summary: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: str | None = None


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    NEEDS_REVISION = "NEEDS_REVISION"


@dataclass(frozen=True)
class ReviewResult:
    decision: ReviewDecision
    summary: str
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentMessage:
    role: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskRunResult:
    mode: str
    success: bool
    status: str
    message: str
    planner: PlannerResult | None = None
    coder_attempts: tuple[CoderResult, ...] = ()
    tests: tuple[TestResult, ...] = ()
    review: ReviewResult | None = None
    tool_calls: int = 0
    repair_attempts: int = 0
    mcp_tool_calls: int = 0
    mcp_tool_latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    tool_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    tool_errors: int = 0
    audit: tuple[Any, ...] = ()
    transitions: tuple[str, ...] = ()
    single_agent: AgentResult | None = None
