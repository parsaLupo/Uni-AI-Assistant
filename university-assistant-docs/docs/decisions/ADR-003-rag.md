# ADR-003 — RAG for University Documents

## Status

Accepted

## Decision

Use Retrieval-Augmented Generation instead of fine-tuning or training a language model from scratch for university document question answering.

## Reasoning

University regulations and manuals are changing source material. Retrieval makes current approved documents available without retraining a model and supports citations.

## Consequences

Document ingestion quality, chunking, metadata, retrieval relevance, and source traceability become first-class engineering concerns.
