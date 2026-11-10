/**
 * Phase 13 — admin API surface.
 *
 * `docs/api/admin.md` endpoints: analytics dashboard/audit-log (aggregate-only)
 * plus the management CRUD for users, courses (+prerequisites), offerings
 * (+schedules), exams, professors, terms, announcements and documents. Every
 * call goes through the shared `requestJson` client and carries the Bearer
 * token; Django `IsAdmin`/`IsSuperAdmin` remains the authority.
 */

import { requestJson } from './client'
import { getAccessToken } from '../features/auth/session'
import type { Paginated } from '../types/api'
import type { Announcement, AcademicTerm, Course, CourseOffering, ClassSchedule } from '../types/academic'
import type {
  AdminDocument,
  AdminDocumentsQuery,
  AdminUser,
  AdminUserCreatePayload,
  AdminUserUpdatePayload,
  AdminUsersQuery,
  AnnouncementQuery,
  CoursePrerequisiteEdge,
  OfferingsQuery,
} from '../types/admin'

export interface AdminDashboard {
  users: {
    active_users: number
    recently_active_users: number
    by_role: Array<{ role: string; count: number }>
  }
  questions: {
    total: number
    last_7_days: number
    answers: number
    insufficient_evidence: number
  }
  /** Routed execution-mode counts (the app's durable "topic" signal). */
  topic_distribution: Array<{ mode: string; count: number }>
  top_documents: Array<{
    id: number
    title: string
    document_type: string
    academic_year: string
    citation_count: number
  }>
  ai: {
    total_requests: number
    error_count: number
    avg_latency_ms: number | null
  }
  documents_total: number
  generated_at: string
}

export interface AuditLogRow {
  id: number
  created_at: string
  actor: number | null
  actor_email?: string
  action: string
  entity_type: string
  entity_id: string
  metadata: Record<string, unknown>
}

