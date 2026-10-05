"""Serializer descriptions of the baseline response contract.

These do not serve data; they give the generated OpenAPI schema (ADR-012) real
shapes so `openapi.yaml` documents what the API actually returns:

* the one error envelope every endpoint must use (`docs/04-api-specification.md`
  section 3, codes from `docs/12-error-handling-observability.md` section 1),
* the health payload (`docs/09-deployment.md` section 7).
"""

from rest_framework import serializers


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
