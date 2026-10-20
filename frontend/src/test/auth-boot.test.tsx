// @vitest-environment jsdom
/**
 * Regression: the session gate must settle under React StrictMode (Phase 05).
 *
 * StrictMode mounts effect 1, cleans it up, then runs effect 2. The original
 * implementation let effect 2 early-return behind a `booted` ref while effect
 * 1's cleanup flipped a `cancelled` flag that suppressed the state update —
 * so the boot promise settled with `cancelled === true` and the guard spun on
 * "در حال بازیابی نشست…" forever. These tests render the provider inside
 * StrictMode (double-invoked in React's development build, which Vitest uses)
 * and assert the status reaches a terminal state, exactly once per network
 * call — a second POST /auth/refresh would race the rotating cookie and trip
 * reuse detection (ADR-014).
 */

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '../features/auth/AuthProvider'

function StatusProbe() {
  const { status, user } = useAuth()
  return (
    <div>
      <p data-testid="status">{status}</p>
      <p data-testid="user">{user?.email ?? '-'}</p>
    </div>
  )
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

const SESSION = {
  access: 'access-1',
  user: { id: 1, email: 'student@semnan.local', role: 'STUDENT' },
}
const PROFILE = {
  id: 1,
  email: 'student@semnan.local',
  role: 'STUDENT',
  first_name: 'سارا',
  last_name: 'محمدی',
  is_active: true,
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  // Vitest runs without `globals: true`, so RTL cannot register its own
  // auto-cleanup — without this the next test finds two probes in the DOM.
  cleanup()
  vi.unstubAllGlobals()
})

describe('AuthProvider boot under StrictMode', () => {
  it('settles to anonymous when the silent refresh is rejected', async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(errorResponse('AUTHENTICATION_REQUIRED', 401)),
    )

    render(
      <StrictMode>
        <AuthProvider>
          <StatusProbe />
        </AuthProvider>
      </StrictMode>,
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('anonymous'))
    // One POST total: the booted ref keeps StrictMode from firing a second
    // refresh against the same rotating cookie.
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('settles to authenticated when refresh and /auth/me succeed', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(SESSION))
      .mockResolvedValueOnce(jsonResponse(PROFILE))

    render(
      <StrictMode>
        <AuthProvider>
          <StatusProbe />
        </AuthProvider>
      </StrictMode>,
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('authenticated'))
    expect(screen.getByTestId('user').textContent).toBe('student@semnan.local')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})