// @vitest-environment jsdom
/**
 * Phase 13 — /admin/users page journey: list from GET /admin/users/ (filters
 * on the wire), create via POST with validated payload, and the deactivate
 * confirmation that DELETEs (soft-delete per docs/api/admin.md). The `fetch`
 * stub stands in for Django; no fixture is imported by production code.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { AdminUsersPage } from '../features/admin'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const USERS_PAGE = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      email: 'student@semnan.local',
      first_name: 'زهرا',
      last_name: 'کریمی',
      role: 'STUDENT',
      is_active: true,
    },
    {
      id: 2,
      email: 'admin@semnan.local',
      first_name: '',
      last_name: '',
      role: 'ADMIN',
      is_active: true,
    },
  ],
}

let fetchMock: ReturnType<typeof vi.fn>
const requested: Array<{ url: string; query: string; method: string; body: string | null }> = []

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost')
  if (url.pathname === '/api/v1/auth/refresh/') {
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (url.pathname === '/api/v1/admin/users/' && (!init?.method || init.method === 'GET')) {
    return json(USERS_PAGE)
  }
  if (url.pathname === '/api/v1/admin/users/' && init?.method === 'POST') {
    return json({
      id: 9,
      email: 'new@semnan.local',
      first_name: 'مخصوص',
      last_name: 'آزمون',
      role: 'PROFESSOR',
      is_active: true,
    }, 201)
  }
  const detail = url.pathname.match(/^\/api\/v1\/admin\/users\/(\d+)\/$/)
  if (detail && init?.method === 'DELETE') {
    return new Response(null, { status: 204 })
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

function renderPage(initial = '/admin/users') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initial]}>
          <AdminUsersPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requested.length = 0
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
    const url = new URL(String(input), 'http://localhost')
    const body = typeof init?.body === 'string' ? init.body : null
    requested.push({
      url: url.pathname,
      query: url.search,
      method: init?.method ?? 'GET',
      body,
    })
    return Promise.resolve(respond(input, init))
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('admin users page', () => {
  it('renders user rows from the admin users endpoint', async () => {
    renderPage()

    expect(await screen.findByText('student@semnan.local')).toBeTruthy()
    expect(screen.getByText('admin@semnan.local')).toBeTruthy()
    expect(screen.getAllByText('دانشجو').length).toBeGreaterThan(0)
    expect(screen.getAllByText('مدیر').length).toBeGreaterThan(0)

    const listCalls = requested.filter(
      (entry) => entry.url === '/api/v1/admin/users/' && entry.method === 'GET',
    )
    expect(listCalls).toHaveLength(1)
    expect(listCalls[0].query).toContain('page=1')
  })

  it('filters by role on the wire', async () => {
    renderPage()
    await screen.findByText('student@semnan.local')

    fireEvent.change(screen.getByLabelText(/نقش/), { target: { value: 'ADMIN' } })
    await waitFor(() => {
      const calls = requested.filter(
        (entry) => entry.url === '/api/v1/admin/users/' && entry.method === 'GET',
      )
      expect(calls.some((entry) => entry.query.includes('role=ADMIN'))).toBe(true)
    })
  })

  it('creates a user through POST with a validated payload', async () => {
    renderPage()
    await screen.findByText('student@semnan.local')

    fireEvent.click(screen.getByRole('button', { name: 'افزودن' }))
    expect(await screen.findByText('افزودن کاربر')).toBeTruthy()

    // Invalid email is rejected client-side with a Persian message.
    fireEvent.change(screen.getByLabelText(/ایمیل/), {
      target: { value: 'not-an-email' },
    })
    fireEvent.change(screen.getByLabelText(/گذرواژه/), {
      target: { value: 'Str0ng-Pass!' },
    })
    fireEvent.submit(screen.getByRole('button', { name: 'ذخیره' }).closest('form')!)
    expect(await screen.findByText('ایمیل معتبر وارد کنید.')).toBeTruthy()

    fireEvent.change(screen.getByLabelText(/ایمیل/), {
      target: { value: 'new@semnan.local' },
    })
    fireEvent.submit(screen.getByRole('button', { name: 'ذخیره' }).closest('form')!)

    await waitFor(() => {
      const post = requested.find(
        (entry) => entry.url === '/api/v1/admin/users/' && entry.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(post!.body!)).toMatchObject({
        email: 'new@semnan.local',
        role: 'STUDENT',
      })
    })
  })

  it('deactivates a user only after confirmation', async () => {
    renderPage()
    await screen.findByText('student@semnan.local')

    const removeButtons = screen.getAllByRole('button', { name: 'حذف' })
    fireEvent.click(removeButtons[0])
    expect(
      await screen.findByText('با غیرفعال‌سازی، ورود این کاربر مسدود می‌شود و ردیف حساب باقی می‌ماند (حذف نرم).'),
    ).toBeTruthy()

    // The dialog holds confirm ('حذف') and cancel ('انصراف'); click confirm.
    const dialog = await screen.findByRole('dialog', { name: 'غیرفعال‌سازی حساب' })
    const confirm = Array.from(dialog.querySelectorAll('button')).find(
      (button) => button.textContent === 'حذف',
    )!
    fireEvent.click(confirm)

    await waitFor(() => {
      expect(
        requested.some(
          (entry) => entry.url === '/api/v1/admin/users/1/' && entry.method === 'DELETE',
        ),
      ).toBe(true)
    })
  })
})
