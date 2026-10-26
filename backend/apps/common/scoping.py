"""Helpers for scoping academic data to the authenticated student's department."""


def student_department_id(user) -> int | None:
    """Return the department id of *user*'s student profile, if any.

    Admins, professors and anonymous callers return ``None`` so they keep the
    unscoped (full) view. Only authenticated students with a completed profile
    (department set) are scoped.
    """
    if not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "role", None) != "STUDENT":
        return None
    profile = getattr(user, "student_profile", None)
    if profile is None:
        try:
            profile = user.student_profile
        except Exception:  # noqa: BLE001 — missing related object is expected
            profile = None
    if profile is None:
        return None
    dept = getattr(profile, "department", None)
    return getattr(dept, "pk", None) or getattr(dept, "id", None)
