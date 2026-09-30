# ADR-002 — PostgreSQL + pgvector

## Status

Accepted

## Decision

Use PostgreSQL as the single primary data store and enable pgvector for embedding storage/retrieval.

## Reasoning

Structured academic data and vectorized document chunks can remain in one operational database, reducing infrastructure complexity for MVP.

## Consequences

Vector search scale and indexing strategy must be measured as the corpus grows. A separate vector database remains a future migration option if requirements justify it.
