// @vitest-environment jsdom
/**
 * Phase 12 page-level journey: /notifications must render only what the
 * scoped list returned, keep reading an *explicit* action (per-row + mark-all
 * buttons POST to the documented endpoints), narrows unread rows server-side
 * via `?unread=true`, and honestly renders the empty and error states.
 * The `fetch` stub stands in for Django; no fixture is imported by production code.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { NotificationsPage } from '../features/notifications'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const UNREAD_ANNOUNCEMENT = {
  id: 11,
  type: 'ANNOUNCEMENT',
  title: 'اطلاعیه برنامه امتحانات',
  body: 'برنامه امتحانات ترم جاری اعلام شد.',
  link: '/announcements',
  is_read: false,
  read_at: null,
  expires_at: null,
  created_at: '2026-11-09T10:00:00Z',
}

const READ_DEADLINE = {
  id: 12,
  type: 'DEADLINE',
  title: 'مهلت ثبت‌نام',
  body: '',
  link: '',
  is_read: true,
  read_at: '2026-11-08T11:00:00Z',
  expires_at: '2026-12-01T00:00:00Z',
  created_at: '2026-11-08T08:00:00Z',
}

let rows: Array<Record<string, unknown>> = []
let unreadCount = 1
const requests: Array<{ path: string; search: string; init: RequestInit | undefined }> = []

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost')
  const entry = { path: url.pathname, search: url.search, init }
  requests.push(entry)

  if (url.pathname === '/api/v1/auth/refresh/') {
    return json(
      { error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } },
      401,
    )
  }
  if (url.pathname === '/api/v1/notifications/unread-count/') {
    return json({ unread_count: unreadCount })
  }
  if (url.pathname === '/api/v1/notifications/') {
    const results = url.search.includes('unread=true')
      ? rows.filter((row) => !row.is_read)
      : rows
    // `count` stays at the unfiltered total, matching the backend envelope.
    return json({ count: rows.length, next: null, previous: null, results })
  }
  const markMatch = url.pathname.match(/^\/api\/v1\/notifications\/(\d+)\/mark-read\/$/)
  if (markMatch) {
    const row = rows.find((candidate) => candidate.id === Number(markMatch[1]))
    if (row) {
      row.is_read = true
      unreadCount = Math.max(0, unreadCount - 1)
    }
    return json({ ...row, read_at: '2026-11-09T12:00:00Z' })
  }
  if (url.pathname === '/api/v1/notifications/mark-all-read/') {
    let updated = 0
    rows.forEach((row) => {
      if (!row.is_read) {
        row.is_read = true
        updated += 1
      }
    })
    unreadCount = 0
    return json({ updated })
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

let fetchMock: ReturnType<typeof vi.fn>

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={['/notifications']}>
          <NotificationsPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requests.length = 0
  rows = [
    { ...UNREAD_ANNOUNCEMENT },
    { ...READ_DEADLINE },
  ]
  unreadCount = 1
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) =>
    Promise.resolve(respond(input, init)),
  )
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('notifications page', () => {
  it('renders the scoped rows with Persian type labels and expiry', async () => {
    renderPage()

    expect(await screen.findByText('اطلاعیه برنامه امتحانات')).toBeTruthy()
    expect(screen.getByText('مهلت ثبت‌نام')).toBeTruthy()
    expect(screen.getByText('ناخوانده')).toBeTruthy()
    expect(screen.getByText(/بدون انقضا/)).toBeTruthy()

    // The list call went to the documented endpoint.
    expect(
      requests.some((entry) => entry.path === '/api/v1/notifications/'),
    ).toBe(true)
  })

  it('marks one row read via POST and refetches the list', async () => {
    renderPage()
    expect(await screen.findByText('اطلاعیه برنامه امتحانات')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'خواندم' }))

    await waitFor(() => {
      expect(
        requests.filter((entry) => entry.path === '/api/v1/notifications/11/mark-read/')
          .length,
      ).toBe(1)
      // The server-side state change refetched the active list query.
      expect(
        requests.filter(
          (entry) =>
            entry.path === '/api/v1/notifications/' &&
            entry.init?.method !== 'POST',
        ).length,
      ).toBeGreaterThan(1)
    })
  })

  it('marks all unread rows read in one call', async () => {
    renderPage()
    const markAll = await screen.findByRole('button', {
      name: 'علامت‌گذاری همه به‌عنوان خوانده‌شده',
    })
    fireEvent.click(markAll)

    await waitFor(() => {
      expect(
        requests.some(
          (entry) => entry.path === '/api/v1/notifications/mark-all-read/',
        ),
      ).toBe(true)
    })
  })

  it('hides the mark-all button and the per-row action when every active row is read', async () => {
    rows = [{ ...READ_DEADLINE }]
    unreadCount = 0
    renderPage()

    expect(await screen.findByText('مهلت ثبت‌نام')).toBeTruthy()
    expect(
      screen.queryByRole('button', {
        name: 'علامت‌گذاری همه به‌عنوان خوانده‌شده',
      }),
    ).toBeNull()
    // Already-read rows carry no mark-read action either.
    expect(screen.queryByRole('button', { name: 'خواندم' })).toBeNull()
    expect(screen.queryByText('ناخوانده')).toBeNull()
  })

  it('narrows to unread rows server-side with ?unread=true', async () => {
    renderPage()
    expect(await screen.findByText('اطلاعیه برنامه امتحانات')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('وضعیت'), {
      target: { value: 'unread' },
    })

    await waitFor(() => {
      expect(requests.some((entry) => entry.search.includes('unread=true'))).toBe(
        true,
      )
    })
  })

  it('surfaces the documented Persian error envelope on failure', async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
      const url = new URL(String(input), 'http://localhost')
      requests.push({ path: url.pathname, search: url.search, init })
      if (url.pathname === '/api/v1/auth/refresh/') {
        return Promise.resolve(
          json(
            { error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } },
            401,
          ),
        )
      }
      return Promise.resolve(
        json({ error: { code: 'INTERNAL_ERROR', message: '', details: {} } }, 500),
      )
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    expect(await screen.findByText('خطای غیرمنتظره‌ای رخ داد؛ لطفاً کمی بعد تلاش کنید.')).toBeTruthy()
  })

  it('starts with the honest empty state suggestion filters can be cleared', async () => {
    rows = []
    unreadCount = 0
    renderPage()

    expect(await screen.findByText('یادآوری فعالی ندارید.')).toBeTruthy()
    // URL state starts clean: page/scope params absent on first load.
    expect(requests.some((entry) => entry.search.includes('unread=true'))).toBe(
      false,
    )
  })
})
