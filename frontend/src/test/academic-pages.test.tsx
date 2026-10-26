// @vitest-environment jsdom
/**
 * Phase 06 page-level journeys (docs/08 §3: browse → detail, exams, calendar).
 *
 * The pages are rendered with the real providers (Router + QueryClient +
 * AuthProvider) and a stubbed `fetch`, so the test asserts what the user sees
 * *and* which documented query parameters the UI sends. No fixture is ever
 * imported by production code — these JSON bodies only stand in for Django in
 * the test process.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { CalendarPage } from '../features/calendar/CalendarPage'
import { CourseDetailPage, CoursesPage } from '../features/courses'
import { ExamsPage } from '../features/exams/ExamsPage'
import { ProfessorDetailPage, ProfessorsPage } from '../features/professors'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function page<T>(results: T[], count = results.length) {
  return { count, next: null, previous: null, results }
}

const TERM = {
  id: 1,
  name: 'نیمسال اول ۱۴۰۵-۱۴۰۶',
  academic_year: '1405-1406',
  semester_type: 'FIRST',
  starts_at: '2026-03-21',
  ends_at: '2027-01-09',
  is_current: true,
}

const DEPARTMENT = {
  id: 7,
  faculty: { id: 1, name: 'دانشکده مهندسی', code: 'F-CE' },
  name: 'گروه مهندسی کامپیوتر',
  code: '16',
}

const COURSE = {
  id: 11,
  code: '1916003',
  title: 'ساختمان داده',
  credits: 3,
  course_type: 'تخصصی الزامی',
  active: true,
  department: DEPARTMENT,
  prerequisites: [{ id: 12, code: '1916001', title: 'مبانی برنامه‌سازی', credits: 3 }],
}

const OFFERING = {
  id: 101,
  course: { id: 11, code: '1916003', title: 'ساختمان داده', credits: 3, course_type: '' },
  term: TERM,
  professor: {
    id: 21,
    first_name: 'کامران',
    last_name: 'محمدی',
    full_name: 'کامران محمدی',
    academic_title: 'دانشیار',
  },
  section_code: '01',
  capacity: 40,
  status: 'OPEN',
  enrolled_count: 12,
  schedules: [
    {
      id: 1,
      weekday: 6,
      weekday_display: 'شنبه',
      start_time: '08:00:00',
      end_time: '10:00:00',
      classroom: 'کلاس ۱۰۱',
    },
  ],
  exam: {
    id: 5,
    starts_at: '2026-11-05T08:00:00Z',
    ends_at: '2026-11-05T10:00:00Z',
    classroom: 'تالار ۱',
    status: 'SCHEDULED',
    last_updated_at: '2026-10-01T00:00:00Z',
    created_at: '2026-10-01T00:00:00Z',
  },
}

const PROFESSOR = {
  id: 21,
  department: DEPARTMENT,
  first_name: 'کامران',
  last_name: 'محمدی',
  academic_title: 'دانشیار',
  email: 'k.mohammadi@semnan.local',
  office: 'اتاق ۳۰۵',
  website: null,
  bio: 'عضو هیئت علمی گروه مهندسی کامپیوتر.',
  is_active: true,
}

let fetchMock: ReturnType<typeof vi.fn>
let requestedUrls: string[]

function respond(input: RequestInfo | URL): Response {
  const url = new URL(String(input), 'http://localhost')
  requestedUrls.push(url.pathname + url.search)
  const path = url.pathname

  if (path === '/api/v1/auth/refresh/') {
    // No cookie in the test environment → anonymous boot, pages still render.
    return json({ error: { code: 'AUTHENTICATION_REQUIRED', message: '', details: {} } }, 401)
  }
  if (path === '/api/v1/terms/') {
    return json(page([TERM]))
  }
  if (path === '/api/v1/departments/') {
    return json(page([DEPARTMENT]))
  }
  if (path === '/api/v1/courses/') {
    return json(page([COURSE]))
  }
  if (path === '/api/v1/courses/11/') {
    return json(COURSE)
  }
  if (path === '/api/v1/course-offerings/') {
    return json(page([OFFERING]))
  }
  if (path === '/api/v1/professors/') {
    return json(page([PROFESSOR]))
  }
  if (path === '/api/v1/professors/21/') {
    return json(PROFESSOR)
  }
  if (path === '/api/v1/exams/') {
    return json(
      page([
        {
          id: 5,
          course_offering: {
            id: 101,
            course_code: '1916003',
            course_title: 'ساختمان داده',
            section_code: '01',
            term: TERM,
          },
          starts_at: '2026-11-05T08:00:00Z',
          ends_at: '2026-11-05T10:00:00Z',
          classroom: 'تالار ۱',
          status: 'SCHEDULED',
          last_updated_at: '2026-10-01T00:00:00Z',
          created_at: '2026-10-01T00:00:00Z',
        },
      ]),
    )
  }
  if (path === '/api/v1/calendar/events/') {
    return json(
      page([
        {
          id: 3,
          term: TERM,
          title: 'بازه انتخاب واحد',
          event_type: 'REGISTRATION',
          starts_at: '2026-09-01T00:00:00Z',
          ends_at: '2026-09-10T00:00:00Z',
          description: 'انتخاب واحد در سامانه گلستان انجام می‌شود.',
          is_published: true,
        },
      ]),
    )
  }
  if (path === '/api/v1/announcements/') {
    return json(page([]))
  }
  return json({ error: { code: 'NOT_FOUND', message: '', details: {} } }, 404)
}

function renderApp(initialPath: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/courses" element={<CoursesPage />} />
            <Route path="/courses/:id" element={<CourseDetailPage />} />
            <Route path="/professors" element={<ProfessorsPage />} />
            <Route path="/professors/:id" element={<ProfessorDetailPage />} />
            <Route path="/exams" element={<ExamsPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestedUrls = []
  fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(respond(input)))
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('course catalog journey', () => {
  it('browses the list and opens a course with its term-scoped offerings', async () => {
    renderApp('/courses')

    const title = await screen.findByText('ساختمان داده')
    expect(screen.getByText(/1916003/)).toBeTruthy()

    fireEvent.click(title.closest('a')!)

    // Detail page: prerequisites are links to their own course page.
    expect(await screen.findByRole('heading', { name: 'ساختمان داده' })).toBeTruthy()
    expect(await screen.findByText('مبانی برنامه‌سازی')).toBeTruthy()

    // The offering row carries term context and the Jalali exam date.
    expect(await screen.findByText('نیمسال اول ۱۴۰۵-۱۴۰۶')).toBeTruthy()
    expect(screen.getByText('کامران محمدی')).toBeTruthy()

    await waitFor(() =>
      expect(
        requestedUrls.some((url) => url.startsWith('/api/v1/course-offerings/?course=11')),
      ).toBe(true),
    )
  })

  it('sends the documented filters from the URL', async () => {
    renderApp('/courses?search=%D8%AF%D8%A7%D8%AF%D9%87&credits=3&course_type=%D8%AA%D8%AE%D8%B5%D8%B5%DB%8C')

    await screen.findByText('ساختمان داده')

    const request = requestedUrls.find((url) => url.startsWith('/api/v1/courses/'))
    expect(request).toContain('search=')
    expect(request).toContain('credits=3')
    expect(request).toContain('course_type=')
  })
})

describe('professor journey', () => {
  it('opens a professor profile with current-term offerings', async () => {
    renderApp('/professors')

    fireEvent.click((await screen.findByText('دانشیار کامران محمدی')).closest('a')!)

    expect(await screen.findByRole('heading', { name: 'دانشیار کامران محمدی' })).toBeTruthy()
    expect(await screen.findByText('k.mohammadi@semnan.local')).toBeTruthy()
    // Current-term offering + weekly schedule from the offering's schedules.
    expect(await screen.findByText(/نیمسال اول ۱۴۰۵-۱۴۰۶/)).toBeTruthy()
    expect(screen.getByText(/شنبه ۰۸:۰۰–۱۰:۰۰/)).toBeTruthy()

    await waitFor(() =>
      expect(
        requestedUrls.some(
          (url) => url.includes('/course-offerings/') && url.includes('professor=21'),
        ),
      ).toBe(true),
    )
  })
})

describe('exams page', () => {
  it('shows exam rows with term context and requests the current term', async () => {
    renderApp('/exams')

    expect(await screen.findByText('ساختمان داده')).toBeTruthy()
    expect(screen.getByText(/نیمسال اول ۱۴۰۵-۱۴۰۶/)).toBeTruthy()
    expect(screen.getByText(/زمان‌بندی‌شده/)).toBeTruthy()

    const request = requestedUrls.find((url) => url.startsWith('/api/v1/exams/'))
    expect(request).toContain('term=current')
    expect(request).toContain('page_size=25')
  })
})

describe('calendar page', () => {
  it('shows events with their term and requests the current term', async () => {
    renderApp('/calendar')

    expect(await screen.findByText('بازه انتخاب واحد')).toBeTruthy()
    expect(screen.getByText(/نیمسال اول ۱۴۰۵-۱۴۰۶/)).toBeTruthy()
    expect(screen.getAllByText(/ثبت‌نام/).length).toBeGreaterThan(0)

    const request = requestedUrls.find((url) => url.startsWith('/api/v1/calendar/events/'))
    expect(request).toContain('term=current')
  })
})
