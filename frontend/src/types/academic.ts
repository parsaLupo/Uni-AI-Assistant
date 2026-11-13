/**
 * API response types mirroring the backend contract for the Phase 04 academic
 * resources (openapi.yaml). Reads nest related objects under the FK name and
 * list endpoints use the shared pagination envelope — both conventions come
 * straight from docs/04-api-specification.md.
 */

import type { Paginated } from './api'

export interface Faculty {
  id: number
  name: string
  code: string
  website: string | null
  description: string | null
  is_active: boolean
}

export interface Department {
  id: number
  faculty: Faculty
  name: string
  code: string
  description: string | null
  is_active: boolean
}

export type SemesterType = 'FIRST' | 'SECOND' | 'SUMMER'

export interface AcademicTerm {
  id: number
  name: string
  academic_year: string
  semester_type: SemesterType
  /** ISO date (`YYYY-MM-DD`) — a *date*, not an instant. */
  starts_at: string
  ends_at: string
  is_current: boolean
}

export interface CourseBrief {
  id: number
  code: string
  title: string
  credits: number
  course_type: string
}

/** Compact prerequisite row: {id, code, title, credits}. */
export type CoursePrerequisite = CourseBrief

export interface Course extends CourseBrief {
  active: boolean
  department: Department
  prerequisites: CoursePrerequisite[]
}

export interface ClassSchedule {
  id: number
  /**
   * Backend `Weekday` choice value: 0=یکشنبه … 4=پنجشنبه, 5=شنبه, 6=جمعه.
   * This is NOT JS `Date#getDay()` numbering (there جمعه=5, شنبه=6) —
   * convert with `scheduleWeekdayToJs` before comparing to `getDay()`.
   */
  weekday: number
  /** Persian label from the server (`get_weekday_display`). */
  weekday_display: string
  start_time: string // "HH:MM:SS"
  end_time: string
  classroom: string
}

export interface ProfessorBrief {
  id: number
  first_name: string
  last_name: string
  full_name: string
  academic_title: string
}

export type OfferingStatus = 'OPEN' | 'CLOSED' | 'CANCELLED'
export type ExamStatus = 'SCHEDULED' | 'CHANGED' | 'CANCELLED'

export interface ExamOfferingBrief {
  id: number
  course_code: string
  course_title: string
  section_code: string
  term: AcademicTerm
}

export interface Exam {
  id: number
  course_offering: ExamOfferingBrief
  starts_at: string
  ends_at: string
  classroom: string
  status: ExamStatus
  last_updated_at: string
  created_at: string
}

export interface CourseOffering {
  id: number
  course: CourseBrief
  term: AcademicTerm
  professor: ProfessorBrief | null
  section_code: string
  capacity: number
  status: OfferingStatus
  enrolled_count: number
  /** Detail payloads only (course-offerings list and planner rows include them). */
  schedules?: ClassSchedule[]
  exam?: Exam | null
}

export interface Professor {
  id: number
  department: Department
  first_name: string
  last_name: string
  academic_title: string
  email: string
  office: string
  website: string | null
  bio: string
  is_active: boolean
}

export type EventType =
  | 'REGISTRATION'
  | 'EXAM_WEEK'
  | 'HOLIDAY'
  | 'CEREMONY'
  | 'DEADLINE'
  | 'OTHER'

export interface AcademicEvent {
  id: number
  term: AcademicTerm
  title: string
  event_type: EventType
  starts_at: string
  ends_at: string
  description: string
  is_published: boolean
}

export type AnnouncementPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT'

export interface Announcement {
  id: number
  term: AcademicTerm | null
  audience_faculty: Faculty | null
  audience_department: Department | null
  title: string
  body: string
  priority: AnnouncementPriority
  published_at: string | null
  expires_at: string | null
  is_published: boolean
}

export type DegreeLevel = 'BACHELOR' | 'MASTER' | 'PHD'

export interface StudentProfile {
  id: number
  user: { id: number; email: string; first_name: string; last_name: string }
  student_number: string | null
  department: { id: number; name: string; code: string } | null
  faculty: Faculty | null
  degree_level: DegreeLevel | ''
  entry_year: string
  current_term_number: number | null
  current_gpa: string | null // Decimal as string ("17.84")
  onboarding_complete: boolean
}

export type PlannerStatus = 'PLANNED' | 'ENROLLED' | string

export interface PlannerItem {
  id: number
  course_offering: CourseOffering
  status: PlannerStatus
  total_credits: number
  enrolled_at: string
  updated_at: string
}

/** StandardResultsSetPagination subset — used for admin live counts. */
export type CountOnly = Pick<Paginated<unknown>, 'count'>

/** Generic list query understood by every public list endpoint. */
export interface ListQuery {
  page?: number
  page_size?: number
  search?: string
  term?: string | number
  course?: string | number
  professor?: number
  department?: number
  /** Phase 06: documented filters on GET /api/v1/courses/ (docs/api/courses.md). */
  credits?: number
  course_type?: string
  event_type?: string
  /** GET /api/v1/exams/?student=me — the caller's own enrolled offerings. */
  student?: string
  ordering?: string
}
