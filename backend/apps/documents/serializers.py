"""Document serializers (upload validation + metadata)."""

from __future__ import annotations

import hashlib
import os
import re

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.serializers import ConflictModelSerializer
from apps.documents.models import Document, DocumentStatus

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/octet-stream"}


def _sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "document.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    if not cleaned.lower().endswith(".pdf"):
        cleaned = cleaned + ".pdf"
    return cleaned or "document.pdf"


class DocumentSerializer(ConflictModelSerializer):
    uploaded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    file = serializers.FileField(write_only=True, required=True)
    file_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "document_type",
            "file",
            "file_url",
            "academic_year",
            "effective_from",
            "effective_to",
            "version",
            "status",
            "checksum",
            "storage_key",
            "processing_error",
            "failure_stage",
            "attempt_count",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "checksum",
            "storage_key",
            "processing_error",
            "failure_stage",
            "attempt_count",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    def validate_file(self, f: UploadedFile):
        if not f:
            raise serializers.ValidationError("فایل الزامی است.")
        if f.size <= 0:
            raise serializers.ValidationError("فایل خالی است.")
        if f.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("حجم فایل بیش از حد مجاز است.")
        name = f.name or ""
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("پسوند فایل مجاز نیست.")
        # MIME type check
        ct = (f.content_type or "").lower()
        if ct and "pdf" not in ct and ct not in {"application/octet-stream", ""}:
            raise serializers.ValidationError("نوع فایل مجاز نیست.")
        head = f.read(8)
        f.seek(0)
        if not head.startswith(b"%PDF"):
            raise serializers.ValidationError("فایل PDF معتبر نیست.")
        sample = f.read(65536)
        f.seek(0)
        if b"/Encrypt" in sample:
            raise serializers.ValidationError("فایل PDF رمزگذاری شده پشتیبانی نمی‌شود.")
        return f

    def validate_status(self, value):
        allowed = {c[0] for c in DocumentStatus.choices}
        if value not in allowed:
            raise serializers.ValidationError("وضعیت نامعتبر است.")
        return value

    def create(self, validated_data):
        f = validated_data.pop("file")
        # checksum
        f.seek(0)
        sha = hashlib.sha256()
        for chunk in f.chunks():
            sha.update(chunk)
        f.seek(0)

        title = validated_data.get("title", "")
        dtype = validated_data.get("document_type", "")
        if not validated_data.get("version"):
            from django.db.models import Max

            agg = Document.objects.filter(title=title, document_type=dtype).aggregate(Max("version"))
            validated_data["version"] = (agg.get("version__max") or 0) + 1

        f.name = _sanitize_filename(f.name)
        doc = Document.objects.create(
            file=f,
            checksum=sha.hexdigest(),
            storage_key=f.name,
            uploaded_by=self.context["request"].user,
            status=validated_data.pop("status", DocumentStatus.UPLOADED),
            **validated_data,
        )
        return doc

    def update(self, instance, validated_data):
        # handle supersede on activation
        new_status = validated_data.get("status")
        instance = super().update(instance, validated_data)
        if new_status == DocumentStatus.ACTIVE:
            Document.objects.filter(
                title=instance.title,
                document_type=instance.document_type,
            ).exclude(pk=instance.pk).filter(status=DocumentStatus.ACTIVE).update(
                status=DocumentStatus.SUPERSEDED
            )
        return instance