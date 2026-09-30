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
- [ ] Student can authenticate.
- [ ] Unauthorized users cannot access protected resources.
- [ ] Admin endpoints reject non-admin users.
- [ ] Frontend never stores provider secrets.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.
