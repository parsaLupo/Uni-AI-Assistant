# 04 — REST API Specification

## 1. Base URL

Development example:

```text
/api/v1/
```

Production base URL is environment-specific.

## 2. Authentication

Use JWT-based authentication. See `05-authentication.md`.

## 3. Response conventions

### Success

Resource endpoints return JSON objects/lists appropriate to the endpoint.

### Error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "details": {}
  }
}
```

`details` may contain field-level errors or machine-readable metadata.

## 4. Pagination

List endpoints should support pagination. The exact pagination shape must be kept consistent across the API.

Suggested query parameters:

```text
?page=1&page_size=20
```

## 5. Filtering / ordering

Only supported filters should be documented; arbitrary query execution is not allowed.

Typical parameters:

```text
?search=data
?department=...
?term=...
?ordering=...
```

## 6. Endpoint catalog

Admin CRUD for courses, professors, terms, offerings, exams, calendar events,
announcements, enrollments and users is catalogued in `docs/api/admin.md`
(Phase 01 contract; implemented in Phase 04).

| Area | Method | Endpoint | Purpose |
|---|---|---|---|
| Auth | POST | `/auth/login/` | Login |
| Auth | POST | `/auth/refresh/` | Refresh access token |
| Auth | POST | `/auth/logout/` | Logout |
| Profile | GET/PATCH | `/students/me/` | Student profile |
| Courses | GET | `/courses/` | Course list |
| Courses | GET | `/courses/{id}/` | Course detail |
| Professors | GET | `/professors/` | Professor list |
| Professors | GET | `/professors/{id}/` | Professor detail |
| Terms | GET | `/terms/` | Academic terms |
| Departments | GET | `/departments/` | Active departments (student onboarding options) |
| Calendar | GET | `/calendar/events/` | Academic events |
| Exams | GET | `/exams/` | Exam schedule |
| Announcements | GET | `/announcements/` | Published announcements |
| Chat | POST | `/conversations/` | Create conversation |
| Chat | GET | `/conversations/` | List conversations |
| Chat | GET | `/conversations/{id}/` | Conversation detail |
| Chat | POST | `/conversations/{id}/messages/` | Ask question |
| Chat | DELETE | `/conversations/{id}/` | Delete/archive conversation |
| Documents | POST | `/admin/documents/` | Upload document |
| Documents | GET | `/admin/documents/` | Admin document list |
| Analytics | GET | `/admin/analytics/summary/` | Admin summary |

## 7. API contract rules

- Do not return database models directly.
- Use serializers as the public contract.
- Keep public response field names stable.
- Avoid exposing internal provider responses.
- Document permission requirements for each admin endpoint.
- Document whether an endpoint is idempotent or creates a new resource.
