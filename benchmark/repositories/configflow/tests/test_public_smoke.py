from configflow.environment import parse_bool
from configflow.merge import merge_layers
from configflow.paths import set_nested
from configflow.profiles import resolve_profile
from configflow.secrets import redact_mapping
from configflow.service import load_settings
from configflow.validation import validate_port

def test_nominal_configuration_paths():
    assert parse_bool(True) is True
    assert validate_port("8080") == 8080
    assert merge_layers({"debug": False}, {}, {})["debug"] is False
    assert load_settings({"port": 8080, "timeout": 5}, {}, {})["port"] == 8080
    assert set_nested({}, "host", "localhost")["host"] == "localhost"
    assert resolve_profile("base", {"base": {"timeout": 5}})["timeout"] == 5
    assert redact_mapping({"password": "x"})["password"] == "[REDACTED]"
