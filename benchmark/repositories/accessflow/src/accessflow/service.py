"""Authorization and workflow operations with audit output."""
from .audit import audit_snapshot
from .models import AuditRecord
from .policy import is_allowed
from .workflow import transition

class AccessService:
    def __init__(self, grants=(), role_parents=None):
        self.grants = tuple(grants); self.role_parents = role_parents or {}; self.audit = []
    def authorize(self, principal, action, resource, now=None):
        allowed = is_allowed(principal, action, resource, self.grants, self.role_parents, now)
        self.audit.append(AuditRecord(principal.name, action, resource, allowed))
        return allowed
    def audit_snapshot(self): return audit_snapshot(self.audit)
    def change_state(self, state, target): return transition(state, target)
