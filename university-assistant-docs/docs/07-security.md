# 07 — Security Requirements

## 1. Application security

- Use Django security defaults and production settings.
- Disable debug in production.
- Enforce HTTPS in production.
- Set secure cookie flags.
- Restrict allowed hosts/CORS to known environments.
- Validate all incoming data with DRF serializers/forms.

## 2. Authentication security

- Use strong password hashing.
- Do not log tokens/passwords.
- Rate-limit login/refresh endpoints where appropriate.
- Expire access tokens.
- Protect admin routes with backend permissions.

## 3. File upload security

- Allow only expected document types.
- Validate MIME type and extension independently.
- Limit file size.
- Store uploads outside executable paths.
- Sanitize filenames.
- Scan files if an appropriate deployment security tool is available.
- Process PDFs in a sandboxed/controlled environment where possible.

## 4. AI security

- Do not expose provider API keys to React.
- Treat user prompts as untrusted.
- Treat retrieved document text as untrusted.
- Prevent prompt data from overriding system rules.
- Avoid sending unnecessary personal/academic data to external AI providers.
- Add rate limits and usage controls around AI endpoints.

## 5. Authorization

Server-side checks must cover:

- own conversation access
- own profile access
- admin content changes
- document management
- analytics

## 6. Privacy

Store only data needed for the defined functionality. Define retention policy for chat messages, audit logs, and uploaded documents before production use.

## 7. Auditability

Audit high-impact admin actions, such as:

- document upload/delete/activation
- regulation version changes
- exam schedule changes
- role/permission changes

## 8. Security acceptance checklist

Evidence per line was collected in Phase 15 (see `docs/phases/phase-15.md`).

- [x] no secret committed *(CI `secret-scan` job greps tracked files for `gsk_*`, `sk-*`, `AKIA*`, `BEGIN … PRIVATE KEY`; local run clean — no match. `.env` is gitignored and the dev fallback key is refused outside DEBUG/tests.)*
- [x] production debug disabled *(DEBUG defaults to false and refuses to boot without an explicit `DJANGO_SECRET_KEY` (`config/settings.py`); verified by the subprocess boot tests in `apps/common/tests/test_production_settings.py`, which also assert the transport hardening defaults — HTTPS redirect, HSTS 1y, nosniff, same-origin referrer, `X-Frame-Options: DENY`, secure cookies, empty CORS.)*
- [x] admin permissions tested *(server-side `IsAdmin` enforced by the permission matrix, 112 rows: `apps/common/tests/test_permission_matrix.py`, plus openapi exhaustiveness checks; admin visibility alone is never a control.)*
- [x] upload restrictions tested *(extension/MIME/size/magic-byte/encryption checks in `apps/documents/serializers.py::validate_file` with tests in `apps/documents/tests/test_api.py`; uploads stored under `DOCUMENT_STORAGE_ROOT` by checksum-derived key with sanitised filename; AV-scan hook point documented at the same validator, off in the MVP.)*
- [x] AI endpoint rate limit considered *(implemented, not just considered: per-user `ai_ask` budget on `/ai/ask` + `/ai/ask/stream` (`RATE_AI_ASK`, default 20/min) and per-admin `upload` budget (`RATE_UPLOAD`, default 10/min), auth limits from ADR-014; 429s return the documented `RATE_LIMITED` envelope — tests in `apps/ai/tests/test_throttling.py`, `apps/documents/tests/test_throttling.py`, `apps/accounts/tests/test_throttling.py`.)*
- [x] prompt injection test cases exist *(Phase 09 primitives plus the Phase 15 regulation-style pipeline suite: poisoned document chunks stay inside the UNTRUSTED block, planted citations are stripped, injection-only questions are refused via routing — `apps/ai/tests/test_injection_hardening.py`, `apps/ai/tests/test_phase09.py`.)*
- [x] logs do not contain secrets *(access log records request id/method/path/status/latency only; no password, refresh token, question text or query string — proven by `apps/common/tests/test_logging_hygiene.py`; internal failures are logged with the correlation id but never serialized to the client.)*

### Dependency security (Phase 15)

- `pip-audit` runs against the environment and the committed pins; the
  Phase 15 findings (DRF 3.18.1 → 3.18.2, pypdf 5.3.1/6.21.2 → 6.21.4, pip
  25.1.1 → 26.3) were all applied and the audit is now clean
  ("No known vulnerabilities found").
- `npm audit` clean after `vite` 8.3.1 → 8.3.8 (high-severity GHSA set fixed).
- Update path: dependencies are pinned in `backend/requirements.txt` and
  `frontend/package.json` (exact versions). Upgrade flow = bump the pin, run
  the backend suite + `pip-audit -r requirements.txt` (or `npm audit`), record
  the reason in the pin comment. CI adds a secret-scan job; a scheduled
  `pip-audit`/`npm audit` job should be added alongside it in Phase 16.
