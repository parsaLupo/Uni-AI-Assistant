# 08 — Testing Strategy

## 1. Backend

Recommended layers:

- unit tests for domain/business rules
- API tests for DRF endpoints
- integration tests for database-dependent flows
- permission tests
- RAG service tests

## 2. Frontend

Recommended layers:

- component tests
- hook/service tests
- page-level tests for important flows
- end-to-end tests for critical user journeys

## 3. Critical end-to-end journeys

1. Register/login -> dashboard.
2. Browse course -> course detail.
3. Browse professor -> professor detail.
4. View exam schedule.
5. Ask RAG question -> receive answer + source.
6. Create conversation -> ask follow-up -> reload history.
7. Admin uploads document -> document processed -> question retrieves it.

## 4. RAG test dataset

Create a deterministic dataset in `docs/` or test fixtures with a limited number of official-looking sample documents.

Each case should define:

- query
- expected retrieval source(s)
- expected answer facts
- disallowed unsupported claims

## 5. Example test

```text
Question:
شرایط مشروط شدن چیست؟

Expected retrieval:
آیین‌نامه آموزشی / section about probation

Expected answer must mention:
Only facts present in the approved source.

Must not:
Invent a GPA threshold not present in the context.
```

## 6. Test gates

A phase cannot be marked complete when its critical tests fail.

Minimum gates:

- backend tests pass
- frontend tests pass for changed behavior
- migrations succeed
- API contract remains valid
- security-sensitive paths have explicit tests

## 7. Definition of test quality

Do not optimize for raw coverage percentage. Prioritize correctness of business rules, permissions, data integrity, and AI grounding.
