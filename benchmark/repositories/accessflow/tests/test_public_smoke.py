from accessflow.models import Grant, Principal
from accessflow.policy import is_allowed
from accessflow.service import AccessService
from accessflow.workflow import transition

def test_public_authorization_and_workflow():
    user = Principal("sam", ("reader",))
    assert is_allowed(user, "read", "doc", [Grant("reader", "read", "doc")])
    assert transition("draft", "submitted") == "submitted"
    service = AccessService([Grant("reader", "read", "doc")])
    assert service.authorize(user, "read", "doc") is True
    assert len(service.audit) == 1
