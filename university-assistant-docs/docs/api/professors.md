# Professors API

## GET `/api/v1/professors/`

Search/list professors.

Suggested filters:

```text
?search=ahmadi
?department=<id>
?term=<id>
```

## GET `/api/v1/professors/{id}/`

Return professor profile and approved offering information.
