"""Immutable input rows and output summaries."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Sample:
    timestamp: int
    group: str
    value: float | None

@dataclass(frozen=True)
class Summary:
    group: str
    count: int
    total: float
    mean: float