export interface AuditLogQuery {
  entity_type?: string
  action?: string
  actor?: number
  page?: number
  page_size?: number
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetchAdminDashboard(): Promise<AdminDashboard> {
  return requestJson<AdminDashboard>('/admin/analytics/dashboard', {
    headers: authHeaders(),
  })
}

export async function fetchAdminAuditLog(
  query: AuditLogQuery = {},
): Promise<Paginated<AuditLogRow>> {
  return requestJson<Paginated<AuditLogRow>>(
    '/admin/analytics/audit-log',
    { headers: authHeaders() },
    query as Record<string, string | number | undefined>,
  )
}

/* ── Management CRUD (Phase 13 screens, docs/api/admin.md) ──────────────
 * Write payloads stay `Record<string, unknown>` on the wire: the pages
 * already validate field values (Persian digits → ASCII, numbers, dates)
 * before calling these helpers, and `<fk>_id` conventions differ per
 * resource. Types for reads are strict below. */

function list<T>(
  path: string,
  query: Record<string, unknown> | AdminUsersQuery | OfferingsQuery | AnnouncementQuery | AdminDocumentsQuery = {},
): Promise<Paginated<T>> {
  return requestJson<Paginated<T>>(path, { headers: authHeaders() }, query as Record<string, string | number | undefined>)
}

function mutate<T>(method: 'POST' | 'PATCH' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
  return requestJson<T>(path, {
    method,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    headers: authHeaders(),
  })
}

/* ── Users ─────────────────────────────────────────────────────────────── */

export function listAdminUsers(query: AdminUsersQuery = {}): Promise<Paginated<AdminUser>> {
  return list('/admin/users', query)
}

export const createAdminUser = (payload: AdminUserCreatePayload) =>
  mutate<AdminUser>('POST', '/admin/users', payload)

export const updateAdminUser = (id: number, patch: AdminUserUpdatePayload) =>
  mutate<AdminUser>('PATCH', `/admin/users/${id}`, patch)

/** DELETE deactivates instead of dropping the row (docs/api/admin.md). */
export const deleteAdminUser = (id: number) => mutate<void>('DELETE', `/admin/users/${id}`)

/* ── Courses & prerequisites ──────────────────────────────────────────── */

export function listAdminCourses(
  query: { page?: number; page_size?: number; search?: string; department?: string } = {},
): Promise<Paginated<Course>> {
  return list('/admin/courses', query)
}

export const createAdminCourse = (payload: Record<string, unknown>) =>
  mutate<Course>('POST', '/admin/courses', payload)

export const updateAdminCourse = (id: number, payload: Record<string, unknown>) =>
  mutate<Course>('PATCH', `/admin/courses/${id}`, payload)

export const deleteAdminCourse = (id: number) => mutate<void>('DELETE', `/admin/courses/${id}`)

export const fetchCoursePrerequisites = (courseId: number | string) =>
  requestJson<CoursePrerequisiteEdge[]>(`/admin/courses/${courseId}/prerequisites`, {
    headers: authHeaders(),
  })

export const addCoursePrerequisite = (courseId: number | string, prerequisiteCourseId: number) =>
  mutate<CoursePrerequisiteEdge>('POST', `/admin/courses/${courseId}/prerequisites`, {
    prerequisite_course_id: prerequisiteCourseId,
  })

export const deleteCoursePrerequisite = (edgeId: number) =>
  mutate<void>('DELETE', `/admin/prerequisites/${edgeId}`)

/* ── Professors ───────────────────────────────────────────────────────── */

export function listAdminProfessors(
  query: { page?: number; page_size?: number; search?: string; department?: string; is_active?: string } = {},
): Promise<Paginated<import('../types/academic').Professor>> {
  return list('/admin/professors', query)
}

export const createAdminProfessor = (payload: Record<string, unknown>) =>
  mutate<import('../types/academic').Professor>('POST', '/admin/professors', payload)

export const updateAdminProfessor = (id: number, payload: Record<string, unknown>) =>
  mutate<import('../types/academic').Professor>('PATCH', `/admin/professors/${id}`, payload)

export const deleteAdminProfessor = (id: number) =>
  mutate<void>('DELETE', `/admin/professors/${id}`)

/* ── Academic terms ───────────────────────────────────────────────────── */

export function listAdminTerms(
  query: { page?: number; page_size?: number; is_current?: string } = {},
): Promise<Paginated<AcademicTerm>> {
  return list('/admin/terms', query)
}

export const createAdminTerm = (payload: Record<string, unknown>) =>
  mutate<AcademicTerm>('POST', '/admin/terms', payload)

/** PATCH only — a historical term is immutable and DELETE is not exposed. */
export const updateAdminTerm = (id: number, payload: Record<string, unknown>) =>
  mutate<AcademicTerm>('PATCH', `/admin/terms/${id}`, payload)

/* ── Offerings, schedules, exams ──────────────────────────────────────── */

export function listAdminOfferings(query: OfferingsQuery = {}): Promise<Paginated<CourseOffering>> {
  return list('/admin/offerings', query)
}

export const createAdminOffering = (payload: Record<string, unknown>) =>
  mutate<CourseOffering>('POST', '/admin/offerings', payload)

export const updateAdminOffering = (id: number, payload: Record<string, unknown>) =>
  mutate<CourseOffering>('PATCH', `/admin/offerings/${id}`, payload)

export const deleteAdminOffering = (id: number) => mutate<void>('DELETE', `/admin/offerings/${id}`)

export const fetchOfferingSchedules = (offeringId: number | string) =>
  requestJson<ClassSchedule[]>(`/admin/offerings/${offeringId}/schedules`, {
    headers: authHeaders(),
  })

export const createOfferingSchedule = (offeringId: number | string, payload: Record<string, unknown>) =>
  mutate<ClassSchedule>('POST', `/admin/offerings/${offeringId}/schedules`, payload)

export const updateOfferingSchedule = (scheduleId: number, payload: Record<string, unknown>) =>
  mutate<ClassSchedule>('PATCH', `/admin/schedules/${scheduleId}`, payload)

export const deleteOfferingSchedule = (scheduleId: number) =>
  mutate<void>('DELETE', `/admin/schedules/${scheduleId}`)

/** GET /admin/offerings/{id}/exam/ — `null` when no exam is set yet (404). */
export async function fetchOfferingExam(offeringId: number | string) {
  try {
    return await requestJson<import('../types/academic').Exam>(
      `/admin/offerings/${offeringId}/exam`,
      { headers: authHeaders() },
    )
  } catch (error) {
    const status = (error as { status?: number }).status
    if (status === 404) return null
    throw error
  }
}

export const saveOfferingExam = (
  offeringId: number | string,
  payload: Record<string, unknown>,
  partial: boolean,
) =>
  mutate<import('../types/academic').Exam>(
    partial ? 'PATCH' : 'PUT',
    `/admin/offerings/${offeringId}/exam`,
    payload,
  )

/* ── Announcements ────────────────────────────────────────────────────── */

export function listAdminAnnouncements(query: AnnouncementQuery = {}): Promise<Paginated<Announcement>> {
  return list('/admin/announcements', query)
}

export const createAdminAnnouncement = (payload: Record<string, unknown>) =>
  mutate<Announcement>('POST', '/admin/announcements', payload)

export const updateAdminAnnouncement = (id: number, payload: Record<string, unknown>) =>
  mutate<Announcement>('PATCH', `/admin/announcements/${id}`, payload)

export const deleteAdminAnnouncement = (id: number) =>
  mutate<void>('DELETE', `/admin/announcements/${id}`)

/* ── Documents (upload is multipart, create answers 202) ──────────────── */

export function listAdminDocuments(query: AdminDocumentsQuery = {}): Promise<Paginated<AdminDocument>> {
  return list('/admin/documents', query)
}

export const uploadAdminDocument = (form: FormData) =>
  requestJson<AdminDocument>('/admin/documents', { method: 'POST', body: form, headers: authHeaders() })

export const updateAdminDocument = (id: number, payload: Record<string, unknown>) =>
  mutate<AdminDocument>('PATCH', `/admin/documents/${id}`, payload)

export const deleteAdminDocument = (id: number) => mutate<void>('DELETE', `/admin/documents/${id}`)

export const activateAdminDocument = (id: number) =>
  requestJson<AdminDocument>(`/admin/documents/${id}/activate`, {
    method: 'POST',
    headers: authHeaders(),
  })

export const retryAdminDocument = (id: number) =>
  requestJson<AdminDocument>(`/admin/documents/${id}/retry`, {
    method: 'POST',
    headers: authHeaders(),
  })
