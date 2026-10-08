"""Layered configuration merging."""
def deep_merge(base, override):
    """Return a recursive copy where override values take precedence."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def merge_layers(defaults, file_values, environment_values):
    """Merge defaults, file values, then environment values (highest priority)."""
    return deep_merge(deep_merge(defaults, environment_values), file_values)
