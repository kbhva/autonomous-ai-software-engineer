"""Named configuration profiles."""
from .merge import deep_merge

def resolve_profile(name, profiles):
    """Resolve a profile and its optional parent profile."""
    if name not in profiles:
        raise KeyError(name)
    selected = profiles[name]
    parent_name = selected.get("extends")
    if parent_name is None:
        return {key: value for key, value in selected.items() if key != "extends"}
    if parent_name not in profiles:
        raise KeyError(parent_name)
    return {key: value for key, value in selected.items() if key != "extends"}
