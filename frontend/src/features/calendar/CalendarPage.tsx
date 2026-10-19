/** /calendar — published academic events (GET /calendar/events/). */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  cardCls,
} from '../../components/ui'
import { calendarPage, common } from '../../i18n/fa'
import { formatJalaliDate, weekdayFa } from '../../i18n/jalali'
import { eventTypeLabels } from '../../i18n/labels'
import type { EventType, ListQuery } from '../../types/academic'

const EVENT_TYPES: EventType[] = [
  'REGISTRATION',
  'EXAM_WEEK',
  'HOLIDAY',
  'CEREMONY',
  'DEADLINE',
  'OTHER',
]

export function CalendarPage() {
  const [term, setTerm] = useState<'current' | 'all'>('current')
  const [eventType, setEventType] = useState<'' | EventType>('')

  const query: ListQuery = {
    term: term === 'current' ? 'current' : undefined,
    event_type: eventType || undefined,
    page_size: 50,
  }
  const events = useQuery({
    queryKey: queryKeys.events(query),
    queryFn: () => academicApi.events(query),
  })

  const rows = events.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={calendarPage.title}
        subtitle={calendarPage.subtitle}
        actions={
          <div className="flex flex-wrap items-center gap-space-sm">
            <select
              value={term}
              onChange={(event) => setTerm(event.target.value as 'current' | 'all')}
              aria-label={common.filterTerm}
              className="rounded-xl border border-[#CBD5E1] bg-white px-space-sm py-2 text-body-sm text-[#0F172A] focus:border-[#2563EB] focus:outline-none"
            >
              <option value="current">{common.filterCurrent}</option>
              <option value="all">{common.filterAll}</option>
            </select>
            <select
              value={eventType}
              onChange={(event) => setEventType(event.target.value as '' | EventType)}
              aria-label={calendarPage.eventType}
              className="rounded-xl border border-[#CBD5E1] bg-white px-space-sm py-2 text-body-sm text-[#0F172A] focus:border-[#2563EB] focus:outline-none"
            >
              <option value="">{calendarPage.allTypes}</option>
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {eventTypeLabels[type]}
                </option>
              ))}
            </select>
          </div>
        }
      />

      {events.isPending ? (
        <LoadingState />
      ) : events.isError ? (
        <ErrorState error={events.error} onRetry={() => void events.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={calendarPage.empty} />
      ) : (
        <div className="flex flex-col gap-space-sm">
          {rows.map((event, index) => (
            <article
              key={event.id}
              className={`${cardCls} flex flex-col gap-space-sm p-space-md transition-all hover:shadow-md ${index % 2 === 1 ? 'bg-surface-container-low/40' : ''}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-space-sm">
                <div className="flex flex-wrap items-center gap-space-sm">
                  <Chip tone="primary">{eventTypeLabels[event.event_type]}</Chip>
                  <h2 className="m-0 text-headline-sm font-bold text-on-surface">{event.title}</h2>
                </div>
                <Chip>
                  <span className="material-symbols-outlined text-[14px] text-secondary">
                    calendar_today
                  </span>
                  <span className="tnum">
                    {formatJalaliDate(event.starts_at)} ({weekdayFa(new Date(event.starts_at))})
                  </span>
                </Chip>
              </div>
              <div className="flex flex-wrap items-center gap-space-md text-label-sm text-on-surface-variant tnum">
                <span>
                  {calendarPage.from}: {formatJalaliDate(event.starts_at)}
                </span>
                <span>
                  {calendarPage.to}: {formatJalaliDate(event.ends_at)}
                </span>
                <span>{event.term.name}</span>
              </div>
              {event.description ? (
                <p className="m-0 text-body-sm text-on-surface-variant">{event.description}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}