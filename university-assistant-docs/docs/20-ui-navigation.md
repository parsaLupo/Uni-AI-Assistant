# 20 — UI and Navigation Specification

## Public routes

```text
/login
/register
```

## Student routes

```text
/dashboard
/assistant
/conversations/:id
/courses
/courses/:id
/professors
/professors/:id
/calendar
/exams
/announcements
/profile
```

## Admin routes

```text
/admin
/admin/users
/admin/courses
/admin/professors
/admin/terms
/admin/exams
/admin/documents
/admin/announcements
/admin/analytics
```

## Layout

The student application should have a persistent navigation shell, clear page titles, and responsive behavior. The assistant should visually prioritize the conversation, sources, loading state, and errors.

## RTL

The primary UI language is Persian and the main application layout must support RTL from the beginning rather than as a late styling patch.

## AI response presentation

An answer may contain:

- main response
- source/citation cards
- structured result tables
- warnings/uncertainty
- related questions

The frontend must not fabricate citation content; all source labels come from the API response.
