// @vitest-environment jsdom
/**
 * /profile — academic fields render read-only (registrar-owned; direct PATCHes
 * are rejected server-side, so the UI shows facts, not inputs) and the only
 * self-service edit is the password change, POSTed to
 * /auth/password-change/ with the current + new password.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { ProfilePage } from '../features/profile'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const ME = {
  id: 7,
  email: '40212126016@semnan.local',
  role: 'STUDENT',
  first_name: 'پارسا',
  last_name: 'رفیعی اصل',
}

const PROFILE = {
  id: 3,
  user: ME,
  student_number: '40212126016',
  department: { id: 5, name: 'مهندسی کامپیوتر', code: '16' },
  faculty: { id: 1, name: 'دانشکده مهندسی', code: 'F-CE' },
  degree_level: 'BACHELOR',
  entry_year: '1402',
  current_term_number: 5,
  current_gpa: '17.66',
  onboarding_complete: true,
}

let fetchMock: ReturnType<typeof vi.fn>
const requested: Array<{ url: string; method: string; body: string | null }> = []

function respond(input: RequestInfo | URL, init: RequestInit | undefined): Response {
  const path = new URL(String(input), 'http://localhost').pathname
  if (path === '/api/v1/auth/refresh/') {
    // Silent boot refresh: hand back a student session.
    return json({ access: 'test-access', refresh: 'test-refresh', user: ME })
  }
  if (path === '/api/v1/auth/me/') {
    return json(ME)
  }
  if (path === '/api/v1/students/me/') {
    return json(PROFILE)
  }
  if (path === '/api/v1/auth/password-change/' && init?.method === 'POST') {
    return json({ detail: 'گذرواژه با موفقیت تغییر کرد.' })
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
        <MemoryRouter initialEntries={['/profile']}>
          <ProfilePage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requested.length = 0
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit | undefined) => {
    requested.push({
      url: new URL(String(input), 'http://localhost').pathname,
      method: init?.method ?? 'GET',
      body: typeof init?.body === 'string' ? init.body : null,
    })
    return Promise.resolve(respond(input, init))
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('profile page', () => {
  it('renders the academic facts read-only with no editable inputs', async () => {
    renderPage()

    // Academic identity comes from the profile endpoint.
    await screen.findByText('۴۰۲۱۲۱۲۶۰۱۶')
    expect(screen.getByText('مهندسی کامپیوتر')).toBeTruthy()
    expect(screen.getByText('دانشکده مهندسی')).toBeTruthy()
    expect(screen.getByText('کارشناسی')).toBeTruthy()
    // Entry year / GPA are shown with Persian digits; GPA survives the widened
    // decimal field ("17.66").
    expect(screen.getByText('۱۴۰۲')).toBeTruthy()
    expect(screen.getByText('۱۷.۶۶')).toBeTruthy()

    // Nothing academic is editable: no inputs/selects labelled with the
    // academic fields, and no text input holding the student number.
    expect(screen.queryByLabelText(/کد دانشجویی/)).toBeNull()
    expect(screen.queryByLabelText(/رشته تحصیلی/)).toBeNull()
    expect(screen.queryByLabelText(/مقطع/)).toBeNull()
    expect(screen.queryByLabelText(/سال ورود/)).toBeNull()
    expect(screen.queryByDisplayValue('40212126016')).toBeNull()
    // No ویرایش/ذخیره buttons from the old editable form.
    expect(screen.queryByRole('button', { name: 'ویرایش مشخصات' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'ذخیره تغییرات' })).toBeNull()
    // No PATCH is ever sent by the page.
    expect(
      requested.some((entry) => entry.url === '/api/v1/students/me/' && entry.method !== 'GET'),
    ).toBe(false)
  })

  it('submits a password change with the current and new password', async () => {
    renderPage()
    await screen.findByText('۴۰۲۱۲۱۲۶۰۱۶')

    fireEvent.change(screen.getByLabelText('گذرواژهٔ فعلی'), {
      target: { value: 'Old-Passw0rd!' },
    })
    fireEvent.change(screen.getByLabelText('گذرواژه جدید'), {
      target: { value: 'Br4nd-New-Pass!' },
    })
    fireEvent.change(screen.getByLabelText('تکرار گذرواژه جدید'), {
      target: { value: 'Br4nd-New-Pass!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'تغییر گذرواژه' }))

    await waitFor(() => {
      const post = requested.find(
        (entry) => entry.url === '/api/v1/auth/password-change/' && entry.method === 'POST',
      )
      expect(post).toBeTruthy()
      expect(JSON.parse(post!.body!)).toEqual({
        old_password: 'Old-Passw0rd!',
        new_password: 'Br4nd-New-Pass!',
      })
    })
    expect(await screen.findByText('گذرواژه با موفقیت تغییر کرد.')).toBeTruthy()
    // The form clears after a successful change.
    expect((screen.getByLabelText('گذرواژهٔ فعلی') as HTMLInputElement).value).toBe('')
  })

  it('rejects a mismatched confirmation client-side without any request', async () => {
    renderPage()
    await screen.findByText('۴۰۲۱۲۱۲۶۰۱۶')

    fireEvent.change(screen.getByLabelText('گذرواژهٔ فعلی'), {
      target: { value: 'Old-Passw0rd!' },
    })
    fireEvent.change(screen.getByLabelText('گذرواژه جدید'), {
      target: { value: 'Br4nd-New-Pass!' },
    })
    fireEvent.change(screen.getByLabelText('تکرار گذرواژه جدید'), {
      target: { value: 'Different-Pass!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'تغییر گذرواژه' }))

    expect(screen.getByText('تکرار گذرواژه با گذرواژه جدید یکسان نیست.')).toBeTruthy()
    // Too-short new password is caught as well. The mismatch error rendered
    // inside the confirm label, so that query matches with a regex instead of
    // exact text; the new-password label itself has no error text yet.
    fireEvent.change(screen.getByLabelText('گذرواژه جدید'), { target: { value: '123' } })
    fireEvent.change(screen.getByLabelText(/تکرار گذرواژه جدید/), { target: { value: '123' } })
    fireEvent.click(screen.getByRole('button', { name: 'تغییر گذرواژه' }))
    expect(screen.getByText('گذرواژه حداقل ۸ نویسه است.')).toBeTruthy()
    expect(
      requested.some((entry) => entry.url === '/api/v1/auth/password-change/'),
    ).toBe(false)
  })

  it('keeps three password fields only — the academic section is a definition list', async () => {
    renderPage()
    await screen.findByText('۴۰۲۱۲۱۲۶۰۱۶')

    // The academic section is a definition list, not a form: the only inputs
    // on the page are the three password fields (which carry no textbox role).
    const main = document.querySelector('main') ?? document.body
    const inputs = Array.from((main as HTMLElement).querySelectorAll('input'))
    expect(inputs).toHaveLength(3)
    for (const input of inputs) {
      expect((input as HTMLInputElement).type).toBe('password')
    }
    // No dropdowns: degree level is text, not a select.
    expect((main as HTMLElement).querySelectorAll('select')).toHaveLength(0)
  })
})
