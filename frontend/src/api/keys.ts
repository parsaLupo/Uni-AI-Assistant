/**
 * Centralised TanStack Query keys (ADR-013).
 *
 * One module owns every key so mutations can invalidate exactly the affected
 * resource ("courses" invalidates list+detail together, auth keys stay isolated)
 * instead of pattern-matching strings scattered through feature code.
 */

import type { ListQuery } from '../types/academic'

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

  // Admin live counts (page_size=1 → read `count`)
  adminCount: (resource: string, query: ListQuery = {}) =>
    ['admin', 'count', resource, query] as const,
} as const
