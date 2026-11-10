/**
 * Phase 12 — in-app notifications (docs/api/notifications.md).
 *
 * Every endpoint is user-scoped *on the server*: list, badges and mark-read
 * mutations only ever touch the caller's rows, so the UI never needs to filter
 * anything locally. `?unread=true` is a server-side narrowing too.
 */

import { requestJson } from './client'
import { getAccessToken } from '../features/auth/session'
import type { Paginated } from '../types/api'

export type NotificationType = 'ANNOUNCEMENT' | 'DEADLINE' | 'EXAM' | 'SYSTEM'

export interface SchoolNotification {
  id: number
  type: NotificationType
  title: string
  body: string
  /** App path of the related surface (e.g. '/announcements'), may be empty. */
  link: string
  is_read: boolean
  read_at: string | null
  expires_at: string | null
  created_at: string
}

export interface NotificationQuery {
  page?: number
  page_size?: number
  /** Server-side narrowing to unread rows only. */
  unread?: boolean
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function listNotifications(
  query: NotificationQuery = {},
): Promise<Paginated<SchoolNotification>> {
  return requestJson<Paginated<SchoolNotification>>(
    '/notifications',
    { headers: authHeaders() },
    query as Record<string, string | number | undefined>,
  )
}

export async function fetchUnreadCount(): Promise<{ unread_count: number }> {
  return requestJson<{ unread_count: number }>('/notifications/unread-count', {
    headers: authHeaders(),
  })
}

export async function markNotificationRead(id: number): Promise<SchoolNotification> {
  return requestJson<SchoolNotification>(
    `/notifications/${id}/mark-read`,
    { method: 'POST', headers: authHeaders() },
  )
}

export async function markAllNotificationsRead(): Promise<{ updated: number }> {
  return requestJson<{ updated: number }>('/notifications/mark-all-read', {
    method: 'POST',
    headers: authHeaders(),
  })
}
