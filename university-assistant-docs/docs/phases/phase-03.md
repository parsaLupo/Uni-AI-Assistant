# Phase 03 — Authentication and Authorization

## Objective
Implement secure account management and server-side roles.

## Tasks
- User model/configuration.
- Registration policy.
- Login.
- JWT access/refresh flow.
- Logout.
- Role/permission model.
- Protected API endpoints.
- React auth state and protected routes.

## Tests
- valid login
- invalid login
- token refresh
- logout
- permission denial
- own-resource access

## Acceptance criteria
- [x] Student can authenticate. *(live: register 201 → refresh 200 → `/auth/me/` 200 → logout 204; UI `/login` → `/dashboard`)*
- [x] Unauthorized users cannot access protected resources. *(live `GET /admin/users/` anonymous → 401 `AUTHENTICATION_REQUIRED`; `me` without Bearer → 401)*
- [x] Admin endpoints reject non-admin users. *(403 `PERMISSION_DENIED` — `test_admin_users.py`, 17 tests incl. student/professor denial, promotion limits, self-deactivation 409)*
- [x] Frontend never stores provider secrets. *(access token in a module variable only — `session.ts`; no web storage exists in tests and none is touched; refresh token is HttpOnly, never readable by JS)*

## Verification record — 2026-10-05

| Gate | Command | Result |
|---|---|---|
| Backend tests (SQLite) | `python -m pytest` | 57 passed |
| Backend tests (PostgreSQL) | `TEST_DATABASE_URL=… python -m pytest` | 57 passed (`accounts.0001_initial` applied on the test DB) |
| Lint | `ruff check .` | All checks passed |
| System check | `manage.py check` (DEBUG=false) | 0 issues |
| Migration drift | `manage.py makemigrations --check` | No changes detected |
| Contract | `manage.py spectacular --file openapi.yaml --validate` | exit 0, 0 warnings/errors; committed `openapi.yaml` regenerated (auth paths included) |
| Typecheck | `npm run typecheck` | exit 0 |
| Frontend tests | `vitest run` | 23 passed (10 auth-logic tests) |
| Build | `npm run build` | OK — 269.4 kB / 85.6 kB gzip |
| **Live E2E (Docker, real Postgres)** | curl against `localhost:8000` | `register=201` (cookies set) → `refresh=200` with `X-CSRFToken` → `me=200` full profile → `logout=204` → `refresh after logout=401` (family revoked) → `refresh without CSRF=403` → `admin anonymous=401` → health `database: ok` (16 ms) |

Bugs found and fixed during verification: `CsrfViewMiddleware.process_view`
called with wrong kwargs (500 on refresh/logout), `Morsel.has_nonstandard_attr`
does not exist (Python 3.13), admin duplicate-email returned 400 instead of the
contract's 409, `RefreshView`/`LogoutView` broke `spectacular --validate`
(missing `request=None`), frontend silent-refresh reused a consumed `Response`
body and left a dead token in memory after a failed refresh.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.
