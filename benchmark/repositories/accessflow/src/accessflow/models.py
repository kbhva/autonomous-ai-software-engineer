"""Immutable principals, grants and audit records."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    name: str
    roles: tuple[str, ...] = ()

@dataclass(frozen=True)
class Grant:
    subject: str
    action: str
    resource: str
    effect: str = "allow"
    expires_at: int | None = None

@dataclass(frozen=True)
class AuditRecord:
    subject: str
    action: str
    resource: str
    allowed: bool
