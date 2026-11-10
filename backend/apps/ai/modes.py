"""Execution modes for the Phase 09 question router."""

from __future__ import annotations

from enum import Enum


class ExecutionMode(str, Enum):
    STRUCTURED = "STRUCTURED"
    RAG = "RAG"
    HYBRID = "HYBRID"
    GENERAL = "GENERAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
