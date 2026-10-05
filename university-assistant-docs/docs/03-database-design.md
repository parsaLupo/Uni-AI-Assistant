# 03 — Database Design

## 1. Principles

- Normalize core academic data.
- Preserve historical academic records.
- Make time-dependent data explicitly term-aware.
- Use foreign keys for relationships.
- Use status fields for lifecycle state.
- Store source/version metadata for documents.

## 2. ERD

```mermaid
erDiagram
    USER ||--o| STUDENT_PROFILE : has
    USER ||--o{ CONVERSATION : owns
    CONVERSATION ||--o{ MESSAGE : contains
    MESSAGE ||--o{ MESSAGE_SOURCE : cites
    DOCUMENT_CHUNK ||--o{ MESSAGE_SOURCE : supports

    FACULTY ||--o{ DEPARTMENT : contains
    DEPARTMENT ||--o{ COURSE : owns
    DEPARTMENT ||--o{ PROFESSOR : employs
    COURSE ||--o{ COURSE_PREREQUISITE : requires
    COURSE ||--o{ COURSE_OFFERING : offered_as
    ACADEMIC_TERM ||--o{ COURSE_OFFERING : contains
    PROFESSOR ||--o{ COURSE_OFFERING : teaches
    COURSE_OFFERING ||--o{ CLASS_SCHEDULE : has
    COURSE_OFFERING ||--o| EXAM : has

    STUDENT_PROFILE ||--o{ ENROLLMENT : has
    COURSE_OFFERING ||--o{ ENROLLMENT : includes

    ACADEMIC_TERM ||--o{ ACADEMIC_EVENT : contains
    ACADEMIC_TERM ||--o{ ANNOUNCEMENT : scopes

    DOCUMENT ||--o{ DOCUMENT_CHUNK : contains

    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ AUDIT_LOG : triggers
```

## 3. Core entities

### User

Authentication identity. Typical fields:

- id
- email/username according to policy
- password hash
- is_active
- is_staff
- role
- created_at
- updated_at

### StudentProfile

Academic attributes linked to a User:

- user
- student_number
- faculty
- department
- degree_level
- entry_year
- current_term_number
- current_gpa

### Faculty

- name
- code
- is_active

### Department

- faculty
- name
- code
- is_active

### Course

- department
- code
- title
- credits
- course_type
- active

### CoursePrerequisite

- course
- prerequisite_course
- rule_type

`rule_type` can initially support `REQUIRED` and be extended later.

### AcademicTerm

- name
- academic_year
- semester_type
- starts_at
- ends_at
- is_current

### Professor

- department
- first_name
- last_name
- academic_title
- email
- office
- bio
- is_active

### CourseOffering

- course
- term
- professor
- section_code
- capacity
- status

### ClassSchedule

- course_offering
- weekday
- start_time
- end_time
- classroom

### Exam

- course_offering
- starts_at
- ends_at
- classroom
- status
- last_updated_at

### Enrollment

Represents a student's relationship with a course offering.

- student
- course_offering
- status
- grade
- enrolled_at

Suggested status values:

- `ENROLLED`
- `PASSED`
- `FAILED`
- `DROPPED`
- `WITHDRAWN`

### AcademicEvent

- term
- title
- event_type
- starts_at
- ends_at
- description
- is_published

### Announcement

- term (nullable — `NULL` means university-wide)
- audience (nullable: faculty/department/program — `NULL` means everyone)
- title
- body
- priority
- published_at
- expires_at
- is_published

### Document

- title
- document_type
- file_path / storage reference
- academic_year
- effective_from
- effective_to
- version
- status
- checksum
- uploaded_by
- created_at

### DocumentChunk

- document
- chunk_index
- content
- page_number
- section_title
- token_count
- embedding

The embedding column uses pgvector.

### Conversation

- user
- title
- created_at
- updated_at
- archived_at

### Message

- conversation
- role (`USER`, `ASSISTANT`, optionally `SYSTEM` internally)
- content
- retrieval_mode
- created_at
- latency_ms

### MessageSource

- message
- document_chunk
- source_label
- relevance_score
- citation_text

### Notification

- user
- title
- body
- type
- is_read
- created_at

### AuditLog

- actor
- action
- entity_type
- entity_id
- metadata
- created_at

## 4. Important indexes

Recommended early indexes:

- Course.code
- Professor last name / department
- CourseOffering.term + course
- CourseOffering.term + professor
- Exam.course_offering
- AcademicEvent.term + starts_at
- Document.status + academic_year
- DocumentChunk.document + chunk_index
- Conversation.user + updated_at
- Notification.user + is_read

Exact index strategy must be validated against actual queries before over-indexing.

## 5. Historical correctness

Never overwrite old exam/schedule facts merely because the current term changed. Each offering/exam is attached to a specific academic term. Documents similarly require effective/version metadata.

## 6. Constraints (enforced by the database)

`docs/07` §1 requires database constraints; uniqueness must not depend on every
future endpoint remembering to check. Each constraint exists because a specific
rule or query needs it (added in Phase 01, implemented in Phase 04 migrations).

| Invariant | Constraint | Why |
|---|---|---|
| At most one current term | partial unique index on `AcademicTerm(is_current) WHERE is_current` | "current term" is used as the default everywhere; two rows would make it ambiguous |
| One section per course per term | unique `(course, term, section_code)` | offering identity for enrollment and schedules |
| One enrollment per student per offering | unique `(student, course_offering)` | prevents double enrollment and grade rows |
| One exam per offering | `CourseOffering.exam` one-to-one | an exam belongs to a concrete offering, not a course (`docs/17`) |
| Stable codes | unique `Course.code`, unique `(faculty, code)`, unique `(department, code)` | codes are referenced by students and external systems |
| Valid time ranges | `CHECK (starts_at < ends_at)` on terms, events, exams, schedules | invalid ranges corrupt calendar and conflict checks |
| No self-prerequisite | `CHECK (course_id <> prerequisite_course_id)` | a course cannot require itself |

Indexes are listed separately in §4 and must each be justified by a query; over-indexing is a maintenance cost, so re-check them with `EXPLAIN` once real data exists.
