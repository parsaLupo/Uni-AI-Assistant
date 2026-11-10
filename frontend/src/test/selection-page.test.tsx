// @vitest-environment jsdom
/**
 * Phase 11 page-level journey: the /selection surface must render exactly what
 * the engine returned (verdict badge, machine-readable reasons, what-if credit
 * totals, the backend-provided Persian explanation) and send the documented
 * request body. The `fetch` stub stands in for Django; no fixture is imported
 * by production code.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { CourseSelectionPage } from '../features/selection'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const BASE_DECISION = {
  course: { code: '1916003', title: 'ساختمان داده', credits: 3 },
  eligible: true,
  reasons: [],
  term_name: 'نیمسال اول ۱۴۰۵-۱۴۰۶',
  passed_course_codes: ['1916002'],
  missing_prerequisite_codes: [],
  planned_course_codes: ['1916002'],
  extra_course_codes: [],
  credit_totals: {
    limit: 20,
    planned: 3,
    candidate: 3,
    extra: 0,
    total_with_candidate: 6,
    over_limit: false,
  },
  engine_version: 'phase11-rules-v1',
  explanation: {
    text: 'نتیجه بررسی قواعد انتخاب واحد… شرایط لازم برآورده است.',
    source: 'composed',
    engine_eligible: true,
  },
}

const ELIGIBLE = { ...BASE_DECISION }

const INELIGIBLE = {
  ...BASE_DECISION,
  eligible: false,
  extra_course_codes: ['1916001'],
  credit_totals: { ...BASE_DECISION.credit_totals, extra: 1, total_with_candidate: 7 },
  reasons: [
    {
      code: 'PREREQUISITE_MISSING',
      message: 'ابتدا باید این پیش‌نیازها را با موفقیت بگذرانید: 1916002',
      params: { codes: ['1916002'], count: 1 },
    },
  ],
  missing_prerequisite_codes: ['1916002'],
  explanation: {
    text: 'انتخاب این درس مجاز نیست. دلایل:\n- ابتدا باید پیش‌نیاز 1916002 …',
    source: 'composed',
    engine_eligible: false,
  },
}

let fetchMock: ReturnType<typeof vi.fn>
const requested: Array<{ url: string; init: RequestInit | undefined }> = []
let nextSelectionResponse: unknown = ELIGIBLE

function respond(input: RequestInfo | URL): Response {
  const path = new URL(String(input), 'http://localhost').pathname
  if (path === '/api/v1/auth/refresh/') {
    // Anonymous boot in tests; the page itself relies on authedJson's Bearer
    // token path, which the stubbed server ignores.
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (path === '/api/v1/students/me/course-selection/') {
    return json(nextSelectionResponse)
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
        <MemoryRouter initialEntries={['/selection']}>
          <CourseSelectionPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

function submitCheck() {
  fireEvent.change(screen.getByLabelText('کد درس'), {
    target: { value: '1916003' },
  })
  const extras = screen.getByLabelText(/درس‌های فرضی/)
  if (extras) fireEvent.change(extras, { target: { value: '1916001، 1916002' } })
  fireEvent.click(screen.getByRole('button', { name: 'بررسی کنم' }))
}

beforeEach(() => {
  requested.length = 0
  nextSelectionResponse = ELIGIBLE
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
    requested.push({ url: new URL(String(input), 'http://localhost').pathname, init })
    return Promise.resolve(respond(input))
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('course selection page', () => {
  it('shows the honest empty state until a check has been run', () => {
    renderPage()
    expect(screen.getByRole('button', { name: 'بررسی کنم' })).toBeTruthy()
    expect(screen.queryByText('ساختمان داده')).toBeNull()
  })

  it('sends course_code plus comma-separated extras and renders the eligible verdict', async () => {
    renderPage()
    submitCheck()

    expect(await screen.findByText(/ساختمان داده/)).toBeTruthy()
    expect(screen.getByText('مجاز')).toBeTruthy()
    expect(screen.queryByText('دلایل تأیید نشدن')).toBeNull()
    expect(screen.getByText(/نتیجه بررسی قواعد/)).toBeTruthy()
    expect(screen.getByText('نسخه موتور قواعد: phase11-rules-v1')).toBeTruthy()

    // What-if extras are split on the Arabic comma and forwarded verbatim.
    const call = requested.find(
      (entry) => entry.url === '/api/v1/students/me/course-selection/',
    )
    expect(call).toBeTruthy()
    const body = JSON.parse(String(call?.init?.body ?? '{}'))
    expect(body.course_code).toBe('1916003')
    expect(body.extra_course_codes).toEqual(['1916001', '1916002'])

    // What-if totals show Persian digits (6 = 3 planned + 3 candidate).
    expect(screen.getByText('۶')).toBeTruthy()
  })

  it('renders machine-readable reasons for an ineligible verdict', async () => {
    nextSelectionResponse = INELIGIBLE
    renderPage()
    submitCheck()

    expect(await screen.findByText('غیرمجاز')).toBeTruthy()
    expect(screen.getByText('دلایل تأیید نشدن')).toBeTruthy()
    expect(screen.getByText('PREREQUISITE_MISSING')).toBeTruthy()
    expect(
      screen.getByText('ابتدا باید این پیش‌نیازها را با موفقیت بگذرانید: 1916002'),
    ).toBeTruthy()
    expect(screen.getByText(/انتخاب این درس مجاز نیست/)).toBeTruthy()

    await waitFor(() => {
      const reasons = screen.getAllByText('PREREQUISITE_MISSING')
      expect(reasons.length).toBeGreaterThan(0)
    })
  })

  it('surfaces the documented Persian error on a failed request', async () => {
    nextSelectionResponse = { error: { code: 'VALIDATION_ERROR', message: '', details: {} } }
    renderPage()
    fetchMock.mockImplementation((input: RequestInfo | URL, init: RequestInit | undefined) => {
      requested.push({ url: new URL(String(input), 'http://localhost').pathname, init })
      // The real backend answers 400 for an empty course code before any
      // engine call; the page must translate that code, not the raw message.
      return Promise.resolve(json(nextSelectionResponse, 400))
    })
    submitCheck()

    expect(await screen.findByText('اطلاعات واردشده معتبر نیست.')).toBeTruthy()
  })

  it('keeps the submit button disabled without a course code', () => {
    renderPage()
    const button = screen.getByRole('button', { name: 'بررسی کنم' }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
  })
})
