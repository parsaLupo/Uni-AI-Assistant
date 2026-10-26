/**
 * /calendar — published academic events (GET /calendar/events/).
 *
 * Filters follow docs/api/calendar.md: `?term=current|<id>` and
 * `?event_type=`. Each card shows its own term, so term-scoped facts never
 * appear without context.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
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
import { calendarPage, common, coursesPage } from '../../i18n/fa'
import { formatJalaliDate, weekdayFa } from '../../i18n/jalali'
import { eventTypeLabels } from '../../i18n/labels'
import type { EventType, ListQuery } from '../../types/academic'

const PAGE_SIZE = 20

const EVENT_TYPES: EventType[] = [
  'REGISTRATION',
  'EXAM_WEEK',
  'HOLIDAY',
  'CEREMONY',
  'DEADLINE',
  'OTHER',
]

export function CalendarPage() {
  const [page, setPage] = useUrlState<number>('page', 1)
  const [term, setTerm] = useUrlState<string>('term', 'current')
  const [eventType, setEventType] = useUrlState<string>('event_type', '')

  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 50 }),
  })

  const query: ListQuery = {
    term: term === 'all' ? undefined : term,
    event_type: eventType || undefined,
    page,
    page_size: PAGE_SIZE,
  }
  const events = useQuery({
    queryKey: queryKeys.events(query),
    queryFn: () => academicApi.events(query),
    placeholderData: (previous) => previous,
  })

  const hasFilters = term !== 'current' || Boolean(eventType)
  const changeFilter = (setter: (value: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }
  const clearFilters = () => {
    setTerm('current')
    setEventType('')
    setPage(1)
  }

  const rows = events.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={calendarPage.title}
        subtitle={calendarPage.subtitle}
      />

      <FilterRow>
        <FilterSelect
          icon="event"
          label={common.filterTerm}
          value={term}
          onChange={changeFilter(setTerm)}
          className="w-52"
        >
          <option value="current">{common.filterCurrent}</option>
          <option value="all">{common.filterAll}</option>
          {(terms.data?.results ?? [])
            .filter((row) => !row.is_current)
            .map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
        </FilterSelect>

        <FilterSelect
          icon="label_important"
          label={calendarPage.eventType}
          value={eventType}
          onChange={changeFilter(setEventType)}
          className="w-48"
        >
          <option value="">{calendarPage.allTypes}</option>
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {eventTypeLabels[type]}
            </option>
          ))}
        </FilterSelect>

        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}

        {events.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {events.data.count}
          </span>
        ) : null}
      </FilterRow>

      {events.isPending ? (
        <SkeletonRows count={5} />
      ) : events.isError ? (
        <ErrorState error={events.error} onRetry={() => void events.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          message={calendarPage.empty}
          hint={calendarPage.emptyHint}
          action={
            hasFilters ? (
              <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
                {common.clearFilters}
              </button>
            ) : (
              <Link to="/courses" className="text-label-lg text-primary hover:underline">
                {coursesPage.title}
              </Link>
            )
          }
        />
      ) : (
        <>
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
                  <span>{common.filterTerm}: {event.term.name}</span>
                </div>
                {event.description ? (
                  <p className="m-0 text-body-sm text-on-surface-variant">{event.description}</p>
                ) : null}
              </article>
            ))}
          </div>
          <PaginationBar
            count={events.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}
