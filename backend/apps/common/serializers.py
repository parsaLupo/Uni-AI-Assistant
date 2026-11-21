"""Serializer descriptions of the baseline response contract.

These do not serve data; they give the generated OpenAPI schema (ADR-012) real
shapes so `openapi.yaml` documents what the API actually returns:

* the one error envelope every endpoint must use (`docs/04-api-specification.md`
  section 3, codes from `docs/12-error-handling-observability.md` section 1),
* the health payload (`docs/09-deployment.md` section 7).
"""

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField(
        help_text="Machine-readable code from docs/12-error-handling-observability.md."
    )
    message = serializers.CharField(
        help_text="Human-readable, Persian message (ADR-010); never an internal detail."
    )
    details = serializers.DictField(
        required=False,
        help_text="Field-level errors or machine-readable metadata.",
    )


class ErrorEnvelopeSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()


class HealthChecksSerializer(serializers.Serializer):
    database = serializers.CharField(help_text="'ok' or 'unavailable'.")
    database_latency_ms = serializers.FloatField(allow_null=True)
    ai_provider = serializers.CharField(
        help_text="Provider availability; 'not_configured' until the AI phase (ADR-006)."
    )


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()
    request_id = serializers.CharField(help_text="Correlation id (docs/12 section 4).")
    checks = HealthChecksSerializer()


class HealthLiveResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()
    request_id = serializers.CharField(help_text="Correlation id (docs/12 section 4).")


class HealthReadyChecksSerializer(serializers.Serializer):
    database = serializers.CharField(help_text="'ok' or 'unavailable'.")
    database_latency_ms = serializers.FloatField(allow_null=True)


class HealthReadyResponseSerializer(HealthLiveResponseSerializer):
    checks = HealthReadyChecksSerializer()


class HealthDependencyStatusSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="'ok', 'unavailable', 'degraded' or 'eager'.")
    latency_ms = serializers.FloatField(allow_null=True, required=False)


class HealthWorkerStatusSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="'ok', 'unavailable' or 'eager'.")


class HealthDeepChecksSerializer(serializers.Serializer):
    database = HealthDependencyStatusSerializer()
    redis = HealthDependencyStatusSerializer()
    worker = HealthWorkerStatusSerializer()
    storage = HealthWorkerStatusSerializer()
    ai_provider = HealthWorkerStatusSerializer()


class HealthDeepResponseSerializer(HealthLiveResponseSerializer):
    checks = HealthDeepChecksSerializer()


# --- Phase 04 write-path contract -------------------------------------------

UNIQUE_CONFLICT_MESSAGE = "این مقدار قبلاً ثبت شده است؛ شناسه/کد باید یکتا باشد."


class ConflictModelSerializer(serializers.ModelSerializer):
    """ModelSerializer with generated UniqueValidators removed (→ 409 path).

    `docs/api/admin.md` requires uniqueness conflicts to return
    `409 CONFLICT`, but ModelSerializer injects `UniqueValidator`, which
    field-level errors or machine-readable metadata (the Phase 03 duplicate-email
    bug — accounts silenced it per field; Phase 04 generalizes). The database
    constraint becomes the single source of truth; views convert its
    `IntegrityError` with `common.mixins.ConflictOnIntegrityMixin`. Composite
    uniques bring a `UniqueTogetherValidator`, which additionally breaks PATCH
    (it demands every key field on partial updates) — stripped for the same
    reason.
    """

    def get_validators(self):
        # Composite uniques (`(faculty, code)`, `(student, offering)`) come as
        # UniqueTogetherValidator from ModelSerializer and would also break
        # PATCH (they demand every key field on partial updates) — the database
        # decides instead, via ConflictOnIntegrityMixin → 409.
        return [
            v
            for v in super().get_validators()
            if not isinstance(v, (UniqueValidator, UniqueTogetherValidator))
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.validators = [
                v
                for v in field.validators
                if not isinstance(v, (UniqueValidator, UniqueTogetherValidator))
            ]

