/**
 * Centralised TanStack Query keys (ADR-013).
 *
 * One module owns every key so mutations can invalidate exactly the affected
 * resource ("courses" invalidates list+detail together, auth keys stay isolated)
 * instead of pattern-matching strings scattered through feature code.
 */

import type { ListQuery } from '../types/academic'
import type {
  AdminDocumentsQuery,
  AdminUsersQuery,
  AnnouncementQuery,
  OfferingsQuery,
} from '../types/admin'

export const queryKeys = {
  // Auth/session
  me: ['auth', 'me'] as const,

  // Academic resources
  terms: () => ['terms'] as const,
  courses: (query: ListQuery = {}) => ['courses', 'list', query] as const,
  course: (id: number | string) => ['courses', 'detail', id] as const,
  offerings: (query: ListQuery = {}) => ['offerings', query] as const,
  professors: (query: ListQuery = {}) => ['professors', 'list', query] as const,
  professor: (id: number | string) => ['professors', 'detail', id] as const,
  departments: (query?: ListQuery) => ['departments', query] as const,
  events: (query: ListQuery = {}) => ['events', query] as const,
  exams: (query: ListQuery = {}) => ['exams', query] as const,
  announcements: (query: ListQuery = {}) => ['announcements', query] as const,

  // Student
  studentProfile: () => ['students', 'me'] as const,
  planner: (query: ListQuery = {}) => ['students', 'planner', query] as const,

  // Notifications (Phase 12) — count key is invalidated with every mutation.
  notifications: (query: { unread?: boolean; page?: number; page_size?: number } = {}) =>
    ['notifications', 'list', query] as const,
  unreadCount: () => ['notifications', 'unread-count'] as const,

  // Admin live counts (page_size=1 → read `count`)
  adminCount: (resource: string, query: ListQuery = {}) =>
    ['admin', 'count', resource, query] as const,

  // Admin analytics (Phase 13) + audit-log viewer
  adminAnalytics: () => ['admin', 'analytics', 'dashboard'] as const,
  adminAuditLog: (query: { entity_type?: string; action?: string; page?: number; page_size?: number } = {}) =>
    ['admin', 'audit-log', query] as const,

  // Public health probe (admin overview status card)
  health: () => ['health'] as const,

  // Admin management CRUD (Phase 13 screens) — mutations invalidate per
  // resource so the overview's page_size=1 counts stay fresh too.
  adminUsers: (query: AdminUsersQuery = {}) => ['admin', 'users', query] as const,
  adminCourses: (query: { page?: number; page_size?: number; search?: string; department?: string } = {}) =>
    ['admin', 'courses', query] as const,
  coursePrerequisites: (courseId: number | string) =>
    ['admin', 'courses', 'prerequisites', courseId] as const,
  adminProfessors: (query: { page?: number; page_size?: number; search?: string; department?: string } = {}) =>
    ['admin', 'professors', query] as const,
  adminTerms: (query: { page?: number; page_size?: number } = {}) => ['admin', 'terms', query] as const,
  adminOfferings: (query: OfferingsQuery = {}) => ['admin', 'offerings', query] as const,
  offeringSchedules: (offeringId: number | string) =>
    ['admin', 'offerings', 'schedules', offeringId] as const,
  offeringExam: (offeringId: number | string) =>
    ['admin', 'offerings', 'exam', offeringId] as const,
  adminAnnouncements: (query: AnnouncementQuery = {}) => ['admin', 'announcements', query] as const,
  adminDocuments: (query: AdminDocumentsQuery = {}) => ['admin', 'documents', query] as const,
} as const
