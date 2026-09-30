# 12 — Error Handling and Observability

## 1. Error taxonomy

Suggested machine-readable error codes:

```text
VALIDATION_ERROR
AUTHENTICATION_REQUIRED
PERMISSION_DENIED
NOT_FOUND
CONFLICT
RATE_LIMITED
AI_PROVIDER_ERROR
RETRIEVAL_ERROR
DOCUMENT_PROCESSING_ERROR
INTERNAL_ERROR
```

## 2. User-facing behavior

The frontend should translate technical failures into useful Persian messages without exposing internals.

Examples:

```text
AI_PROVIDER_ERROR
=> «سرویس هوش مصنوعی در حال حاضر در دسترس نیست. دوباره تلاش کنید.»
```

```text
RETRIEVAL_ERROR
=> «در بازیابی اطلاعات رسمی خطایی رخ داد.»
```

## 3. Logging

Structured logs should capture:

- timestamp
- log level
- request id/correlation id
- endpoint
- status code
- latency
- error code

For AI flows also consider:

- retrieval mode
- retrieval count
- provider latency
- model identifier

Do not log full sensitive user data by default.

## 4. Correlation IDs

Each request should have a correlation/request ID so errors can be traced across API and AI service logs.

## 5. Health checks

Use a lightweight health endpoint and distinguish between:

- process healthy
- database reachable
- AI provider available

Avoid making the entire application appear unavailable only because an optional AI provider is temporarily unavailable.
