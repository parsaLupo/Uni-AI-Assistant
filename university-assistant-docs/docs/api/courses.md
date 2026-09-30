# Courses API

## GET `/api/v1/courses/`

List courses.

Suggested filters:

```text
?department=<id>
?search=database
?credits=3
?course_type=...
```

## GET `/api/v1/courses/{id}/`

Return course detail, including prerequisites and basic department information.

## GET `/api/v1/course-offerings/`

List course offerings for an academic term.

Suggested filters:

```text
?term=<id>
?course=<id>
?professor=<id>
```

Selection eligibility is not implied by this endpoint; see course selection phase documentation.
