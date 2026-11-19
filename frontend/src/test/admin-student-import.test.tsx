// @vitest-environment jsdom
/**
 * Bulk student import wizard: choose a workbook, keep the suggested mapping,
 * preview/validate, switch to upsert (re-validates), confirm, and read the
 * one-time generated passwords. `fetch` is stubbed — no fixture is imported by
 * production code.
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

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] }

const INSPECTION = {
  file_hash: 'a'.repeat(64),
  sheets: [
    {
      name: 'Students',
      row_count: 1,
      headers: [
        'student_id',
        'first_name',
        'last_name',
        'email',
        'department',
        'degree',
        'entry_year',
        'current_term',
        'gpa',
      ],
      suggested_role: 'students',
      suggested_mapping: {
        student_id: 'student_id',
        first_name: 'first_name',
        last_name: 'last_name',
        email: 'email',
        department: 'department',
        degree: 'degree',
        entry_year: 'entry_year',
        current_term: 'current_term',
        gpa: 'gpa',
      },
      sample_rows: [['40211234', 'سارا', 'محمدی', 'sara@example.edu', 'COMP', 'کارشناسی', '1402', '3', '17.66']],
    },
    {
      name: 'PassedCourses',
      row_count: 1,
      headers: ['student_id', 'course_code', 'grade', 'term'],
      suggested_role: 'passed_courses',
      suggested_mapping: {
        student_id: 'student_id',
        course_code: 'course_code',
        grade: 'grade',
        term: 'term',
      },
      sample_rows: [['40211234', 'CS101', '18', 'نیمسال اول 1404-1405']],
    },
  ],
}

const PREVIEW = {
  file_hash: 'a'.repeat(64),
  mode: 'create_only',
  summary: {
    students_total: 1,
    students_valid: 1,
    students_invalid: 0,
    students_existing: 0,
    will_create: 1,
    will_update: 0,
    will_skip: 0,
    passed_total: 1,
    passed_valid: 1,
    passed_invalid: 0,
    enrollments_total: 0,
    enrollments_valid: 0,
    enrollments_invalid: 0,
    duplicate_rows: 0,
    error_count: 0,
    warning_count: 0,
  },
  students: [
    {
      row: 2,
      student_id: '40211234',
      email: 'sara@example.edu',
      full_name: 'سارا محمدی',
      department: 'مهندسی کامپیوتر',
      degree: 'کارشناسی',
      entry_year: '1402',
      current_term: 3,
      gpa: '17.66',
      outcome: 'create',
      changes: [],
      errors: [],
      warnings: [],
    },
  ],
  passed_courses: [],
  enrollments: [],
  errors: [],
  warnings: [],
  detail_limit: 200,
  details_truncated: false,
}

const RESULT = {
  file_hash: 'a'.repeat(64),
  mode: 'create_only',
  summary: {
    students_processed: 1,
    created: 1,
    updated: 0,
    skipped: 0,
    failed: 0,
    passed_imported: 1,
    enrollments_imported: 0,
    errors: 0,
    warnings: 0,
  },
  results: [
    {
      row: 2,
      student_id: '40211234',
      email: 'sara@example.edu',
      full_name: 'سارا محمدی',
      outcome: 'created',
      passed_imported: 1,
      enrollments_imported: 0,
      warnings: [],
    },
  ],
  errors: [],
  created_credentials: [{ email: 'sara@example.edu', password: 'Un1que-Temp-Pass!' }],
  audit_id: 77,
}

let fetchMock: ReturnType<typeof vi.fn>

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost')
  if (url.pathname === '/api/v1/auth/refresh/') {
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (url.pathname === '/api/v1/admin/users/') {
    return json(EMPTY_PAGE)
  }
  if (url.pathname === '/api/v1/admin/students/import/reports/') {
    return json(EMPTY_PAGE)
  }
  if (url.pathname === '/api/v1/admin/students/import/template/') {
    return new Response(new Blob(['xlsx-bytes']), {
      status: 200,
      headers: { 'content-type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
    })
  }
  if (url.pathname === '/api/v1/admin/students/import/inspect/' && init?.method === 'POST') {
    return json(INSPECTION)
  }
  if (url.pathname === '/api/v1/admin/students/import/validate/' && init?.method === 'POST') {
    return json(PREVIEW)
  }
  if (url.pathname === '/api/v1/admin/students/import/confirm/' && init?.method === 'POST') {
    return json(RESULT)
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
        <MemoryRouter initialEntries={['/admin/users']}>
          <AdminUsersPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

function formField(call: unknown[], key: string): string | null {
  const init = call[1] as RequestInit | undefined
  const body = init?.body
  return body instanceof FormData ? (body.get(key) as string | null) : null
}

function callsTo(path: string) {
  return fetchMock.mock.calls.filter((call) => {
    const url = new URL(String(call[0]), 'http://localhost')
    return url.pathname === path
  })
}

beforeEach(() => {
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) =>
    Promise.resolve(respond(input, init)),
  )
  vi.stubGlobal('fetch', fetchMock)
  // jsdom has no object-URL implementation; the template download uses one.
  Object.assign(URL, {
    createObjectURL: vi.fn(() => 'blob:mock'),
    revokeObjectURL: vi.fn(),
  })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('student import wizard', () => {
  it('downloads the template from the admin endpoint', async () => {
    renderPage()
    fireEvent.click(await screen.findByTestId('open-student-import'))

    const dialog = await screen.findByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: /دانلود قالب اکسل/ }))

    await waitFor(() => expect(callsTo('/api/v1/admin/students/import/template/')).toHaveLength(1))
  })

  it('maps, previews, re-validates in upsert mode, and confirms the import', async () => {
    renderPage()
    fireEvent.click(await screen.findByTestId('open-student-import'))
    const dialog = await screen.findByRole('dialog')

    const file = new File(['PK test'], 'roster.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    fireEvent.change(within(dialog).getByTestId('student-import-file-input'), {
      target: { files: [file] },
    })

    // Inspection ran and the suggested role/columns are visible (not applied silently).
    expect(await within(dialog).findByText(/برگهٔ «Students»/)).toBeTruthy()
    const roleSelect = within(dialog).getByTestId('import-role-Students') as HTMLSelectElement
    expect(roleSelect.value).toBe('students')
    const emailColumn = within(dialog).getByTestId('import-column-Students-email') as HTMLSelectElement
    expect(emailColumn.value).toBe('email')

    fireEvent.click(within(dialog).getByRole('button', { name: /بررسی و پیش‌نمایش/ }))

    expect(await within(dialog).findByText('خلاصهٔ بررسی')).toBeTruthy()
    expect(within(dialog).getByText('40211234')).toBeTruthy()

    const validateCall = callsTo('/api/v1/admin/students/import/validate/')[0]
    const mapping = JSON.parse(formField(validateCall, 'mapping') ?? '{}')
    expect(mapping.sheets.map((sheet: { role: string }) => sheet.role)).toEqual([
      'students',
      'passed_courses',
    ])
    expect(formField(validateCall, 'mode')).toBe('create_only')

    // Switching to upsert re-validates before confirmation.
    fireEvent.click(within(dialog).getByRole('radio', { name: /به‌روزرسانی مشخصات/ }))
    await waitFor(() => expect(callsTo('/api/v1/admin/students/import/validate/')).toHaveLength(2))
    const secondValidate = callsTo('/api/v1/admin/students/import/validate/')[1]
    expect(formField(secondValidate, 'mode')).toBe('upsert')

    const confirmButton = within(dialog).getByRole('button', { name: /ثبت نهایی/ })
    expect(confirmButton.hasAttribute('disabled')).toBe(true)
    fireEvent.click(within(dialog).getByTestId('import-confirm-check'))
    expect(confirmButton.hasAttribute('disabled')).toBe(false)
    fireEvent.click(confirmButton)

    expect(await within(dialog).findByText('نتیجهٔ واردکردن')).toBeTruthy()
    expect(within(dialog).getByText('Un1que-Temp-Pass!')).toBeTruthy()
    const confirmCall = callsTo('/api/v1/admin/students/import/confirm/')[0]
    expect(formField(confirmCall, 'confirm')).toBe('true')
    expect(formField(confirmCall, 'expected_hash')).toBe('a'.repeat(64))
    expect(formField(confirmCall, 'mode')).toBe('upsert')
  })

  it('rejects a non-xlsx file without calling inspect', async () => {
    renderPage()
    fireEvent.click(await screen.findByTestId('open-student-import'))
    const dialog = await screen.findByRole('dialog')

    const file = new File(['csv'], 'roster.csv', { type: 'text/csv' })
    fireEvent.change(within(dialog).getByTestId('student-import-file-input'), {
      target: { files: [file] },
    })

    expect(await within(dialog).findByRole('alert')).toBeTruthy()
    expect(within(dialog).getByRole('alert').textContent).toContain('xlsx')
    expect(callsTo('/api/v1/admin/students/import/inspect/')).toHaveLength(0)
  })
})
