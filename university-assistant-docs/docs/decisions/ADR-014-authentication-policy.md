# ADR-014 — Authentication policy: email identity, rotation, CSRF, rate limits

## Status

Accepted (implemented in Phase 03)

## Decision

Closes OA-01, OA-02, OA-09 and OA-23.

1. **Identity is the email address.** Custom `accounts.User` with
   `USERNAME_FIELD = "email"`; the API field for login is `email`. There is no
   separate username.
2. **Registration is open for students only.** `POST /auth/register/` may be called
   by anyone and **always** creates role `STUDENT` — the client cannot select a role.
   `PROFESSOR`, `ADMIN` and `SUPERADMIN` accounts are created only through
   `POST /admin/users/` by an appropriately privileged admin. `/register` remains a
   public route (`docs/20`).
3. **Refresh tokens rotate with reuse detection.** Refresh lives in an `HttpOnly,
   Secure` cookie scoped to `/api/v1/auth/`. Every refresh is recorded in
   `RefreshTokenRecord` (`jti`, family, revoked_at). A presented refresh token that
   is already revoked means a copy leaked: the **entire family is revoked** and the
   request fails with `401`. Logout revokes the family and clears the cookie.
4. **CSRF is double-submit.** Login sets a readable `csrftoken` cookie; refresh and
   logout are wrapped in `csrf_protect` and must receive it back in the
   `X-CSRFToken` header, otherwise `403 PERMISSION_DENIED`. DRF's default CSRF
   handling does not cover non-session authentication, so this is explicit.
5. **Rate limits:** `auth_ip=10/min` for login and register per IP;
   `auth_refresh=30/min` per user, falling back to per-IP when the presented token
   cannot be verified. Values come from DRF `DEFAULT_THROTTLE_RATES` via env
   (`docs/09` §3 names).
6. **Passwords use Argon2id** (`argon2-cffi`) as the first hasher, Django's built-in
   validators still apply — `docs/07` §2 asks for strong hashing and Argon2id is the
   current OWASP recommendation.
7. **Access tokens** are short-lived (default 5 min, `JWT_ACCESS_MINUTES`), issued by
   `djangorestframework-simplejwt` (pinned), kept in **frontend memory** only, and
   sent as `Authorization: Bearer`.

## Reasoning

`docs/05` fixes the strategy (short access JWT, HttpOnly refresh cookie, memory-only
access token, server-side authorization) but leaves the four open questions above
unanswered; they materially affect the user model and security, so `AGENTS.md`
forbids implementing around them. Email-as-identity matches how universities address
students and removes a second identifier to forget or abuse. Rotation with family
revocation is the standard mitigation for token theft (ADR-004 required the
consequence to be tested rather than assumed). Double-submit CSRF works without
sessions and survives the SPA/cookie topology; a custom-header-only variant offers no
protection when the request itself carries the cookie.

## Consequences

New dependencies: `djangorestframework-simplejwt`, `argon2-cffi`, documented here per
`AGENTS.md` rule 10. `AUTH_USER_MODEL` is set before any feature model exists, which
is why Phase 03 precedes Phase 04 (a later user-model change would be a costly
migration). The read paths (`/auth/login/`, `/auth/refresh/`, `/auth/me/`,
`/auth/register/`, `/auth/logout/`) are documented in `docs/api/auth.md` and appear in
`openapi.yaml`. Rate limits are enforced from `LocMemCache`, which is per-process —
multi-worker deployments must switch to a shared cache (Redis arrives with ADR-011).
Frontend stores the access token in memory only (`AGENTS.md` §9 forbids browser
secrets; `docs/05` §8 forbids localStorage for tokens); refresh state is re-established
on boot by calling `/auth/refresh/`.
