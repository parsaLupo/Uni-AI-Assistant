# ADR-005 — Hybrid Structured Query + RAG

## Status

Accepted

## Decision

Do not route every university question through RAG. Use structured PostgreSQL queries for normalized facts and RAG for unstructured documents; combine them for hybrid questions.

## Reasoning

Exam times, course offerings, and professor assignments are more reliable and deterministic when queried directly from structured records. Regulations and manuals are naturally document-based.

## Consequences

The system needs a question router and multiple retrieval paths, but factual reliability and traceability improve.
