# 01 — Requirements

## Functional requirements

### Authentication

- FR-AUTH-001: User can register according to project policy.
- FR-AUTH-002: User can log in securely.
- FR-AUTH-003: User can refresh authentication state.
- FR-AUTH-004: User can log out.
- FR-AUTH-005: Server enforces role-based permissions.

### Student profile

- FR-STU-001: Student profile contains academic identity and program information.
- FR-STU-002: Student can view/update permitted profile fields.
- FR-STU-003: Student academic history can represent passed/failed/current courses.

### Academic data

- FR-ACAD-001: Admin can manage faculties and departments.
- FR-ACAD-002: Admin can manage courses.
- FR-ACAD-003: Course can have prerequisites.
- FR-ACAD-004: Admin can manage professors.
- FR-ACAD-005: Admin can create course offerings per academic term.
- FR-ACAD-006: Course offerings can have schedules and classrooms.
- FR-ACAD-007: Exams can be stored per course offering.

### Calendar and announcements

- FR-CAL-001: Admin can create/edit academic events.
- FR-CAL-002: Students can view events relevant to their term.
- FR-ANN-001: Admin can publish announcements.
- FR-ANN-002: Students can view active announcements.

### Documents / RAG

- FR-DOC-001: Admin can upload approved PDF documents.
- FR-DOC-002: System stores document metadata.
- FR-DOC-003: Document can be versioned/deactivated.
- FR-DOC-004: System extracts text from approved documents.
- FR-DOC-005: System chunks text and stores metadata.
- FR-DOC-006: System creates embeddings.
- FR-DOC-007: System stores embeddings in pgvector.
- FR-DOC-008: Retrieval returns source metadata.

### AI assistant

- FR-AI-001: Student can create a conversation.
- FR-AI-002: Student can send a natural-language question.
- FR-AI-003: System can route question to structured query, RAG, hybrid, general, or out-of-scope path.
- FR-AI-004: System can generate a grounded response using relevant official context.
- FR-AI-005: Response can contain citations/source references.
- FR-AI-006: System can return uncertainty when evidence is insufficient.
- FR-AI-007: Conversation history is persisted for the owner.

### Admin / analytics

- FR-ADM-001: Admin can manage core data.
- FR-ADM-002: Admin can inspect document processing state.
- FR-ADM-003: Admin can view usage statistics.
- FR-ADM-004: Security-sensitive actions are auditable.

## Future functional requirements

- FR-SEL-001: Course selection eligibility engine.
- FR-SEL-002: Conflict detection.
- FR-SEL-003: Credit-limit validation.
- FR-SEL-004: Personalized recommendations.
- FR-NOT-001: Smart deadline notifications.

## Acceptance principles

A requirement is accepted only when it has:

- implementation
- test coverage appropriate to risk
- documented API/UI behavior
- clear permission behavior
- an observable acceptance criterion
