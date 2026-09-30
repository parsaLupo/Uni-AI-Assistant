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

- [ ] no secret committed
- [ ] production debug disabled
- [ ] admin permissions tested
- [ ] upload restrictions tested
- [ ] AI endpoint rate limit considered
- [ ] prompt injection test cases exist
- [ ] logs do not contain secrets
