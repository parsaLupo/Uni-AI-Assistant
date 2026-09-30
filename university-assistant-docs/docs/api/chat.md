# Chat API

## POST `/api/v1/conversations/`

Create a new conversation.

## GET `/api/v1/conversations/`

List the authenticated user's conversations.

## GET `/api/v1/conversations/{id}/`

Return conversation history.

## POST `/api/v1/conversations/{id}/messages/`

Submit a question.

### Input

```json
{
  "content": "شرایط مشروط شدن چیست؟"
}
```

### Output concept

```json
{
  "message": {
    "id": "...",
    "role": "ASSISTANT",
    "content": "...",
    "retrieval_mode": "RAG"
  },
  "sources": [
    {
      "document_id": "...",
      "label": "آیین‌نامه آموزشی",
      "page": 12,
      "section": "...",
      "relevance_score": 0.91
    }
  ]
}
```

The exact response fields may evolve, but source traceability should remain part of the contract for grounded answers.

## DELETE `/api/v1/conversations/{id}/`

Delete/archive a conversation according to retention policy. Ownership must be verified server-side.
