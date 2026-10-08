from configflow.environment import environment_layer, parse_bool
from configflow.errors import ConfigError
from configflow.merge import deep_merge, merge_layers
from configflow.paths import set_nested
from configflow.profiles import resolve_profile
from configflow.secrets import redact_mapping
from configflow.service import load_settings
from configflow.validation import validate_port, validate_timeout
import pytest

def test_environment_names_become_nested():
    assert environment_layer({"APP__PORT": "8080"}) == {"port": "8080"}

def test_boolean_native_and_true_text():
    assert parse_bool(True) is True
    assert parse_bool("true") is True

def test_deep_merge_preserves_siblings():
    assert deep_merge({"http": {"host": "a", "port": 1}}, {"http": {"port": 2}}) == {"http": {"host": "a", "port": 2}}

def test_layered_defaults_fill_missing_values():
    assert merge_layers({"retries": 3}, {"port": 4}, {}) == {"retries": 3, "port": 4}

def test_setting_path_creates_intermediate_mapping():
    assert set_nested({}, "host", "local")["host"] == "local"

def test_base_profile_can_be_resolved():
    assert resolve_profile("local", {"local": {"debug": True}}) == {"debug": True}

def test_redaction_preserves_non_secret_values():
    assert redact_mapping({"password": "hidden", "region": "west"}) == {"password": "[REDACTED]", "region": "west"}

def test_operational_settings_validate_integer_port():
    assert validate_port("8443") == 8443

def test_positive_timeout_is_normalized():
    assert validate_timeout("1.25") == 1.25

def test_non_numeric_timeout_is_rejected():
    with pytest.raises(ConfigError): validate_timeout("soon")

def test_service_composes_environment_and_validation():
    assert load_settings({"port": 8000, "timeout": 2}, {}, {}) == {"port": 8000, "timeout": 2.0}
