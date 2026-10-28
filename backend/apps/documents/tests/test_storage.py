"""Storage adapter tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from apps.documents.storage import LocalStorageAdapter


@pytest.mark.django_db
def test_local_storage_save_read_delete(tmp_path):
    adapter = LocalStorageAdapter(tmp_path / "store")
    key = "documents/test.pdf"
    data = b"%PDF-1.4\n%%EOF"
    returned = adapter.save(key, data)
    assert returned == key
    assert adapter.exists(key)
    assert adapter.read(key) == data
    adapter.delete(key)
    assert not adapter.exists(key)


def test_path_traversal_rejected(tmp_path):
    adapter = LocalStorageAdapter(tmp_path / "store")
    with pytest.raises(Exception):
        adapter.save("../evil.pdf", b"x")
