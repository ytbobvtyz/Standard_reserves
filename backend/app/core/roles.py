"""Roles that share the logistics workspace."""

LOGISTICS_ROLES = ("logistics", "admin")


def has_logistics_access(role: str) -> bool:
    return role in LOGISTICS_ROLES
