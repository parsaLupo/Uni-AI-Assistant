# 17 — Domain Rules

## Academic time awareness

Course offerings, schedules, exams, and regulations can depend on an academic term/effective period. Queries must not mix current and historical records without an explicit reason.

## Prerequisite

A course is eligible only when all required prerequisite rules are satisfied according to the configured academic policy.

## Passed course

A passed course normally should not be recommended for repetition unless a specific university policy permits it and the model supports that rule explicitly.

## Course offering

A course existing in the catalog does not imply that it is offered in the current term.

## Exam

An exam belongs to a concrete course offering, not just to a generic course.

## Regulation

When answering a regulation question, the system should prefer a currently effective approved document and preserve the source/version information.

## Source requirement

For university-specific claims generated through RAG, the response should expose source metadata whenever the UI/API supports it.

## Insufficient evidence

If the system cannot establish an answer from trusted structured data or approved documents, it should not invent a university-specific fact.

## AI role

The LLM explains and synthesizes evidence. Deterministic backend rules decide business-critical eligibility/results.
