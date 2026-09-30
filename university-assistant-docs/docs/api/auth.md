# Auth API

## POST `/api/v1/auth/login/`

Authenticate a user.

### Input

```json
{
  "username": "student@example.com",
  "password": "..."
}
```

### Output concept

```json
{
  "access": "<short-lived-access-token>",
  "user": {
    "id": "...",
    "role": "STUDENT"
  }
}
```

Refresh token handling follows `docs/05-authentication.md`.

## POST `/api/v1/auth/refresh/`

Issue a new access token using the refresh mechanism.

## POST `/api/v1/auth/logout/`

Clear/invalidate refresh authentication state according to the chosen implementation.
