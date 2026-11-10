/**
 * /notifications — Phase 12 in-app notification center.
 *
 * Thin client over `GET /notifications/` (docs/api/notifications.md): the
 * server already restricts the list to the caller's non-expired rows and
 * handles `?unread=true`, so the page only renders and persists read state via
 * the documented mark-read endpoints. Visible rows are NOT auto-marked read —
 * reading remains an explicit user action so unseen reminders stay visible.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../api/keys'
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationQuery,
  type SchoolNotification,
} from '../../api/notifications'
import type { NotificationType } from '../../api/notifications'
import {
  Chip,
  EmptyState,
  ErrorState,
  FilterRow,
  FilterSelect,
  PageHeader,
  PaginationBar,
  SkeletonRows,
  btnSecondaryCls,
  cardCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { toPersianDigits } from '../../i18n/digits'
import { formatJalaliDate } from '../../i18n/jalali'
import { notificationTypeLabels } from '../../i18n/labels'
import { common, notificationsPage } from '../../i18n/fa'

const PAGE_SIZE = 10
const UNREAD_QUERY = { unread: true } as const

export function NotificationsPage() {
  const [page, setPage] = useUrlState<number>('page', 1)
  const [scope, setScope] = useUrlState<string>('scope', '')

  const query: NotificationQuery = {
    page,
    page_size: PAGE_SIZE,
    ...(scope === 'unread' ? UNREAD_QUERY : {}),
  }
  const queryClient = useQueryClient()
  const notifications = useQuery({
    queryKey: queryKeys.notifications(query),
    queryFn: () => listNotifications(query),
    placeholderData: (previous) => previous,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.notifications({}) })
    void queryClient.invalidateQueries({ queryKey: queryKeys.unreadCount() })
  }

  const markOne = useMutation({
    mutationFn: (id: number) => markNotificationRead(id),
    onSuccess: invalidate,
  })
  const markAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  })

  const rows = notifications.data?.results ?? []
  const hasActiveUnread = rows.some((row) => !row.is_read)

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader title={notificationsPage.title} subtitle={notificationsPage.subtitle} />

      <FilterRow>
        <FilterSelect
          icon="notifications"
          label={common.statusLabel}
          value={scope}
          onChange={(value) => {
            setScope(value)
            setPage(1)
          }}
          className="w-52"
        >
          <option value="">{common.filterAll}</option>
          <option value="unread">{notificationsPage.unreadOnly}</option>
        </FilterSelect>

        {hasActiveUnread ? (
          <button
            type="button"
            className={btnSecondaryCls}
            onClick={() => markAll.mutate()}
            disabled={markAll.isPending}
            aria-label={notificationsPage.markAllRead}
          >
            <span className="material-symbols-outlined text-[16px]">done_all</span>
            {notificationsPage.markAllRead}
            {markAll.isPending ? '…' : ''}
          </button>
        ) : null}

        {notifications.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(notifications.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {notifications.isPending ? (
        <SkeletonRows count={4} />
      ) : notifications.isError ? (
        <ErrorState
          error={notifications.error}
          onRetry={() => void notifications.refetch()}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          message={notificationsPage.empty}
          hint={notificationsPage.emptyHint}
          action={
            scope === 'unread' ? (
              <button
                type="button"
                className={btnSecondaryCls}
                onClick={() => {
                  setScope('')
                  setPage(1)
                }}
              >
                {common.filterAll}
              </button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="flex flex-col gap-space-md">
            {rows.map((row, index) => (
              <NotificationRow
                key={row.id}
                notification={row}
                dimmed={index % 2 === 1}
                onMarkRead={() => markOne.mutate(row.id)}
                marking={markOne.isPending && markOne.variables === row.id}
              />
            ))}
          </div>
          <PaginationBar
            count={notifications.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}

function NotificationRow({
  notification,
  dimmed,
  onMarkRead,
  marking,
}: {
  notification: SchoolNotification
  dimmed: boolean
  onMarkRead: () => void
  marking: boolean
}) {
  const readLabel = typeLabel(notification.type)
  return (
    <article
      className={[
        cardCls,
        'flex flex-col gap-space-sm p-space-lg transition-all hover:shadow-md',
        dimmed ? 'bg-surface-container-low/40' : '',
      ].join(' ')}
    >
      <div className="flex flex-wrap items-center justify-between gap-space-sm">
        <div className="flex flex-wrap items-center gap-space-sm">
          <Chip tone={notification.is_read ? 'neutral' : 'primary'}>
            <span className="material-symbols-outlined text-[14px]">
              {typeIcon(notification.type)}
            </span>
            {readLabel}
          </Chip>
          <h2
            className={`m-0 text-headline-sm ${notification.is_read ? 'font-semibold text-on-surface-variant' : 'font-bold text-on-surface'}`}
          >
            {notification.title}
          </h2>
          {!notification.is_read ? <Chip tone="warning">{notificationsPage.unreadBadge}</Chip> : null}
        </div>
        {!notification.is_read ? (
          <button
            type="button"
            onClick={onMarkRead}
            disabled={marking}
            className={btnSecondaryCls}
            aria-label={notificationsPage.markRead}
          >
            {marking ? common.loading : notificationsPage.markRead}
          </button>
        ) : null}
      </div>

      {notification.body ? (
        <p className="m-0 whitespace-pre-line text-body-md leading-relaxed text-on-surface-variant">
          {notification.body}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-space-md border-t border-outline-variant pt-space-sm text-label-sm text-on-surface-variant">
        <span className="tnum">
          <span className="material-symbols-outlined inline-flex align-middle text-[14px]">
            calendar_today
          </span>{' '}
          {formatJalaliDate(notification.created_at)}
        </span>
        <span className="tnum">
          {notificationsPage.expiresAt}:{' '}
          {notification.expires_at
            ? formatJalaliDate(notification.expires_at)
            : notificationsPage.noExpiry}
        </span>
      </div>
    </article>
  )
}

function typeIcon(type: NotificationType): string {
  switch (type) {
    case 'ANNOUNCEMENT':
      return 'campaign'
    case 'DEADLINE':
      return 'schedule'
    case 'EXAM':
      return 'assignment'
    default:
      return 'info'
  }
}

function typeLabel(type: NotificationType): string {
  return notificationTypeLabels[type]
}
