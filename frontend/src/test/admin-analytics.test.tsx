// @vitest-environment jsdom
/**
 * Phase 13 page-level journey: /admin/analytics must render exactly what
 * `GET /admin/analytics/dashboard/` returned (aggregate-only counts, mode
 * distribution, top documents) plus the read-only audit-log table driven by
 * `GET /admin/analytics/audit-log/?page=…&action=…`. The `fetch` stub stands
 * in for Django; no fixture is imported by production code (docs/06 §8).
 */

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { AdminAnalyticsPage } from '../features/admin'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const DASHBOARD = {
  users: {
    active_users: 12,
    recently_active_users: 4,
    by_role: [
      { role: 'STUDENT', count: 10 },
      { role: 'ADMIN', count: 2 },
    ],
  },
  questions: {
    total: 37,
    last_7_days: 5,
    answers: 36,
    insufficient_evidence: 2,
  },
  topic_distribution: [
    { mode: 'STRUCTURED', count: 20 },
    { mode: 'RAG', count: 16 },
  ],
  top_documents: [
    {
      id: 9,
      title: 'آیین‌نامه آموزشی',
      document_type: 'REG',
      academic_year: '1405-1406',
      citation_count: 8,
    },
  ],
  ai: { total_requests: 48, error_count: 3, avg_latency_ms: 742.5 },
  documents_total: 21,
  generated_at: '2026-11-09T10:00:00+03:30',
}

const AUDIT_PAGE = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 101,
      created_at: '2026-11-08T09:30:00+03:30',
      actor: 3,
      actor_email: 'admin@semnan.local',
      action: 'CREATE',
      entity_type: 'academics.Faculty',
      entity_id: '7',
      metadata: {},
    },
  ],
}

let fetchMock: ReturnType<typeof vi.fn>
const requested: Array<{ url: string; query: string }> = []

function respond(input: RequestInfo | URL): Response {
  const url = new URL(String(input), 'http://localhost')
  if (url.pathname === '/api/v1/auth/refresh/') {
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (url.pathname === '/api/v1/admin/analytics/dashboard/') {
    return json(DASHBOARD)
  }
  if (url.pathname === '/api/v1/admin/analytics/audit-log/') {
    return json(AUDIT_PAGE)
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={['/admin/analytics']}>
          <AdminAnalyticsPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requested.length = 0
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
    const url = new URL(String(input), 'http://localhost')
    requested.push({ url: url.pathname, query: url.search })
    void init
    return Promise.resolve(respond(input))
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('admin analytics page', () => {
  it('renders the aggregate metrics with Persian digits and no message content', async () => {
    renderPage()

    expect(await screen.findByText('۱۲')).toBeTruthy() // active_users
    expect(screen.getByText('۳۷')).toBeTruthy() // questions total
    expect(screen.getByText('۴۸')).toBeTruthy() // ai total_requests
    expect(screen.getByText(/خطاهای هوش مصنوعی: ۳/)).toBeTruthy() // ai error hint
    expect(screen.getByText('۷۴۲.۵')).toBeTruthy() // avg latency (ms)
    expect(screen.getByText('پاسخ از داده ساختاریافته')).toBeTruthy()
    expect(screen.getByText('آیین‌نامه آموزشی')).toBeTruthy()
    expect(screen.getAllByText('۸').length).toBeGreaterThan(0) // citation_count

    // Aggregate-only contract: a raw payload field name never leaks, and the
    // stub never fabricates message text (docs/06 §8).
    expect(screen.queryByText('content')).toBeNull()
  })

  it('renders the audit-log viewer rows', async () => {
    renderPage()

    expect(await screen.findByText('academics.Faculty')).toBeTruthy()
    expect(screen.getByText('#7')).toBeTruthy()
    expect(screen.getByText('admin@semnan.local')).toBeTruthy()
    expect(screen.getByText('گزارش حسابرسی')).toBeTruthy()
  })

  it('sends both aggregate-only endpoints and lets the action filter refilter the audit page', async () => {
    renderPage()
    await screen.findByText('academics.Faculty')

    const dashboardCalls = requested.filter(
      (entry) => entry.url === '/api/v1/admin/analytics/dashboard/',
    )
    expect(dashboardCalls).toHaveLength(1)

    const auditCalls = requested.filter(
      (entry) => entry.url === '/api/v1/admin/analytics/audit-log/',
    )
    expect(auditCalls).toHaveLength(1)
    expect(auditCalls[0].query).toContain('page=1')
    expect(auditCalls[0].query).toContain('page_size=15')

    // Changing the action filter commits `?auditAction=CREATE&auditPage=1`.
    fireEvent.change(screen.getByLabelText(/اقدام/), {
      target: { value: 'CREATE' },
    })
    await vi.waitFor(() => {
      const calls = requested.filter(
        (entry) => entry.url === '/api/v1/admin/analytics/audit-log/',
      )
      expect(
        calls.some((entry) => entry.query.includes('action=CREATE')),
      ).toBe(true)
    })
  })
})
