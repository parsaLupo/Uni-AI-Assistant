/**
 * Top-bar notification bell (Phase 12): the unread badge is the `unread-count`
 * endpoint, polled every 60s so a newly published announcement shows up without
 * a manual reload. Mutations elsewhere invalidate this query key, so the badge
 * drops as soon as the user reads their reminders.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { fetchUnreadCount } from '../../api/notifications'
import { toPersianDigits } from '../../i18n/digits'
import { nav as navText } from '../../i18n/fa'

/** Badge poll cadence (docs/api/notifications.md: no push channel in this phase). */
const POLL_MS = 60_000

export function NotificationBell() {
  const unread = useQuery({
    queryKey: queryKeys.unreadCount(),
    queryFn: fetchUnreadCount,
    refetchInterval: POLL_MS,
  })

  const count = unread.isError ? 0 : (unread.data?.unread_count ?? 0)

  return (
    <Link
      to="/notifications"
      className="relative flex h-9 w-9 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary"
      aria-label={navText.notifications}
      title={
        count
          ? `${navText.notifications} — ${toPersianDigits(count)}`
          : navText.notifications
      }
    >
      <span className="material-symbols-outlined text-[22px]">
        {count > 0 ? 'notifications' : 'notifications_none'}
      </span>
      {count > 0 ? (
        <span
          data-testid="unread-badge"
          className="absolute -top-1 -left-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-error text-[11px] font-bold text-on-error tnum"
        >
          {toPersianDigits(count > 99 ? 99 : count)}
        </span>
      ) : null}
    </Link>
  )
}
