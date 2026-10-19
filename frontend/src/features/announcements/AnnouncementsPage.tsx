/**
 * /announcements — the published feed (GET /announcements/). Expiry and
 * audience filtering are already enforced server-side, so what renders here is
 * exactly what the caller is allowed to see (docs/api/admin.md list rules).
 */

import { useQuery } from '@tanstack/react-query'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  PaginationBar,
  cardCls,
} from '../../components/ui'
import { announcementsPage, common } from '../../i18n/fa'
import { formatJalaliDate } from '../../i18n/jalali'
import { priorityLabels } from '../../i18n/labels'
import { useState } from 'react'

const PAGE_SIZE = 10

export function AnnouncementsPage() {
  const [page, setPage] = useState(1)
  const announcements = useQuery({
    queryKey: queryKeys.announcements({ page, page_size: PAGE_SIZE }),
    queryFn: () => academicApi.announcements({ page, page_size: PAGE_SIZE }),
    placeholderData: (previous) => previous,
  })

  const rows = announcements.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader title={announcementsPage.title} subtitle={announcementsPage.subtitle} />

      {announcements.isPending ? (
        <LoadingState />
      ) : announcements.isError ? (
        <ErrorState error={announcements.error} onRetry={() => void announcements.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={announcementsPage.empty} />
      ) : (
        <>
          <div className="flex flex-col gap-space-md">
            {rows.map((row, index) => {
              const urgent = row.priority === 'HIGH' || row.priority === 'URGENT'
              const audience =
                row.audience_department?.name ??
                row.audience_faculty?.name ??
                announcementsPage.audienceAll
              return (
                <article
                  key={row.id}
                  className={`${cardCls} flex flex-col gap-space-sm p-space-lg transition-all hover:shadow-md ${index % 2 === 1 ? 'bg-surface-container-low/40' : ''}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-space-sm">
                    <div className="flex flex-wrap items-center gap-space-sm">
                      <Chip tone={urgent ? 'warning' : 'primary'}>
                        {urgent ? (
                          <span className="material-symbols-outlined text-[14px]">priority_high</span>
                        ) : null}
                        {priorityLabels[row.priority]}
                      </Chip>
                      <h2 className="m-0 text-headline-sm font-bold text-on-surface">{row.title}</h2>
                    </div>
                    <span className="flex items-center gap-1 text-label-sm text-outline tnum">
                      <span className="material-symbols-outlined text-[14px]">calendar_today</span>
                      {announcementsPage.publishedAt}:{' '}
                      {row.published_at ? formatJalaliDate(row.published_at) : common.notSetFallback}
                    </span>
                  </div>

                  <p className="m-0 whitespace-pre-line text-body-md leading-relaxed text-on-surface-variant">
                    {row.body}
                  </p>

                  <div className="flex flex-wrap items-center gap-space-md border-t border-outline-variant pt-space-sm text-label-sm text-on-surface-variant">
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[14px]">groups</span>
                      {announcementsPage.audience}: {audience}
                    </span>
                    <span className="tnum">
                      {announcementsPage.expiresAt}:{' '}
                      {row.expires_at
                        ? formatJalaliDate(row.expires_at)
                        : announcementsPage.noExpiry}
                    </span>
                    {row.term ? <span className="tnum">{row.term.name}</span> : null}
                  </div>
                </article>
              )
            })}
          </div>
          <PaginationBar
            count={announcements.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}