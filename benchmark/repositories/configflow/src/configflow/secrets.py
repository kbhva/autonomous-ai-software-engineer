"""Safe display helpers for settings and diagnostics."""
_SECRET_NAMES = {"password", "token", "secret", "api_key"}

def redact_mapping(values):
    """Copy a mapping while replacing values whose key names are sensitive."""
    return {key: ("[REDACTED]" if key.lower() in _SECRET_NAMES else value)
            for key, value in values.items()}
