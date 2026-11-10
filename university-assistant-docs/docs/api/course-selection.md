# Course Selection API (Phase 11)

The endpoint is the deterministic rules engine's surface: the verdict and every
rejection reason come from PostgreSQL records only. The LLM never decides
eligibility (`AGENTS.md` section 8, `docs/18` "Course selection rule"); the
response embeds a Persian explanation already composed from the engine result.

## POST `/api/v1/students/me/course-selection/`

Evaluate one course for the authenticated student's *current-term* plan.

- Auth: Bearer token; student role required (professors/admins get
  `403 PERMISSION_DENIED`).
- Read-only: nothing is created or written.

### Input

```json
{
  "course_code": "1916003",
  "extra_course_codes": ["1916001", "1916002"]
}
```

- `course_code` (required) — course code; Persian/Arabic digits and Arabic
  yeh/kaf variants are normalized on the backend.
- `extra_course_codes` (optional) — what-if list: credits of these courses are
  added to the term total (`what-if credit totals`). Every code must exist;
  an unknown code is a `400 VALIDATION_ERROR`, not a silently ignored extra.

### Output

```json
{
  "course": { "code": "1916003", "title": "…", "credits": 3 },
  "eligible": false,
  "reasons": [
    {
      "code": "PREREQUISITE_MISSING",
      "message": "ابتدا باید این پیش‌نیازها را با موفقیت بگذرانید: 1916002",
      "params": { "codes": ["1916002"], "count": 1 }
    }
  ],
  "term_name": "نیمسال اول ۱۴۰۵-۱۴۰۶",
  "passed_course_codes": ["1916001"],
  "missing_prerequisite_codes": ["1916002"],
  "planned_course_codes": ["1916009"],
  "extra_course_codes": [],
  "credit_totals": {
    "limit": 20,
    "planned": 16,
    "candidate": 3,
    "extra": 0,
    "total_with_candidate": 19,
    "over_limit": false
  },
  "engine_version": "phase11-rules-v1",
  "explanation": {
    "text": "…قاعده‌محور…",
    "source": "composed",
    "engine_eligible": false
  }
}
```

### Stable reason codes

| Code | Meaning |
|---|---|
| `UNKNOWN_COURSE` | Code not found in the catalog (also returned by the engine; the HTTP view answers `404` before calling it) |
| `ALREADY_PASSED` | The course is already in the student's history as `PASSED` (docs/17: no silent repetition) |
| `ALREADY_PLANNED` | Already `PLANNED`/`ENROLLED` in the current term |
| `PREREQUISITE_MISSING` | Required prerequisite edges without a `PASSED` record |
| `NOT_OFFERED_CURRENT_TERM` | No offering of the course in `AcademicTerm.is_current` |
| `OFFERING_CLOSED` | Offerings exist but none has status `OPEN` |
| `CREDIT_LIMIT_EXCEEDED` | `planned + candidate + extras` exceeds the limit (OA-24 default 20; `exactly 20` passes) |
| `SCHEDULE_CONFLICT` | Every *open* section overlaps the plan's schedule rows; a conflict-free section is chosen automatically |

`reasons[].code` is machine-readable and stable; `message` is Persian and
display-ready; `params` carries raw values for programmatic use.

### Errors

| Situation | Response |
|---|---|
| Missing/empty `course_code` | `400 VALIDATION_ERROR` |
| `extra_course_codes` not a string list, or unknown extra code | `400 VALIDATION_ERROR` |
| Unknown course code | `404 NOT_FOUND` |
| Non-student caller | `403 PERMISSION_DENIED` |
| Unauthenticated | `401 AUTHENTICATION_REQUIRED` |

### Credit limit configuration

The limit is a Django setting, `COURSE_SELECTION_MAX_TERM_CREDITS`
(OA-24 baseline 20) — registrar still to confirm the official value.
