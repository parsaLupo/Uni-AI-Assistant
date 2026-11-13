"""Conversation serializers (Phase 10)."""

from __future__ import annotations

from apps.conversations.models import Conversation, Message, MessageSource
from rest_framework import serializers


class MessageSourceSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(source="document_chunk.document_id", read_only=True)
    page = serializers.IntegerField(source="document_chunk.page_number", read_only=True)
    section = serializers.CharField(source="document_chunk.section_title", read_only=True)

    class Meta:
        model = MessageSource
        fields = [
            "id",
            "document_id",
            "source_label",
            "page",
            "section",
            "relevance_score",
            "citation_text",
            "created_at",
        ]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    sources = MessageSourceSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "role",
            "content",
            "retrieval_mode",
            "insufficient_evidence",
            "latency_ms",
            "created_at",
            "sources",
        ]
        read_only_fields = [
            "id",
            "conversation",
            "role",
            "content",
            "retrieval_mode",
            "insufficient_evidence",
            "latency_ms",
            "created_at",
            "sources",
        ]


class ConversationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "archived_at"]
        read_only_fields = fields


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "archived_at", "messages"]
        read_only_fields = fields


class ConversationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
