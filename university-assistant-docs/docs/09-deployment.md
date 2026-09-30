# 09 — Deployment

## 1. Target architecture

```text
Internet
   |
   v
Reverse Proxy / HTTPS
   |
   +--------------------+
   |                    |
   v                    v
React static app      Django API
                          |
                          v
                 PostgreSQL + pgvector
                          |
                          v
                     AI Provider
```

## 2. Containers

MVP container set may be:

- `frontend`
- `backend`
- `db`
- `nginx` or equivalent reverse proxy

A background worker can be added later if document ingestion becomes asynchronous.

## 3. Environment configuration

Never commit secrets. Use environment variables or deployment secret management.

Example categories:

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DATABASE_URL
ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
JWT settings
AI_PROVIDER_API_KEY
AI_MODEL
EMBEDDING_MODEL
```

Exact names are implementation-defined and must match `.env.example`.

## 4. Database operations

Production deployment process should include:

1. backup
2. migration
3. application restart/rollout
4. health checks
5. smoke test

## 5. Backups

Back up PostgreSQL data on a defined schedule. Verify that a backup can actually be restored in a non-production environment.

## 6. Static/media assets

- frontend static assets served by reverse proxy/CDN where appropriate
- uploaded documents stored in controlled storage
- avoid exposing raw internal filesystem paths

## 7. Health checks

Backend should expose a lightweight health endpoint, for example:

```text
GET /api/v1/health/
```

It should report application availability and, where appropriate, database connectivity without leaking sensitive details.

## 8. Production readiness checklist

- [ ] HTTPS
- [ ] DEBUG off
- [ ] secret management
- [ ] database backup
- [ ] migrations applied
- [ ] health check
- [ ] logging
- [ ] rate limits
- [ ] CORS/host restrictions
- [ ] document storage configured
