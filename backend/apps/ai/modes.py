"""Execution modes for the Phase 09 question router."""

from __future__ import annotations

from enum import Enum


# UP042 (StrEnum) is intentionally not applied: `str` inheritance keeps
# `.value` serialisation to the DB/API while raw strings compare equal.
class ExecutionMode(str, Enum):  # noqa: UP042
    STRUCTURED = "STRUCTURED"
    RAG = "RAG"
    HYBRID = "HYBRID"
    GENERAL = "GENERAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
