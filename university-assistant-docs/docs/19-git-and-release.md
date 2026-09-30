# 19 — Git and Release Conventions

## Commit style

Use clear commits such as:

```text
feat(auth): add JWT login endpoint
feat(courses): add prerequisite model
feat(rag): add document chunk retrieval
fix(chat): prevent access to another user's conversation
chore(docker): add postgres development service
```

## Commit rule

A commit should represent one coherent change. Avoid combining unrelated features.

## Release checkpoint

Before tagging a milestone:

- tests pass
- migrations verified
- docs updated
- environment variables documented
- known limitations recorded

## Phase checkpoint

Each completed phase should have a stable commit/checkpoint so the project can be inspected or reverted from a known state.
