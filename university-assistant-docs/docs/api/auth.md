# Auth API

Identity is the **email address** (ADR-014 / OA-02). Emails are normalized to
lowercase before storage and lookup, so `Student@Example.edu` and
`student@example.edu` are the same account. Error responses use the
standard envelope (`docs/04` §3); codes from `docs/12`. Throttled requests return
`429` with `RATE_LIMITED` (`auth_ip=10/min`, `auth_refresh=30/min` — OA-09).
Duplicate registrations return `409 CONFLICT`.

## POST `/api/v1/auth/register/`

Create a student account and sign in. Public route (`docs/20`).

### Input

```json
{
  "email": "student@example.edu",
  "password": "...",
  "first_name": "...",
  "last_name": "..."
}
```

`password` must satisfy Django's validators (length, common-password and numeric
checks). **The role is never accepted from the client** — the account is always
`STUDENT`; privileged accounts are created by an admin via `/admin/users/`.

### Output

Same shape as login (access token + user + refresh cookie), so the user is signed in
immediately after registering.

## POST `/api/v1/auth/login/`

Authenticate a user.

### Input

```json
{
  "email": "student@example.edu",
  "password": "..."
}
```

### Output

```json
{
  "access": "<short-lived-access-token>",
  "user": {
    "id": "...",
    "email": "student@example.edu",
    "role": "STUDENT"
  }
}
```

Sets two cookies: `refresh_token` (`HttpOnly`, `Secure` in production, `SameSite=Lax`,
path `/api/v1/auth/`) and `csrftoken` (readable by the SPA). The access token is kept
in frontend memory only (`docs/05` §3) and sent as `Authorization: Bearer`.

## POST `/api/v1/auth/refresh/`

Issue a new access token from the refresh cookie. **CSRF protected** (OA-23): must
send the `X-CSRFToken` header matching the `csrftoken` cookie, otherwise
`403 PERMISSION_DENIED`.

The refresh token **rotates** on every use: the response carries a new cookie. If a
revoked refresh token is presented (replay), the whole token family is revoked and
the request returns `401 AUTHENTICATION_REQUIRED` (ADR-014).

### Output

```json
{
  "access": "<new-access-token>",
  "user": { "id": "...", "email": "...", "role": "STUDENT" }
}
```

## POST `/api/v1/auth/logout/`

Revoke the refresh family identified by the cookie, clear the cookie, return `204`.
CSRF protected like refresh; idempotent (no cookie → still `204`).

## GET `/api/v1/auth/me/`

Return the authenticated user. Requires `Authorization: Bearer`.

### Output

```json
{
  "id": "...",
  "email": "student@example.edu",
  "first_name": "...",
  "last_name": "...",
  "role": "STUDENT",
  "is_active": true
}
```

Used by the SPA on boot (after refresh) to restore auth state.
