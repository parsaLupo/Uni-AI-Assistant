// @vitest-environment jsdom
/**
 * Phase 11 page-level journey: the /selection surface must render exactly what
 * the engine returned (verdict badge, machine-readable reasons, what-if credit
 * totals, the backend-provided Persian explanation) and send the documented
 * request body. The `fetch` stub stands in for Django; no fixture is imported
 * by production code.
 *
 * The added cases pin the code-or-name workflow: the page always submits
 * `course_query`, renders the ambiguity list without a verdict, and only calls
 * the engine for the course code the student explicitly picks.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { CourseSelectionPage } from '../features/selection'
import { selectionPage } from '../i18n/fa'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const BASE_DECISION = {
  status: 'resolved' as const,
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

const AMBIGUOUS = {
  status: 'ambiguous' as const,
  query: 'نظریه زبان ها و ماشین ها',
  total: 2,
  candidates: [
    {
      code: '1916010',
      title: 'نظریه زبان‌ها و ماشین‌ها',
      credits: 3,
      department: 'گروه مهندسی کامپیوتر',
      course_type: 'اصلی',
    },
    {
      code: '1916011',
      title: 'نظریه زبانها و ماشینها',
      credits: 3,
      department: 'گروه مهندسی کامپیوتر',
      course_type: 'اصلی',
    },
  ],
}

const NOT_FOUND_BODY = {
  error: {
    code: 'NOT_FOUND',
    message: 'درسی با این کد یا نام در پایگاه داده یافت نشد؛ کد درس یا نام دقیق آن را وارد کنید.',
    details: { query: 'نام کاملاً ناموجود' },
  },
}

let fetchMock: ReturnType<typeof vi.fn>
const requested: Array<{ url: string; init: RequestInit | undefined }> = []
let nextSelectionResponse: unknown = ELIGIBLE
let nextSelectionStatus = 200

function respond(input: RequestInfo | URL): Response {
  const path = new URL(String(input), 'http://localhost').pathname
  if (path === '/api/v1/auth/refresh/') {
    // Anonymous boot in tests; the page itself relies on authedJson's Bearer
    // token path, which the stubbed server ignores.
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (path === '/api/v1/students/me/course-selection/') {
    return json(nextSelectionResponse, nextSelectionStatus)
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

function typeQuery(value: string) {
  fireEvent.change(screen.getByLabelText(selectionPage.courseQueryLabel), {
    target: { value },
  })
}

function submitCheck(query = '1916003') {
  typeQuery(query)
  const extras = screen.getByLabelText(/درس‌های فرضی/)
  if (extras) fireEvent.change(extras, { target: { value: '1916001، 1916002' } })
  fireEvent.click(screen.getByRole('button', { name: selectionPage.check }))
}

function selectionCalls() {
  return requested.filter((entry) => entry.url === '/api/v1/students/me/course-selection/')
}

beforeEach(() => {
  requested.length = 0
  nextSelectionResponse = ELIGIBLE
  nextSelectionStatus = 200
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
    expect(screen.getByRole('button', { name: selectionPage.check })).toBeTruthy()
    expect(screen.queryByText('ساختمان داده')).toBeNull()
    // The input advertises both search methods.
    expect(screen.getByLabelText(selectionPage.courseQueryLabel)).toBeTruthy()
    expect(screen.getByPlaceholderText(selectionPage.courseQueryPlaceholder)).toBeTruthy()
  })

  it('sends course_query plus comma-separated extras and renders the eligible verdict', async () => {
    renderPage()
    submitCheck()

    expect(await screen.findByText(/ساختمان داده/)).toBeTruthy()
    expect(screen.getByText('مجاز')).toBeTruthy()
    expect(screen.queryByText('دلایل تأیید نشدن')).toBeNull()
    expect(screen.getByText(/نتیجه بررسی قواعد/)).toBeTruthy()
    expect(screen.getByText('نسخه موتور قواعد: phase11-rules-v1')).toBeTruthy()

    // What-if extras are split on the Arabic comma and forwarded verbatim.
    const call = selectionCalls()[0]
    expect(call).toBeTruthy()
    const body = JSON.parse(String(call?.init?.body ?? '{}'))
    expect(body.course_query).toBe('1916003')
    expect(body.extra_course_codes).toEqual(['1916001', '1916002'])

    // What-if totals show Persian digits (6 = 3 planned + 3 candidate).
    expect(screen.getByText('۶')).toBeTruthy()
  })

  it('submits a Persian course name through the same course_query field', async () => {
    renderPage()
    submitCheck('نظریه زبان‌ها و ماشین‌ها')

    expect(await screen.findByText(/ساختمان داده/)).toBeTruthy()
    const call = selectionCalls()[0]
    expect(JSON.parse(String(call?.init?.body ?? '{}')).course_query).toBe(
      'نظریه زبان‌ها و ماشین‌ها',
    )
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

  it('shows every candidate for an ambiguous name and evaluates none of them', async () => {
    nextSelectionResponse = AMBIGUOUS
    renderPage()
    submitCheck('نظریه زبان ها و ماشین ها')

    expect(await screen.findByText(selectionPage.ambiguousTitle)).toBeTruthy()
    expect(screen.getByText(selectionPage.ambiguousHint)).toBeTruthy()

    // Both rows are listed with their distinguishing fields.
    expect(screen.getByText('نظریه زبان‌ها و ماشین‌ها')).toBeTruthy()
    expect(screen.getByText('نظریه زبانها و ماشینها')).toBeTruthy()
    expect(screen.getByText('1916010')).toBeTruthy()
    expect(screen.getByText('1916011')).toBeTruthy()
    expect(screen.getAllByText('گروه مهندسی کامپیوتر').length).toBe(2)
    expect(screen.getAllByText('۳ واحد').length).toBe(2)

    // No verdict and no second (engine) request happened automatically.
    expect(screen.queryByText('مجاز')).toBeNull()
    expect(screen.queryByText('غیرمجاز')).toBeNull()
    expect(selectionCalls().length).toBe(1)
  })

  it('evaluates only the candidate the student explicitly selects', async () => {
    nextSelectionResponse = AMBIGUOUS
    renderPage()
    submitCheck('نظریه زبان ها و ماشین ها')

    await screen.findByText(selectionPage.ambiguousTitle)
    // The second response is the engine verdict for the chosen code.
    nextSelectionResponse = {
      ...ELIGIBLE,
      course: { code: '1916011', title: 'نظریه زبانها و ماشینها', credits: 3 },
    }

    const rows = screen.getAllByRole('button', { name: new RegExp(selectionPage.selectCandidate) })
    expect(rows.length).toBe(2)
    fireEvent.click(rows[1])

    expect(await screen.findByText(/نظریه زبانها و ماشینها/)).toBeTruthy()
    expect(screen.getByText('مجاز')).toBeTruthy()

    const calls = selectionCalls()
    expect(calls.length).toBe(2)
    // The engine receives the chosen catalog code, not the typed name.
    expect(JSON.parse(String(calls[1]?.init?.body ?? '{}')).course_query).toBe('1916011')
  })

  it('shows the dedicated not-found state for an unknown name', async () => {
    nextSelectionResponse = NOT_FOUND_BODY
    nextSelectionStatus = 404
    renderPage()
    submitCheck('نام کاملاً ناموجود')

    expect(await screen.findByText(selectionPage.notFoundTitle)).toBeTruthy()
    expect(screen.getByText(selectionPage.notFoundMessage)).toBeTruthy()
    // It is not the generic error panel, and no verdict is shown.
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByText('مجاز')).toBeNull()
  })

  it('does not fire a second request when the button is double-clicked', async () => {
    let resolveFetch: (response: Response) => void = () => undefined
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init: RequestInit | undefined) => {
        const path = new URL(String(input), 'http://localhost').pathname
        requested.push({ url: path, init })
        if (path === '/api/v1/auth/refresh/') {
          return Promise.resolve(
            json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401),
          )
        }
        return new Promise<Response>((resolve) => {
          resolveFetch = resolve
        })
      },
    )
    renderPage()
    typeQuery('1916003')

    const button = screen.getByRole('button', { name: selectionPage.check }) as HTMLButtonElement
    fireEvent.click(button)
    fireEvent.click(button)

    await waitFor(() => expect(button.disabled).toBe(true))
    resolveFetch(json(ELIGIBLE))
    expect(await screen.findByText(/ساختمان داده/)).toBeTruthy()
    expect(selectionCalls().length).toBe(1)
  })

  it('surfaces the documented Persian error on a failed request', async () => {
    nextSelectionResponse = { error: { code: 'VALIDATION_ERROR', message: '', details: {} } }
    nextSelectionStatus = 400
    renderPage()
    submitCheck()

    expect(await screen.findByText('اطلاعات واردشده معتبر نیست.')).toBeTruthy()
  })

  it('keeps the submit button disabled without a course query', () => {
    renderPage()
    const button = screen.getByRole('button', { name: selectionPage.check }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
  })
})
