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
import type { NotificationType } from '../api/notifications'
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

export const notificationTypeLabels: Record<NotificationType, string> = {
  ANNOUNCEMENT: 'اطلاعیه',
  DEADLINE: 'مهلت',
  EXAM: 'امتحان',
  SYSTEM: 'سیستمی',
}

/** Execution modes (docs/08 §2) — the routed mode persisted on answers. */
export const executionModeLabels: Record<string, string> = {
  STRUCTURED: 'پاسخ از داده ساختاریافته',
  RAG: 'پاسخ از اسناد',
  HYBRID: 'پاسخ ترکیبی',
  GENERAL: 'توضیح عمومی',
  OUT_OF_SCOPE: 'خارج از دامنه',
}

/** Document lifecycle (Phase 07 model choices) — Persian presentation. */
export const documentStatusLabels: Record<string, string> = {
  UPLOADED: 'آپلود شده',
  VALIDATING: 'در حال اعتبارسنجی',
  PROCESSING: 'در حال پردازش',
  INDEXED: 'ایندکس شده',
  ACTIVE: 'فعال',
  SUPERSEDED: 'جایگزین شده',
  INACTIVE: 'غیرفعال',
  ARCHIVED: 'آرشیو شده',
  FAILED: 'ناموفق',
}

/** Persian chip tone per document status for the admin table. */
export const documentStatusTone: Record<string, 'success' | 'warning' | 'primary' | 'neutral' | 'danger'> = {
  UPLOADED: 'neutral',
  VALIDATING: 'primary',
  PROCESSING: 'primary',
  INDEXED: 'primary',
  ACTIVE: 'success',
  SUPERSEDED: 'neutral',
  INACTIVE: 'neutral',
  ARCHIVED: 'neutral',
  FAILED: 'danger',
}
