"""Policy evaluation over principal roles and resource grants."""
from .delegation import resource_matches
from .roles import expand_roles

def is_allowed(principal, action, resource, grants, role_parents=None, now=None):
    roles = expand_roles(principal.roles, role_parents or {})
    relevant = [g for g in grants if g.subject in roles or g.subject == principal.name]
    relevant = [g for g in relevant if g.action == action and resource_matches(g.resource, resource)
                and (g.expires_at is None or now is None or now < g.expires_at)]
    return any(g.effect == "allow" for g in relevant)
