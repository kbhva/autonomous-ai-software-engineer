"""Role expansion using a simple local role graph."""
def expand_roles(roles, parents):
    """Return all direct and inherited roles without duplicates."""
    expanded = set(roles)
    for role in roles:
        expanded.update(parents.get(role, ()))
    return frozenset(expanded)
