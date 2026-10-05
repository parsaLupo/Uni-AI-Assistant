/**
 * API response types mirroring the backend contract.
 *
 * Error codes come from docs/12-error-handling-observability.md section 1 and
 * are implemented in backend/apps/common/errors.py. Keeping both lists aligned
 * is verified by tests on each side.
 */

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'AUTHENTICATION_REQUIRED'
  | 'PERMISSION_DENIED'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'RATE_LIMITED'
  | 'AI_PROVIDER_ERROR'
  | 'RETRIEVAL_ERROR'
  | 'DOCUMENT_PROCESSING_ERROR'
  | 'INTERNAL_ERROR'
  // Documented extensions, see ADR-008.
  | 'METHOD_NOT_ALLOWED'
  | 'REQUEST_FAILED'

/** The single error shape defined by docs/04-api-specification.md section 3. */
export interface ApiErrorBody {
  error: {
    code: ApiErrorCode | string
    message: string
    details: Record<string, unknown>
  }
}

/** Consistent list envelope from StandardResultsSetPagination. */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface HealthResponse {
  status: 'ok'
  service: string
  version: string
  request_id: string
  checks: {
    database: 'ok' | 'unavailable'
    database_latency_ms: number | null
    /** 'not_configured' until the AI provider adapter phase (ADR-006). */
    ai_provider: string
  }
}

/** Roles from ADR-014 / docs/17. The server is authoritative about role checks. */
export type UserRole = 'STUDENT' | 'PROFESSOR' | 'ADMIN' | 'SUPERADMIN'

/** GET /api/v1/auth/me/ output (docs/api/auth.md). */
export interface AuthUser {
  id: number
  email: string
  first_name: string
  last_name: string
  role: UserRole
  is_active: boolean
}

/**
 * POST /auth/login/, /auth/register/, /auth/refresh/ output. The refresh cookie
 * itself is HttpOnly and never crosses this boundary (docs/05 section 3): only
 * the short-lived access token lives in frontend memory.
 */
export interface AuthSession {
  access: string
  user: {
    id: number
    email: string
    role: UserRole
    first_name?: string
    last_name?: string
  }
}
