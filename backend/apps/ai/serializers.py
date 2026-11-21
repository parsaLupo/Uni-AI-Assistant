"""Schema-only serializers for the AI ask endpoints (ADR-012).

These do not validate requests at runtime (the views keep their existing
handling); they give drf-spectacular enough shape information to document the
contract without guessing.
"""

from __future__ import annotations

from rest_framework import serializers


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(help_text="Persian question text.")
    message_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional conversation message id to persist the routing mode on.",
    )


class AskResponseSerializer(serializers.Serializer):
    mode = serializers.CharField(
        help_text="STRUCTURED, RAG, HYBRID, GENERAL or OUT_OF_SCOPE."
    )
    answer = serializers.CharField()
    sources = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    structured_evidence = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    document_evidence = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    insufficient_evidence = serializers.BooleanField()
    evidence_conflicts = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    provider = serializers.DictField(
        help_text="Provider name/model id; never the API key."
    )
    latency_ms = serializers.IntegerField(required=False)
