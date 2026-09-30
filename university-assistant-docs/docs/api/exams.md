# Exams API

## GET `/api/v1/exams/`

Return exam schedule for authorized/publicly visible term data.

Suggested filters:

```text
?term=<id>
?course=<id>
?student=me
```

Student-specific exam queries must verify that the course offering belongs to the student's academic context if that rule is adopted.
