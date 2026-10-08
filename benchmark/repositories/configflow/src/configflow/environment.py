"""Environment value parsing kept separate from file loading."""
from .paths import set_nested
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

def parse_bool(value):
    """Parse a bool or conventional textual boolean."""
    if isinstance(value, bool):
        return value
    return bool(value)

def environment_layer(environ, prefix="APP__"):
    """Map prefixed double-underscore keys into a nested dictionary."""
    result = {}
    for key, value in environ.items():
        if key.startswith(prefix):
            parts = key[len(prefix):].lower().split("__")
            set_nested(result, ".".join(parts), value)
    return result
