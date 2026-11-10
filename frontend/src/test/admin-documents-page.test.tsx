// @vitest-environment jsdom
/**
 * Phase 13 — /admin/documents page journey: list from GET /admin/documents/,
 * multipart upload POST (FormData carries the PDF + metadata), and the
 * activate confirmation that POSTs `.../activate/` to supersede old versions.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { AdminDocumentsPage } from '../features/admin'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const DOCUMENTS_PAGE = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 11,
      title: 'آیین‌نامه آموزشی',
      document_type: 'REG',
      academic_year: '1405-1406',
      effective_from: '2024-06-20',
      effective_to: null,
      version: 2,
      status: 'INDEXED',
      processing_error: '',
      failure_stage: '',
      attempt_count: 1,
      uploaded_by: 3,
      created_at: '2026-10-01T08:00:00+03:30',
      updated_at: '2026-10-01T08:30:00+03:30',
    },
    {
      id: 12,
      title: 'راهنمای انتخاب واحد',
      document_type: 'GUIDE',
      academic_year: '1404-1405',
      effective_from: '2023-06-20',
      effective_to: null,
      version: 1,
      status: 'FAILED',
      processing_error: 'خطای پارس',
      failure_stage: 'parse',
      attempt_count: 2,
      uploaded_by: 3,
      created_at: '2025-10-01T08:00:00+03:30',
      updated_at: '2025-10-01T09:00:00+03:30',
    },
  ],
}

let fetchMock: ReturnType<typeof vi.fn>
const requested: Array<{ url: string; query: string; method: string; body: unknown }> = []

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost')
  if (url.pathname === '/api/v1/auth/refresh/') {
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (url.pathname === '/api/v1/admin/documents/' && (!init?.method || init.method === 'GET')) {
    return json(DOCUMENTS_PAGE)
  }
  if (url.pathname === '/api/v1/admin/documents/' && init?.method === 'POST') {
    return json(DOCUMENTS_PAGE.results[0], 202)
  }
  if (url.pathname === '/api/v1/admin/documents/11/activate/' && init?.method === 'POST') {
    return json({ ...DOCUMENTS_PAGE.results[0], status: 'ACTIVE' })
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
        <MemoryRouter initialEntries={['/admin/documents']}>
          <AdminDocumentsPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requested.length = 0
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
    const url = new URL(String(input), 'http://localhost')
    requested.push({
      url: url.pathname,
      query: url.search,
      method: init?.method ?? 'GET',
      body: init?.body ?? null,
    })
    return Promise.resolve(respond(input, init))
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('admin documents page', () => {
  it('renders document rows with lifecycle statuses', async () => {
    renderPage()

    expect(await screen.findByText('آیین‌نامه آموزشی')).toBeTruthy()
    expect(screen.getByText('راهنمای انتخاب واحد')).toBeTruthy()
    expect(screen.getAllByText('ایندکس شده').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ناموفق').length).toBeGreaterThan(0)
    expect(screen.getByText('خطای پارس')).toBeTruthy()
  })

  it('uploads a doc as multipart POST with the file and title', async () => {
    renderPage()
    await screen.findByText('آیین‌نامه آموزشی')

    fireEvent.click(screen.getByRole('button', { name: 'بارگذاری سند' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(screen.getByLabelText(/عنوان سند/), {
      target: { value: 'سند آزمون' },
    })
    const file = new File(['%PDF-1.4 test'], 'regulations.pdf', { type: 'application/pdf' })
    const fileInput = dialog.querySelector('input[type="file"]')!
    expect(fileInput).toBeTruthy()
    fireEvent.change(fileInput, { target: { files: [file] } })
    fireEvent.submit(screen.getByRole('button', { name: 'بارگذاری و پردازش' }).closest('form')!)

    await waitFor(() => {
      const post = requested.find(
        (entry) => entry.url === '/api/v1/admin/documents/' && entry.method === 'POST',
      )
      expect(post).toBeTruthy()
      const form = post!.body as FormData
      expect(form.get('title')).toBe('سند آزمون')
      expect((form.get('file') as File).name).toBe('regulations.pdf')
    })
  })

  it('activates an indexed document only after confirmation', async () => {
    renderPage()
    await screen.findByText('آیین‌نامه آموزشی')

    fireEvent.click(screen.getByRole('button', { name: 'فعال‌سازی' }))
    const dialog = await screen.findByRole('dialog', { name: 'فعال‌سازی' })
    const confirm = Array.from(dialog.querySelectorAll('button')).find(
      (button) => button.textContent === 'حذف',
    )!
    expect(
      requested.some(
        (entry) =>
          entry.url === '/api/v1/admin/documents/11/activate/' && entry.method === 'POST',
      ),
    ).toBe(false) // confirmation dialog, nothing sent yet
    fireEvent.click(confirm)

    await waitFor(() => {
      expect(
        requested.some(
          (entry) =>
            entry.url === '/api/v1/admin/documents/11/activate/' && entry.method === 'POST',
        ),
      ).toBe(true)
    })
  })
})
