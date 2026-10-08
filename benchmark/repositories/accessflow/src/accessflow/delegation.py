"""Delegation scope matching used by policy callers."""
def resource_matches(granted, requested):
    """A grant matches itself, global scope, or a descendant path."""
    if granted == "*" or granted == requested: return True
    return requested.startswith(granted)
