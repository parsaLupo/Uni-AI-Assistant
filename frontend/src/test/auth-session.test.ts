/**
 * Phase 03 frontend auth logic tests (docs/05 section 3, ADR-014/015).
 *
 * These exercise the token/CSRF/refresh rules in a plain Node environment with
 * a stubbed fetch — no DOM library is added because AGENTS.md rule 10 blocks
 * dependencies a phase does not need; component rendering tests belong to
 * Phase 05 once testing-library is justified.
 *
 * Notably, `localStorage` does not exist in this environment at all, so any
 * attempt by the code to persist the token there would throw and fail here —
 * the in-memory-only requirement is enforced by construction.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authedJson, login, logout, readCsrfCookie, refreshSession } from '../features/auth/api'
import { getAccessToken, setAccessToken } from '../features/auth/session'
import { persianErrorText } from '../i18n/fa'

const SESSION_BODY = {
  access: 'access-token-1',
  user: { id: 1, email: 'student@example.edu', role: 'STUDENT' },
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function errorResponse(code: string, status: number): Response {
  return jsonResponse({ error: { code, message: code, details: {} } }, status)
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  setAccessToken(null)
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  // Node has no document; a minimal stub lets the CSRF cookie reader run.
  vi.stubGlobal('document', { cookie: '' })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('login', () => {
  it('keeps the access token in memory only', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SESSION_BODY))

    const session = await login('student@example.edu', 'secret')

    expect(session.access).toBe('access-token-1')
    expect(getAccessToken()).toBe('access-token-1')
    // Nothing was written to any web storage (it does not even exist here).
    expect('localStorage' in globalThis).toBe(false)
    expect('sessionStorage' in globalThis).toBe(false)
    // The request body carries credentials, never a client-chosen role.
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(String(init.body)).toContain('student@example.edu')
    expect(String(init.body)).not.toContain('role')
  })
})

describe('refreshSession', () => {
  it('echoes the csrftoken cookie in X-CSRFToken (double submit, OA-23)', async () => {
    ;(globalThis as { document: { cookie: string } }).document.cookie = 'csrftoken=csrf-123'
    fetchMock.mockResolvedValueOnce(jsonResponse(SESSION_BODY))

    await refreshSession()

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>)['X-CSRFToken']).toBe('csrf-123')
  })

  it('returns null without a cookie instead of sending a stale header', () => {
    expect(readCsrfCookie()).toBeNull()
  })
})

describe('authedJson', () => {
  it('sends Authorization from the in-memory token', async () => {
    setAccessToken('access-token-1')
    fetchMock.mockResolvedValueOnce(jsonResponse({ id: 1 }))

    await authedJson('/students/me')

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer access-token-1')
  })

  it('refreshes silently once and retries after a 401', async () => {
    setAccessToken('expired-token')
    fetchMock
      .mockResolvedValueOnce(errorResponse('AUTHENTICATION_REQUIRED', 401))
      .mockResolvedValueOnce(jsonResponse({ ...SESSION_BODY, access: 'access-token-2' }))
      .mockResolvedValueOnce(jsonResponse({ id: 1, email: 'student@example.edu' }))

    const me = await authedJson<{ id: number }>('/auth/me')

    expect(me.id).toBe(1)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    // Call order: failed authed GET → refresh → retried GET with the new token.
    const retry = fetchMock.mock.calls[2] as [string, RequestInit]
    expect((retry[1].headers as Record<string, string>).Authorization).toBe('Bearer access-token-2')
    expect(getAccessToken()).toBe('access-token-2')
  })

  it('does not loop when the retried request is rejected again', async () => {
    setAccessToken('expired-token')
    // Refresh succeeds, but the retried call is still rejected: the client must
    // give up after exactly one retry instead of refreshing again forever.
    fetchMock
      .mockResolvedValueOnce(errorResponse('AUTHENTICATION_REQUIRED', 401))
      .mockResolvedValueOnce(jsonResponse({ ...SESSION_BODY, access: 'access-token-2' }))
      .mockImplementation(() => Promise.resolve(errorResponse('AUTHENTICATION_REQUIRED', 401)))

    await expect(authedJson('/auth/me')).rejects.toMatchObject({
      code: 'AUTHENTICATION_REQUIRED',
    })
    // initial + refresh + one retry = exactly three calls, then stop.
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('propagates the failure when the refresh call itself is rejected', async () => {
    setAccessToken('expired-token')
    // A fresh Response per call: real fetch never hands back a consumed body.
    fetchMock.mockImplementation(() => Promise.resolve(errorResponse('AUTHENTICATION_REQUIRED', 401)))

    await expect(authedJson('/auth/me')).rejects.toMatchObject({
      code: 'AUTHENTICATION_REQUIRED',
    })
    // The failed refresh aborts the flow: initial call + refresh only.
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(getAccessToken()).toBeNull()
  })
})

describe('logout', () => {
  it('sends the CSRF header and clears the in-memory token', async () => {
    setAccessToken('access-token-1')
    ;(globalThis as { document: { cookie: string } }).document.cookie = 'csrftoken=csrf-123'
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await logout()

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>)['X-CSRFToken']).toBe('csrf-123')
    expect(getAccessToken()).toBeNull()
  })

  it('clears the local token even when the network call fails', async () => {
    setAccessToken('access-token-1')
    fetchMock.mockRejectedValueOnce(new TypeError('offline'))

    await expect(logout()).rejects.toThrow()
    expect(getAccessToken()).toBeNull()
  })
})

describe('Persian error rendering (docs/12 section 2)', () => {
  it('maps stable codes to Persian text', () => {
    expect(persianErrorText('AUTHENTICATION_REQUIRED')).toContain('وارد حساب')
    expect(persianErrorText('RATE_LIMITED')).toContain('بیش از حد مجاز')
  })

  it('never falls back to an English server message', () => {
    expect(persianErrorText('SOME_UNKNOWN_CODE', 'English text')).toContain('خطای غیرمنتظره')
    expect(persianErrorText('SOME_UNKNOWN_CODE', 'متن فارسی')).toBe('متن فارسی')
  })
})
