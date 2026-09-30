# ADR-001 — Technology Stack

## Status

Accepted

## Decision

Use React + TypeScript for frontend, Django + Django REST Framework for backend, PostgreSQL for primary data, pgvector for vector retrieval, and Docker for environment consistency.

## Reasoning

- strong separation between frontend and backend
- mature Python ecosystem for AI/RAG work
- PostgreSQL supports both relational data and vectors through pgvector
- REST API is explicit and easy to test
- Docker improves reproducibility

## Consequences

The project has more moving parts than a monolithic Django template app, but gains a clear architecture suitable for a portfolio/undergraduate software project with AI capabilities.
