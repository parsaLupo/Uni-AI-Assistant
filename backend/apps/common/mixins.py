"""DRF view mixins shared across apps (Phase 04+)."""

from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.common.errors import CONFLICT, ApiError
from apps.common.serializers import UNIQUE_CONFLICT_MESSAGE

_NONE_DEPT = "__none__"


class DepartmentScopedMixin:
    """Scope queryset to the calling student's department.

    - STUDENT: only rows owned by ``request.user.student_profile.department``
    - ADMIN / SUPERADMIN: no filter (see everything)
    - Student with no profile / no department: empty queryset
    - Anonymous: handled by authentication permissions before this mixin runs

    Subclasses must implement ``_filter_by_department`` to specify the
    department filter path for their model.
    """

    def _department_id(self, request):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return None
        if getattr(user, "role", None) in Role.privileged():
            return None  # admin / superadmin: no filter
        profile = getattr(user, "student_profile", None)
        if profile is None:
            try:
                profile = user.student_profile
            except Exception:  # noqa: BLE001
                profile = None
        if profile is None or getattr(profile, "department_id", None) is None:
            return _NONE_DEPT  # sentinel -> empty queryset
        return profile.department_id

    def get_queryset(self):
        qs = super().get_queryset()
        dept_id = self._department_id(self.request)
        if dept_id is None:
            return qs  # privileged: no filter
        if dept_id == _NONE_DEPT:
            return qs.none()  # student without a department sees nothing
        return self._filter_by_department(qs, dept_id)

    def _filter_by_department(self, qs, department_id):
        """Override in subclasses to specify the department filter path."""
        raise NotImplementedError


class ConflictOnIntegrityMixin:
    """Map database constraint violations on write to the documented 409.

    Covers both single-field uniques (validators stripped by
    `ConflictModelSerializer`) and composite ones the serializer never checks
    (`(faculty, code)`, `(course, term, section_code)`, `(student, offering)`).
    The inner atomic block saves the surrounding transaction - without it an
    IntegrityError would poison the test runner's outer transaction.
    """

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError as exc:
            raise ApiError(CONFLICT, UNIQUE_CONFLICT_MESSAGE, http_status=409) from exc

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().update(request, *args, **kwargs)
        except IntegrityError as exc:
            raise ApiError(CONFLICT, UNIQUE_CONFLICT_MESSAGE, http_status=409) from exc
