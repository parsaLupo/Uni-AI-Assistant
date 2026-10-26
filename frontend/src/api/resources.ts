/**
 * Typed resource calls for the Phase 04 endpoints.
 *
 * Every function goes through the shared `requestJson` client (single error
 * envelope → ApiError → Persian text), so features never touch `fetch`
 * directly (ADR-013). The in-memory access token from the auth session is
 * attached here; the refresh cookie rides along via `credentials: 'include'`.
 */

import { requestJson } from './client'
import { getAccessToken } from '../features/auth/session'
import type { Paginated } from '../types/api'
import type {
  AcademicEvent,
  AcademicTerm,
  Announcement,
  Course,
  CourseOffering,
  Department,
  Exam,
  Faculty,
  ListQuery,
  PlannerItem,
  Professor,
  StudentProfile,
} from '../types/academic'

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function get<T>(path: string, query?: ListQuery): Promise<T> {
  return requestJson<T>(path, { headers: authHeaders() }, query as Record<string, string | number | undefined>)
}

function send<T>(method: 'POST' | 'PATCH' | 'PUT', path: string, body: unknown): Promise<T> {
  return requestJson<T>(path, {
    method,
    body: JSON.stringify(body),
    headers: authHeaders(),
  })
}

/** Count-only helper: list endpoints accept page_size, `count` is always present. */
function countOf(resource: string, query?: ListQuery): Promise<number> {
  return get<Pick<Paginated<unknown>, 'count'>>(resource, {
    page: 1,
    page_size: 1,
    ...query,
  }).then((page) => page.count)
}

export const academicApi = {
  // ── Academic structure ────────────────────────────────────────────────
  terms: (query?: ListQuery) => get<Paginated<AcademicTerm>>('terms', query),
  /** Public active-department read (onboarding options + filters). */
  departments: (query?: ListQuery) => get<Paginated<Department>>('departments', query),
  adminDepartments: (query?: ListQuery) =>
    get<Paginated<Department>>('admin/departments', { page_size: 100, ...query }),
  adminFaculties: (query?: ListQuery) =>
    get<Paginated<Faculty>>('admin/faculties', { page_size: 100, ...query }),

  // ── Courses & offerings ───────────────────────────────────────────────
  courses: (query?: ListQuery) => get<Paginated<Course>>('courses', query),
  course: (id: number | string) => get<Course>(`courses/${id}`),
  offerings: (query?: ListQuery) => get<Paginated<CourseOffering>>('course-offerings', query),

  // ── Professors ────────────────────────────────────────────────────────
  professors: (query?: ListQuery) => get<Paginated<Professor>>('professors', query),
  professor: (id: number | string) => get<Professor>(`professors/${id}`),

  // ── Calendar / exams / announcements ──────────────────────────────────
  events: (query?: ListQuery) => get<Paginated<AcademicEvent>>('calendar/events', query),
  exams: (query?: ListQuery) => get<Paginated<Exam>>('exams', query),
  announcements: (query?: ListQuery) => get<Paginated<Announcement>>('announcements', query),

  // ── Student ───────────────────────────────────────────────────────────
  studentProfile: () => get<StudentProfile>('students/me'),
  updateStudentProfile: (patch: Partial<StudentProfile>) =>
    send<StudentProfile>('PATCH', 'students/me', patch),
  planner: (query?: ListQuery) => get<PlannerItem[]>('students/planner', query),

  // ── Admin live counts (Phase 05 overview; /admin/analytics is Phase 13) ──
  adminCount: (resource: string, query?: ListQuery) => countOf(resource, query),
}

export type AcademicApi = typeof academicApi
