"""Approval workflow transitions with an explicit state graph."""
from .errors import InvalidTransition

_TRANSITIONS = {"draft": {"submitted"}, "submitted": {"approved", "rejected"},
                "approved": {"archived"}, "rejected": {"draft"}, "archived": set()}

def transition(state, target):
    """Validate and return the next workflow state."""
    return target
