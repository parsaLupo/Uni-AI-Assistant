/**
 * HTTP client for the University Smart Assistant API.
 *
 * React talks to Django only through REST (AGENTS.md section 3) and never sees
 * an AI provider key (AGENTS.md section 9), so every call goes through here.
 * Non-2xx responses are normalised into ApiError using the documented envelope
 * (docs/04-api-specification.md section 3) so screens can translate the code
 * into a Persian message (docs/12-error-handling-observability.md section 2)
 * without parsing raw HTTP details.
 */

import type { ApiErrorBody } from '../types/api'
import { fallbackErrorMessage } from '../i18n/fa'

const DEFAULT_BASE_URL = '/api/v1'

export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined
  return (configured && configured.trim()) || DEFAULT_BASE_URL
}

export function buildApiUrl(path: string, query?: Record<string, string | number | undefined>): string {
  const base = apiBaseUrl().replace(/\/+$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${base}${normalizedPath.replace(/\/+$/, '')}/`

  if (!query) {
    return url
  }

  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const queryString = search.toString()
  return queryString ? `${url}?${queryString}` : url
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>
  readonly requestId: string | null

  constructor(
    code: string,
    message: string,
    status: number,
    details: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
    this.requestId = requestId
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const error = (value as { error?: unknown }).error
  return typeof error === 'object' && error !== null && 'code' in error && 'message' in error
}

/** Convert any failed response into ApiError, even when the body is not JSON. */
export async function toApiError(response: Response): Promise<ApiError> {
  const requestId = response.headers.get('X-Request-ID')
  let payload: unknown = null

  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (isApiErrorBody(payload)) {
    return new ApiError(
      payload.error.code,
      payload.error.message,
      response.status,
      (payload.error.details ?? {}) as Record<string, unknown>,
      requestId,
    )
  }

  // A response that ignores the contract is surfaced as INTERNAL_ERROR so the
  // UI can still show a stable message (docs/12 section 2). The text is Persian
  // because users must never see an English error (docs/11 localization).
  return new ApiError('INTERNAL_ERROR', fallbackErrorMessage, response.status, {}, requestId)
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    credentials: 'include',
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw await toApiError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
