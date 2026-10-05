"""Role-based permissions (docs/05 section 7, enforced server-side)."""

from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsAdmin(BasePermission):
    """ADMIN or SUPERADMIN — the default gate for /admin/* endpoints."""

    message = "این عملیات فقط برای مدیران مجاز است."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role in Role.privileged())


class IsSuperAdmin(BasePermission):
    """SUPERADMIN only — privileged role changes and privileged deactivation."""

    message = "این عملیات فقط برای مدیر ارشد مجاز است."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.SUPERADMIN)
