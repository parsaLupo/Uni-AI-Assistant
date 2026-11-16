// @vitest-environment jsdom
/**
 * Admin form focus & date round-trip regression (jsdom).
 *
 * Focus contract: the shared Modal must move focus into the dialog exactly
 * once when it opens. Its open/close effects may not depend on the inline
 * `onClose` callback — a new function identity per parent render made the
 * effect re-run on every keystroke and steal focus from the controlled
 * inputs (the "one character per click" bug across all admin modals).
 *
 * Date contract: the announcement editor shows a stored UTC instant as the
 * viewer-local `datetime-local` value, and submitting preserves the exact
 * instant — editing only the title must not shift `published_at` by the
 * viewer's UTC offset.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { Modal } from '../components/ui'
import { AdminAnnouncementsPage } from '../features/admin'
import { AuthProvider } from '../features/auth/AuthProvider'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** A modal whose parent re-renders on every keystroke, like the real pages. */
function ReRenderingModal() {
  const [text, setText] = useState('')
  return (
    <Modal open onClose={() => setText(text)} title="تست مودال">
      <input
        aria-label="فیلد تست"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
    </Modal>
  )
}

describe('Modal focus stability', () => {
  it('keeps focus in the input across keystrokes even though onClose changes identity', () => {
    render(<ReRenderingModal />)
    const input = screen.getByLabelText('فیلد تست') as HTMLInputElement

    input.focus()
    // Type several characters; every change re-renders the parent and
    // recreates the inline onClose arrow.
    for (const character of ['الف', 'ب', 'ج']) {
      fireEvent.change(input, { target: { value: input.value + character } })
      expect(document.activeElement).toBe(input)
    }
    expect(input.value).toBe('الفبج')

    // The dialog surface is not the focus owner while the user types.
    const surface = document.querySelector('[role="dialog"] > div[class*="relative"]') as HTMLElement
    expect(surface).toBeTruthy()
    expect(document.activeElement).not.toBe(surface)
  })

  it('moves focus into the dialog exactly once when it opens', () => {
    function Openable() {
      const [open, setOpen] = useState(false)
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            باز کن
          </button>
          <Modal open={open} onClose={() => setOpen(false)} title="تست">
            <input aria-label="داخل" />
          </Modal>
        </>
      )
    }
    render(<Openable />)
    fireEvent.click(screen.getByText('باز کن'))
    const inside = screen.getByLabelText('داخل')
    expect(document.activeElement).toBe(inside.closest('[role="dialog"]')?.querySelector('[tabindex="-1"]') ?? document.body)
    expect(document.activeElement).not.toBe(inside)
  })
})

/* ── Announcement datetime round-trip ──────────────────────────────────── */

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

const ROW = {
  id: 5,
  term: null,
  audience_faculty: null,
  audience_department: null,
  title: 'اعلامیه آزمایشی',
  body: 'متن',
  priority: 'NORMAL',
  published_at: '2026-11-15T09:33:00Z',
  expires_at: '2026-11-15T18:03:00Z',
  is_published: true,
}

const calls: Array<{ method: string; path: string; body: unknown }> = []

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const url = new URL(String(input), 'http://localhost')
  const method = init?.method ?? 'GET'
  calls.push({ method, path: url.pathname, body: init?.body ? JSON.parse(String(init.body)) : null })
  if (url.pathname === '/api/v1/auth/refresh/') {
    return json({ access: 'token', user: { id: 3, email: 'a@x.com', role: 'ADMIN' } })
  }
  if (url.pathname === '/api/v1/auth/me/') {
    return json({ id: 3, email: 'a@x.com', role: 'ADMIN', first_name: 'م', last_name: 'د', is_active: true })
  }
  if (url.pathname.endsWith('/admin/announcements/') && method === 'GET') {
    return json({ count: 1, next: null, previous: null, results: [ROW] })
  }
  if (url.pathname.endsWith('/admin/announcements/5/') && method === 'PATCH') {
    return json({ ...ROW, ...(typeof init?.body === 'string' ? JSON.parse(init.body) : {}) })
  }
  if (url.pathname.includes('/terms/')) return json({ count: 0, next: null, previous: null, results: [] })
  if (url.pathname.includes('faculties') || url.pathname.includes('departments')) {
    return json({ count: 0, next: null, previous: null, results: [] })
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={['/admin/announcements']}>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <AdminAnnouncementsPage />
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  calls.length = 0
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) =>
    Promise.resolve(respond(input, init)),
  ))
})

describe('Announcement editor — date round trip', () => {
  it('shows the stored UTC instant as local wall time and re-submits the same instant', async () => {
    renderPage()
    // Open edit for the seeded row.
    const editButton = await screen.findByRole('button', { name: 'ویرایش' })
    fireEvent.click(editButton)

    const published = await screen.findByDisplayValue(utcOf('2026-11-15T09:33:00Z')) as HTMLInputElement
    const expires = screen.getByDisplayValue(utcOf('2026-11-15T18:03:00Z')) as HTMLInputElement

    // Editing only the title (keystrokes) must not touch the dates.
    const title = screen.getByLabelText('عنوان') as HTMLInputElement
    fireEvent.change(title, { target: { value: ROW.title + ' دوم' } })
    expect(published.value).toBe(utcOf('2026-11-15T09:33:00Z'))
    expect(expires.value).toBe(utcOf('2026-11-15T18:03:00Z'))

    fireEvent.click(screen.getByRole('button', { name: 'ذخیره' }))

    const patch = await waitFor(() => {
      const found = calls.find((call) => call.method === 'PATCH' && call.path.endsWith('/announcements/5/'))
      expect(found).toBeTruthy()
      return found!
    })
    const patchBody = patch.body as Record<string, unknown>
    // The exact instant survives the round trip (no UTC-as-local slicing).
    // toISOString emits milliseconds, so compare the instants themselves.
    expect(new Date(patchBody.published_at as string).getTime()).toBe(new Date(ROW.published_at).getTime())
    expect(new Date(patchBody.expires_at as string).getTime()).toBe(new Date(ROW.expires_at).getTime())
    expect(patchBody).toMatchObject({ title: 'اعلامیه آزمایشی دوم' })
  })
})

/** Local datetime-local rendering used as the expected input value. */
function utcOf(iso: string): string {
  const date = new Date(iso)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
