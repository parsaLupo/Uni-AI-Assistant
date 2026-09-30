# ADR-006 — AI Provider Adapter

## Status

Accepted

## Decision

Access the chosen LLM/embedding provider through backend service abstractions/adapters rather than calling the provider directly from views.

## Reasoning

This isolates provider-specific code, makes testing easier, and allows provider/model changes with less application churn.

## Consequences

A small abstraction layer must be maintained and tested; prompt/model configuration must be explicit and versioned.
