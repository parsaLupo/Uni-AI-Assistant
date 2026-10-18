"""DRF view mixins shared across apps (Phase 04+)."""

from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.common.errors import CONFLICT, ApiError
from apps.common.serializers import UNIQUE_CONFLICT_MESSAGE


class ConflictOnIntegrityMixin:
    """Map database constraint violations on write to the documented 409.

    Covers both single-field uniques (validators stripped by
    `ConflictModelSerializer`) and composite ones the serializer never checks
    (`(faculty, code)`, `(course, term, section_code)`, `(student, offering)`).
    The inner atomic block saves the surrounding transaction — without it an
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
