/**
 * Auth API calls (docs/api/auth.md).
 *
 * Two contract details drive the design:
 * - `/auth/refresh/` and `/auth/logout/` are cookie-authenticated and CSRF
 *   protected (OA-23 / ADR-014 decision 4), so they echo the readable
 *   `csrftoken` cookie in the `X-CSRFToken` header (double submit).
 * - `/auth/me/` and every future authenticated call carry the in-memory access
 *   token as `Authorization: Bearer`. On a 401 the client refreshes silently
 *   once and retries exactly once — never a refresh loop (docs/05 section 3).
 */

import { ApiError, requestJson } from '../../api/client'
import type { AuthSession, AuthUser } from '../../types/api'
import { getAccessToken, setAccessToken } from './session'

/** Read the SPA-readable csrftoken cookie Django sets at login/register. */
export function readCsrfCookie(): string | null {
  if (typeof document === 'undefined') {
    return null
  }
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

async function postSession(
  path: 'login' | 'register' | 'refresh',
  body?: Record<string, unknown>,
): Promise<AuthSession> {
  const headers: Record<string, string> = {}
  if (path === 'refresh') {
    // Double-submit: header must match cookie or the server answers 403.
    const csrf = readCsrfCookie()
    if (csrf) {
      headers['X-CSRFToken'] = csrf
    }
  }

  const session = await requestJson<AuthSession>(`/auth/${path}`, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
  })
  setAccessToken(session.access)
  return session
}

export function login(email: string, password: string): Promise<AuthSession> {
  return postSession('login', { email, password })
}

export interface RegisterInput {
  email: string
  password: string
  first_name: string
  last_name: string
}

export function register(input: RegisterInput): Promise<AuthSession> {
  // No `role` field: the server ignores client-supplied roles (ADR-014 decision 2).
  return postSession('register', { ...input })
}

export function refreshSession(): Promise<AuthSession> {
  return postSession('refresh')
}

export async function logout(): Promise<void> {
  const csrf = readCsrfCookie()
  try {
    await requestJson<void>('/auth/logout', {
      method: 'POST',
      headers: csrf ? { 'X-CSRFToken': csrf } : {},
    })
  } finally {
    // Local state is cleared even if the network call fails: the user asked to
    // leave, and the cookie is revoked server-side when it does reach Django.
    setAccessToken(null)
  }
}

/**
 * Authenticated request: Bearer header + one silent refresh on 401.
 *
 * The retry happens at most once per call and only when a token existed to
 * begin with, so a genuinely rejected token cannot spin into a refresh loop.
 */
export async function authedJson<T>(path: string, init?: RequestInit): Promise<T> {
  const call = (token: string | null): Promise<T> =>
    requestJson<T>(path, {
      ...init,
      headers: {
        ...init?.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })

  try {
    return await call(getAccessToken())
  } catch (error) {
    if (error instanceof ApiError && error.status === 401 && getAccessToken()) {
      try {
        await refreshSession()
      } catch (refreshError) {
        // The refresh was rejected (expired/revoked/replayed): drop the dead
        // token so the session is honestly anonymous instead of retrying with
        // a known-bad credential on the next request (docs/05 section 3).
        setAccessToken(null)
        throw refreshError
      }
      return call(getAccessToken())
    }
    throw error
  }
}

/** GET /auth/me/ — restores the full profile on boot (docs/api/auth.md). */
export function fetchMe(): Promise<AuthUser> {
  return authedJson<AuthUser>('/auth/me')
}
