# Documents API

All document management endpoints are admin-only unless a later role explicitly permits access.

## POST `/api/v1/admin/documents/`

Upload an approved PDF and metadata.

Required conceptual metadata:

- title
- document_type
- academic_year/effective period
- version

## GET `/api/v1/admin/documents/`

List documents and processing status.

## GET `/api/v1/admin/documents/{id}/`

View metadata and processing status.

## PATCH `/api/v1/admin/documents/{id}/`

Update metadata/status where permitted.

## DELETE `/api/v1/admin/documents/{id}/`

Remove/deactivate according to document retention policy.
