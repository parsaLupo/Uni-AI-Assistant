"""Conversation persistence models for Phase 09/10."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-updated_at", "-created_at")
        indexes = [models.Index(fields=("user", "-updated_at"))]

    def __str__(self) -> str:
        return self.title or f"Conversation {self.pk}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"
        SYSTEM = "SYSTEM", "System"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    retrieval_mode = models.CharField(max_length=32, blank=True, default="")
    insufficient_evidence = models.BooleanField(default=False)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        indexes = [models.Index(fields=("conversation", "created_at"))]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"


class MessageSource(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    document_chunk = models.ForeignKey(
        "documents.DocumentChunk",
        on_delete=models.CASCADE,
        related_name="message_sources",
    )
    source_label = models.CharField(max_length=255, blank=True, default="")
    relevance_score = models.FloatField(default=0.0)
    citation_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        indexes = [models.Index(fields=("message",))]

    def __str__(self) -> str:
        return f"Source for message {self.message_id}"

