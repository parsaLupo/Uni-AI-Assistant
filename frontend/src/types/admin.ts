/**
 * Phase 13 — types for the admin management contracts (docs/api/admin.md).
 *
 * Shapes mirror the DRF serializers exactly: reads nest related objects under
 * the FK name, writes take `<fk>_id` (the Phase 04 convention), and list
 * endpoints use the shared pagination envelope.
 */

import type { UserRole } from './api'
import type {
  Announcement,
  AcademicTerm,
  ClassSchedule,
  Course,
  CourseBrief,
  CourseOffering,
  Exam,
  Professor,
} from './academic'

/* ── Users (accounts) ─────────────────────────────────────────────────── */

/** User row as returned by GET /admin/users/ (MeSerializer shape). */
export interface AdminUser {
  id: number
  email: string
  first_name: string
  last_name: string
  role: UserRole
  is_active: boolean
}

export interface AdminUsersQuery {
  page?: number
  page_size?: number
  search?: string
  role?: UserRole | ''
  is_active?: 'true' | 'false' | ''
}

export interface AdminUserCreatePayload {
  email: string
  password: string
  first_name?: string
  last_name?: string
  role: UserRole
}

export interface AdminUserUpdatePayload {
  first_name?: string
  last_name?: string
  role?: UserRole
  is_active?: boolean
}

/* ── Courses / prerequisites / offerings / schedules / exams ──────────── */

/** One prerequisite edge: GET /admin/courses/{id}/prerequisites/. */
export interface CoursePrerequisiteEdge {
  id: number
  course: CourseBrief
  prerequisite_course: CourseBrief
}

export interface OfferingsQuery {
  page?: number
  page_size?: number
  /** Term id or the documented literal "current". */
  term?: string
  course?: string /** id or code */
  professor?: string
  status?: string
}

export type { Course, CourseOffering, ClassSchedule, Exam, AcademicTerm, Professor }

/* ── Documents (docs/api/documents.md) ────────────────────────────────── */

export type DocumentStatusValue =
  | 'UPLOADED'
  | 'VALIDATING'
  | 'PROCESSING'
  | 'INDEXED'
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'INACTIVE'
  | 'ARCHIVED'
  | 'FAILED'

export interface AdminDocument {
  id: number
  title: string
  document_type: string
  academic_year: string
  effective_from: string | null
  effective_to: string | null
  version: number
  status: DocumentStatusValue
  processing_error: string
  failure_stage: string
  attempt_count: number
  uploaded_by: number | null
  created_at: string
  updated_at: string
}

export interface AdminDocumentsQuery {
  page?: number
  page_size?: number
  search?: string
  status?: DocumentStatusValue | ''
  document_type?: string
  academic_year?: string
}

/* ── Announcements ────────────────────────────────────────────────────── */

export interface AnnouncementQuery {
  page?: number
  page_size?: number
  search?: string
  term?: string
  is_published?: 'true' | 'false' | ''
}

export type AnnouncementRow = Announcement

