"""Validation for operational settings."""
from .errors import ConfigError

def validate_timeout(value):
    """Require a positive numeric timeout and return it as float."""
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        raise ConfigError("timeout must be numeric") from None
    if timeout < 0:
        raise ConfigError("timeout must be non-negative")
    return timeout

def validate_port(value):
    port = int(value)
    if not 1 <= port <= 65535:
        raise ConfigError("port must be between 1 and 65535")
    return port
