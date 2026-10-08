"""Small immutable data models used at service boundaries."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Ticket:
    ticket_id: int
    title: str
    status: str = "open"
    tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class Event:
    ticket_id: int
    kind: str
    sequence: int
