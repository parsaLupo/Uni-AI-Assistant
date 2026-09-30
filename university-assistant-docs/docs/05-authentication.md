# 05 — Authentication and Authorization

## 1. Goal

Provide secure authentication for React SPA users while keeping credentials and AI secrets away from the browser.

## 2. Roles

Initial roles:

- `STUDENT`
- `PROFESSOR`
- `ADMIN`
- `SUPERADMIN`

Authorization must be enforced in Django/DRF.

## 3. Token strategy

Recommended architecture:

- short-lived access JWT
- refresh JWT stored in an HttpOnly, Secure cookie
- access token kept in frontend memory rather than localStorage
- refresh mechanism performed through backend endpoint

Exact cookie settings depend on deployment topology, but production must use HTTPS.

## 4. Authentication flow

```text
React
  -> POST /auth/login/
  -> Django verifies credentials
  -> Django issues access token + refresh cookie
  -> React keeps access token in memory
  -> API requests use Authorization header
```

## 5. Refresh flow

```text
React
  -> POST /auth/refresh/
  -> browser sends refresh cookie
  -> backend validates refresh token
  -> new access token returned
```

## 6. Logout

Logout must invalidate/expire the refresh mechanism according to the chosen JWT strategy and clear the cookie.

## 7. Permissions

Examples:

- Student: read published academic data, manage own conversations/profile fields.
- Professor: limited read access plus future professor-specific permissions.
- Admin: manage university content and users where authorized.
- Superadmin: platform-level administration.

## 8. Forbidden behavior

- Secrets in React environment bundles.
- Password storage outside Django's password hashing system.
- Client-only authorization.
- Long-lived access tokens without reason.
