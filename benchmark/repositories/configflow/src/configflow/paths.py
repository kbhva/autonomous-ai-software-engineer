"""Nested settings path operations."""
def set_nested(values, dotted_key, value):
    """Set a dotted key, creating intermediate dictionaries when needed."""
    parts = dotted_key.split(".")
    if not parts or any(not part for part in parts):
        raise ValueError("setting path contains an empty component")
    cursor = values
    for part in parts[:-1]:
        child = cursor.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"{part!r} is not a mapping")
        cursor = child
    values[parts[-1]] = value
    return values
