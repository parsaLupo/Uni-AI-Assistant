// @vitest-environment jsdom
/**
 * Phase 13 — /admin/users page journey: list from GET /admin/users/ (filters
 * on the wire), create via POST with validated payload, and the deactivate
 * confirmation that DELETEs (soft-delete per docs/api/admin.md). The `fetch`
 * stub stands in for Django; no fixture is imported by production code.
 */

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

const DEPARTMENTS_PAGE = {
  count: 1,
  next: null,
  previous: null,
  results: [
    { id: 5, name: 'گروه مهندسی کامپیوتر', code: '16', faculty: 1, is_active: true },
  ],
}

const COURSES_PAGE = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 11,
      code: '1916002',
      title: 'ریاضیات عمومی',
      credits: 3,
      course_type: 'پایه',
      active: true,
      prerequisites: [],
    },
    {
      id: 12,
      code: '1916008',
      title: 'نظریه زبان‌ها و ماشین‌ها',
      credits: 3,
      course_type: 'اصلی',
      active: true,
      prerequisites: [],
    },
  ],
}

const OFFERINGS_PAGE = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 21,
      course: { id: 11, code: '1916002', title: 'ریاضیات عمومی', credits: 3, course_type: '' },
      term: { id: 3, name: 'نیمسال اول ۱۴۰۵-۱۴۰۶', is_current: true },
      professor: null,
      section_code: '01',
      capacity: 40,
      status: 'OPEN',
      enrolled_count: 0,
    },
    {
      id: 22,
      course: { id: 12, code: '1916008', title: 'نظریه زبان‌ها و ماشین‌ها', credits: 3, course_type: '' },
      term: { id: 3, name: 'نیمسال اول ۱۴۰۵-۱۴۰۶', is_current: true },
      professor: null,
      section_code: '01',
      capacity: 40,
      status: 'OPEN',
      enrolled_count: 0,
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
  if (url.pathname === '/api/v1/departments/') {
    return json(DEPARTMENTS_PAGE)
  }
  if (url.pathname === '/api/v1/courses/') {
    return json(COURSES_PAGE)
  }
  if (url.pathname === '/api/v1/course-offerings/') {
    return json(OFFERINGS_PAGE)
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
    const dialog = screen.getByRole('dialog', { name: 'افزودن کاربر' })

    // Invalid email is rejected client-side with a Persian message.
    fireEvent.change(within(dialog).getByLabelText(/ایمیل/), {
      target: { value: 'not-an-email' },
    })
    fireEvent.change(within(dialog).getByLabelText(/گذرواژه/), {
      target: { value: 'Str0ng-Pass!' },
    })
    fireEvent.submit(within(dialog).getByRole('button', { name: 'ذخیره' }).closest('form')!)
    expect(await screen.findByText('ایمیل معتبر وارد کنید.')).toBeTruthy()

    fireEvent.change(within(dialog).getByLabelText(/ایمیل/), {
      target: { value: 'new@semnan.local' },
    })
    // A professor account: no student section on the wire.
    fireEvent.change(within(dialog).getByLabelText(/^نقش/), {
      target: { value: 'PROFESSOR' },
    })
    fireEvent.submit(within(dialog).getByRole('button', { name: 'ذخیره' }).closest('form')!)

    await waitFor(() => {
      const post = requested.find(
        (entry) => entry.url === '/api/v1/admin/users/' && entry.method === 'POST',
      )
      expect(post).toBeTruthy()
      const payload = JSON.parse(post!.body!)
      expect(payload).toMatchObject({
        email: 'new@semnan.local',
        role: 'PROFESSOR',
      })
      expect(payload.passed_course_codes).toBeUndefined()
      expect(payload.current_offering_ids).toBeUndefined()
    })
  })

  it('keeps the student academic section hidden until the student role is picked', async () => {
    renderPage()
    await screen.findByText('student@semnan.local')

    fireEvent.click(screen.getByRole('button', { name: 'افزودن' }))
    const dialog = await screen.findByRole('dialog', { name: 'افزودن کاربر' })

    // Before a role is selected: only the basic user fields.
    expect(within(dialog).queryByText('اطلاعات تحصیلی دانشجو')).toBeNull()

    // Selecting دانشجو reveals the section.
    fireEvent.change(within(dialog).getByLabelText(/^نقش/), { target: { value: 'STUDENT' } })
    expect(within(dialog).getByText('اطلاعات تحصیلی دانشجو')).toBeTruthy()

    // Switching to ADMIN hides it again.
    fireEvent.change(within(dialog).getByLabelText(/^نقش/), { target: { value: 'ADMIN' } })
    expect(within(dialog).queryByText('اطلاعات تحصیلی دانشجو')).toBeNull()

    fireEvent.change(within(dialog).getByLabelText(/^نقش/), { target: { value: 'STUDENT' } })
    expect(within(dialog).getByText('اطلاعات تحصیلی دانشجو')).toBeTruthy()
  })

  it('creates a student with academic data and course selections', async () => {
    renderPage()
    await screen.findByText('student@semnan.local')

    fireEvent.click(screen.getByRole('button', { name: 'افزودن' }))
    const dialog = await screen.findByRole('dialog', { name: 'افزودن کاربر' })

    fireEvent.change(within(dialog).getByLabelText(/ایمیل/), {
      target: { value: 'new-student@semnan.local' },
    })
    fireEvent.change(within(dialog).getByLabelText(/گذرواژه/), {
      target: { value: 'Str0ng-Pass!' },
    })
    fireEvent.change(within(dialog).getByLabelText(/^نقش/), { target: { value: 'STUDENT' } })

    // The section appears; options stay locked until a department is picked.
    expect(within(dialog).getByText('اطلاعات تحصیلی دانشجو')).toBeTruthy()
    expect(within(dialog).getAllByText('ابتدا رشته تحصیلی را انتخاب کنید.').length).toBeGreaterThan(0)

    const departmentSelect = within(dialog).getByLabelText(/رشته تحصیلی/) as HTMLSelectElement
    // The catalog options arrive async — wait for the department row, since a
    // change against an option-less select is ignored by jsdom.
    await waitFor(() => {
      expect(Array.from(departmentSelect.options).some((option) => option.value === '5')).toBe(true)
    })
    fireEvent.change(departmentSelect, { target: { value: '5' } })
    fireEvent.change(within(dialog).getByLabelText(/کد دانشجویی/), {
      target: { value: '40412345' },
    })
    fireEvent.change(within(dialog).getByLabelText(/سال ورود/), {
      target: { value: '۱۴۰۲' },
    })
    fireEvent.change(within(dialog).getByLabelText(/مقطع تحصیلی/), {
      target: { value: 'BACHELOR' },
    })

    // Courses and offerings load scoped to the department on the wire.
    await waitFor(() => {
      expect(
        requested.some(
          (entry) => entry.url === '/api/v1/courses/' && entry.query.includes('department=5'),
        ),
      ).toBe(true)
      expect(
        requested.some(
          (entry) =>
            entry.url === '/api/v1/course-offerings/' &&
            entry.query.includes('term=current') &&
            entry.query.includes('department=5'),
        ),
      ).toBe(true)
    })

    // Select a passed course and a current-term offering; the same course can
    // appear in both lists, so queries are scoped per multiselect testId.
    fireEvent.click(
      await within(within(dialog).getByTestId('passed-courses')).findByRole('checkbox', {
        name: /1916002 — ریاضیات عمومی/,
      }),
    )
    fireEvent.click(
      await within(within(dialog).getByTestId('current-courses')).findByRole('checkbox', {
        name: /1916008 — نظریه زبان‌ها و ماشین‌ها/,
      }),
    )

    fireEvent.submit(within(dialog).getByRole('button', { name: 'ذخیره' }).closest('form')!)

    await waitFor(() => {
      const post = requested.find(
        (entry) => entry.url === '/api/v1/admin/users/' && entry.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(post!.body!)).toMatchObject({
        email: 'new-student@semnan.local',
        role: 'STUDENT',
        student_number: '40412345',
        department_id: 5,
        degree_level: 'BACHELOR',
        entry_year: '1402',
        passed_course_codes: ['1916002'],
        current_offering_ids: [22],
      })
    })
  })

  it('removes a course from the current-term options once it is marked passed', async () => {
    renderPage()
    await screen.findByText('student@semnan.local')

    fireEvent.click(screen.getByRole('button', { name: 'افزودن' }))
    const dialog = await screen.findByRole('dialog', { name: 'افزودن کاربر' })

    fireEvent.change(within(dialog).getByLabelText(/^نقش/), { target: { value: 'STUDENT' } })
    const departmentSelect = within(dialog).getByLabelText(/رشته تحصیلی/) as HTMLSelectElement
    await waitFor(() => {
      expect(Array.from(departmentSelect.options).some((option) => option.value === '5')).toBe(true)
    })
    fireEvent.change(departmentSelect, { target: { value: '5' } })

    const passedBox = within(dialog).getByTestId('passed-courses')
    const currentBox = within(dialog).getByTestId('current-courses')

    // Both lists initially offer 1916002 (catalog row + current offering).
    await within(currentBox).findByRole('checkbox', { name: /1916002 — ریاضیات عمومی/ })
    expect(
      within(passedBox).getByRole('checkbox', { name: /1916002 — ریاضیات عمومی/ }),
    ).toBeTruthy()

    // Marking it passed removes it from the current-term options immediately.
    fireEvent.click(
      within(passedBox).getByRole('checkbox', { name: /1916002 — ریاضیات عمومی/ }),
    )
    await waitFor(() => {
      expect(
        within(currentBox).queryByRole('checkbox', { name: /1916002 — ریاضیات عمومی/ }),
      ).toBeNull()
    })
    // …and it stays selected in the passed list.
    expect(
      (within(passedBox).getByRole('checkbox', { name: /1916002 — ریاضیات عمومی/ }) as HTMLInputElement)
        .checked,
    ).toBe(true)
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
