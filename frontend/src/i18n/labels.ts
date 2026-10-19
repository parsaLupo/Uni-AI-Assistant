/**
 * Persian labels for API enum values.
 *
 * The backend serialises enum *values* (OPEN, REGISTRATION, HIGH …) and only
 * provides `*_display` for weekday, so presentation-side mapping lives here —
 * English identifiers stay English on the wire (AGENTS.md localization rules),
 * while every string a user reads is Persian (docs/20).
 */

import type {
  AnnouncementPriority,
  DegreeLevel,
  EventType,
  ExamStatus,
  OfferingStatus,
  SemesterType,
} from '../types/academic'
import type { UserRole } from '../types/api'

export const eventTypeLabels: Record<EventType, string> = {
  REGISTRATION: 'ثبت‌نام',
  EXAM_WEEK: 'هفته امتحانات',
  HOLIDAY: 'تعطیلات',
  CEREMONY: 'مراسم',
  DEADLINE: 'مهلت',
  OTHER: 'سایر',
}

export const priorityLabels: Record<AnnouncementPriority, string> = {
  LOW: 'کم',
  NORMAL: 'عادی',
  HIGH: 'زیاد',
  URGENT: 'فوری',
}

export const offeringStatusLabels: Record<OfferingStatus, string> = {
  OPEN: 'باز',
  CLOSED: 'بسته',
  CANCELLED: 'لغوشده',
}

export const examStatusLabels: Record<ExamStatus, string> = {
  SCHEDULED: 'زمان‌بندی‌شده',
  CHANGED: 'تغییریافته',
  CANCELLED: 'لغوشده',
}

export const degreeLevelLabels: Record<DegreeLevel, string> = {
  BACHELOR: 'کارشناسی',
  MASTER: 'کارشناسی ارشد',
  PHD: 'دکتری',
}

export const semesterLabels: Record<SemesterType, string> = {
  FIRST: 'نیمسال اول',
  SECOND: 'نیمسال دوم',
  SUMMER: 'نیمسال تابستان',
}

export const roleLabels: Record<UserRole, string> = {
  STUDENT: 'دانشجو',
  PROFESSOR: 'استاد',
  ADMIN: 'مدیر',
  SUPERADMIN: 'مدیر ارشد',
}
