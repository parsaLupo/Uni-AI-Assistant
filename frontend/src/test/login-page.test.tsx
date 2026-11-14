// @vitest-environment jsdom
/**
 * /login — password-field icon states and the post-login landing route.
 *
 * Icon contract: the key icon alone while the field is empty; the show/hide
 * toggle replaces it in the same slot once the user types (never both), and
 * the key returns when the field is cleared. The toggle is type="button" so
 * it can never submit the form.
 *
 * Redirect contract (`landingFor`): ADMIN/SUPERADMIN always land on `/admin`
 * — even when an intended URL (`state.from`) points elsewhere — while other
 * roles keep their previous landing (remembered URL, else the role home).
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { LoginPage } from '../features/auth/LoginPage'
import { landingFor } from '../features/auth/ProtectedRoute'
import { auth } from '../i18n/fa'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function user(role: string) {
  return {
    id: 1,
    email: `${role.toLowerCase()}@example.edu`,
    role,
    first_name: 'کاربر',
    last_name: 'آزمایشی',
  }
}

const requested: Array<{ path: string; method: string; body: string | null }> = []
let sessionUser = user('STUDENT')

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost')
  if (url.pathname === '/api/v1/auth/refresh/') {
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (url.pathname === '/api/v1/auth/login/' && init?.method === 'POST') {
    return json({ access: 'test-access', refresh: 'test-refresh', user: sessionUser })
  }
  if (url.pathname === '/api/v1/auth/me/') {
    return json(sessionUser)
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

const seen: string[] = []

function LocationRecorder() {
  const location = useLocation()
  useEffect(() => {
    seen.push(location.pathname)
  }, [location])
  return null
}

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        {/* Records every location, including routes that unmount /login. */}
        <LocationRecorder />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin" element={<div>admin-overview</div>} />
          <Route path="/dashboard" element={<div>student-dashboard</div>} />
          <Route path="*" element={<div>other</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  seen.length = 0
  requested.length = 0
  sessionUser = user('STUDENT')
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
    requested.push({
      path: new URL(String(input), 'http://localhost').pathname,
      method: init?.method ?? 'GET',
      body: typeof init?.body === 'string' ? init.body : null,
    })
    return Promise.resolve(respond(input, init))
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const passwordInput = () => screen.getByLabelText(auth.password) as HTMLInputElement
const toggle = () => screen.queryByRole('button', { name: auth.togglePassword })

describe('login page — password field icons', () => {
  it('shows only the key icon while the password is empty', async () => {
    renderLogin()
    await screen.findByText(auth.loginTitle)

    expect(screen.getByText('key')).toBeTruthy()
    expect(toggle()).toBeNull()
  })

  it('swaps the key for the eye toggle once the user types, never both', async () => {
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    expect(screen.queryByText('key')).toBeNull()
    expect(toggle()).toBeTruthy()
    expect(passwordInput().type).toBe('password')

    // Toggling reveals the value (eye-off glyph state)…
    fireEvent.click(toggle()!)
    expect(passwordInput().type).toBe('text')
    expect(toggle()!.getAttribute('aria-pressed')).toBe('true')

    // …and toggling again hides it.
    fireEvent.click(toggle()!)
    expect(passwordInput().type).toBe('password')
    expect(toggle()!.getAttribute('aria-pressed')).toBe('false')
  })

  it('returns to the key icon when the field is cleared', async () => {
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    expect(toggle()).toBeTruthy()
    fireEvent.change(passwordInput(), { target: { value: '' } })
    expect(screen.getByText('key')).toBeTruthy()
    expect(toggle()).toBeNull()
  })

  it('never submits the form when the eye toggle is clicked', async () => {
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(screen.getByLabelText(auth.email), {
      target: { value: 'admin@semnan.local' },
    })
    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    fireEvent.click(toggle()!)

    expect(
      requested.some((entry) => entry.path === '/api/v1/auth/login/'),
    ).toBe(false)
    // Still on the login screen.
    expect(screen.getByText(auth.loginTitle)).toBeTruthy()
  })
})

describe('login page — post-login redirect', () => {
  it('lands an admin on /admin after login', async () => {
    sessionUser = user('ADMIN')
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(screen.getByLabelText(auth.email), {
      target: { value: 'admin@semnan.local' },
    })
    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    fireEvent.click(screen.getByRole('button', { name: auth.submitLogin }))

    await waitFor(() => {
      expect(seen).toContain('/admin')
    })
    expect(screen.getByText('admin-overview')).toBeTruthy()
  })

  it('keeps the student landing on the student dashboard', async () => {
    sessionUser = user('STUDENT')
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(screen.getByLabelText(auth.email), {
      target: { value: 'student@semnan.local' },
    })
    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    fireEvent.click(screen.getByRole('button', { name: auth.submitLogin }))

    await waitFor(() => {
      expect(seen).toContain('/dashboard')
    })
    expect(screen.getByText('student-dashboard')).toBeTruthy()
  })

  it('lands a professor on the same student-level dashboard as before', async () => {
    sessionUser = user('PROFESSOR')
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(screen.getByLabelText(auth.email), {
      target: { value: 'prof@semnan.local' },
    })
    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    fireEvent.click(screen.getByRole('button', { name: auth.submitLogin }))

    await waitFor(() => {
      expect(seen).toContain('/dashboard')
    })
  })

  it('sends the credentials on the wire exactly once', async () => {
    sessionUser = user('ADMIN')
    renderLogin()
    await screen.findByText(auth.loginTitle)

    fireEvent.change(screen.getByLabelText(auth.email), {
      target: { value: 'admin@semnan.local' },
    })
    fireEvent.change(passwordInput(), { target: { value: 'Str0ng-Pass!' } })
    fireEvent.click(screen.getByRole('button', { name: auth.submitLogin }))

    await waitFor(() => {
      expect(seen).toContain('/admin')
    })
    const logins = requested.filter((entry) => entry.path === '/api/v1/auth/login/')
    expect(logins).toHaveLength(1)
    expect(JSON.parse(logins[0].body!)).toEqual({
      email: 'admin@semnan.local',
      password: 'Str0ng-Pass!',
    })
  })
})

describe('landingFor — post-login target selection', () => {
  it('pins admin roles to /admin regardless of any intended URL', () => {
    expect(landingFor({ role: 'ADMIN' }, '/profile')).toBe('/admin')
    expect(landingFor({ role: 'ADMIN' }, '/admin/users')).toBe('/admin')
    expect(landingFor({ role: 'ADMIN' }, undefined)).toBe('/admin')
    expect(landingFor({ role: 'SUPERADMIN' }, '/dashboard')).toBe('/admin')
  })

  it('keeps the previous behavior for every other role', () => {
    expect(landingFor({ role: 'STUDENT' }, '/profile')).toBe('/profile')
    expect(landingFor({ role: 'STUDENT' }, undefined)).toBe('/dashboard')
    expect(landingFor({ role: 'PROFESSOR' }, undefined)).toBe('/dashboard')
    expect(landingFor({ role: 'PROFESSOR' }, '/exams')).toBe('/exams')
    expect(landingFor(null, '/calendar')).toBe('/calendar')
    expect(landingFor(null, '/login')).toBe('/dashboard')
  })
})
