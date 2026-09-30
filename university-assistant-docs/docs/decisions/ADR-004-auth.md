# ADR-004 — JWT Authentication for React SPA

## Status

Accepted

## Decision

Use JWT-based authentication with short-lived access tokens and refresh tokens, with refresh-token storage designed to avoid persistent token exposure in browser localStorage.

## Reasoning

The system is a separate React SPA and Django API. JWT provides a clear API authentication model while remaining independent of browser session rendering.

## Consequences

Token lifecycle, logout semantics, cookie security, CSRF considerations, and refresh handling must be tested explicitly.
