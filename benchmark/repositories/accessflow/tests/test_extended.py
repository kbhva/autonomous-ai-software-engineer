from accessflow.audit import audit_snapshot
from accessflow.delegation import resource_matches
from accessflow.models import Grant, Principal
from accessflow.policy import is_allowed
from accessflow.roles import expand_roles
from accessflow.service import AccessService
from accessflow.workflow import transition

def test_direct_roles_are_retained(): assert expand_roles(("reader",), {}) == frozenset({"reader"})
def test_single_level_role_parent_is_included():
    assert expand_roles(("staff",), {"staff": ("reader",)}) == frozenset({"staff", "reader"})
def test_matching_allow_grants_access():
    assert is_allowed(Principal("sam", ("reader",)), "read", "doc", [Grant("reader", "read", "doc")])
def test_missing_grant_denies_access(): assert not is_allowed(Principal("sam"), "write", "doc", [])
def test_nonexpired_grant_is_usable_when_time_is_known():
    assert is_allowed(Principal("sam"), "read", "doc", [Grant("sam", "read", "doc", expires_at=20)], now=10)
def test_valid_transition_changes_state(): assert transition("draft", "submitted") == "submitted"
def test_exact_scope_matches_resource(): assert resource_matches("team/a", "team/a")
def test_global_scope_matches_resource(): assert resource_matches("*", "team/a")
def test_audit_snapshot_contains_all_records(): assert audit_snapshot([1, 2]) == [1, 2]
def test_service_records_authorization_decision():
    service = AccessService([Grant("reader", "read", "doc")])
    assert service.authorize(Principal("sam", ("reader",)), "read", "doc")
    assert len(service.audit) == 1
