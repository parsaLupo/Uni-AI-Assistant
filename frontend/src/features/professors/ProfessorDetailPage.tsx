/**
 * /professors/:id — profile card + the professor's offerings for a term
 * (GET /professors/{id}/ + GET /course-offerings/?professor=<id>&term=…).
 *
 * Offerings are term-scoped, so the term is a visible filter (default: the
 * current term) and every row repeats the term name and weekly schedule.
 */

import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  FilterSelect,
  LoadingState,
  PageHeader,
  cardCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { common, coursesPage, professorsPage } from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import { formatTimeFa } from '../../i18n/jalali'
import type { ListQuery } from '../../types/academic'

export function ProfessorDetailPage() {
  const { id } = useParams<{ id: string }>()
  const professorId = Number(id)
  const [term, setTerm] = useUrlState<string>('term', 'current')

  const professor = useQuery({
    queryKey: queryKeys.professor(professorId),
    queryFn: () => academicApi.professor(professorId),
    enabled: Number.isFinite(professorId),
  })
  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 50 }),
  })

  const offeringsQuery: ListQuery = {
    professor: professorId,
    term: term === 'all' ? undefined : term,
    page_size: 50,
  }
  const offerings = useQuery({
    queryKey: queryKeys.offerings(offeringsQuery),
    queryFn: () => academicApi.offerings(offeringsQuery),
    enabled: Number.isFinite(professorId),
    placeholderData: (previous) => previous,
  })

  if (professor.isPending) {
    return (
      <div className="px-gutter-desktop pt-space-lg">
        <LoadingState />
      </div>
    )
  }
  if (professor.isError) {
    return (
      <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
        <ErrorState error={professor.error} onRetry={() => void professor.refetch()} />
        <Link to="/professors" className="w-fit text-label-lg text-primary hover:underline">
          {professorsPage.backToList}
        </Link>
      </div>
    )
  }

  const data = professor.data
  const rows = offerings.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <Link
        to="/professors"
        className="flex w-fit items-center gap-1 text-label-lg text-primary hover:underline"
      >
        <span className="material-symbols-outlined text-[18px]">chevron_right</span>
        {common.back}
      </Link>

      <PageHeader
        title={`${data.academic_title} ${data.first_name} ${data.last_name}`}
        subtitle={data.department.name}
      />

      <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
        <section className={`${cardCls} flex flex-col gap-space-sm p-space-lg lg:col-span-4`}>
          <dl className="m-0 flex flex-col gap-space-sm text-body-sm">
            {data.office ? (
              <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
                <dt className="text-on-surface-variant">{professorsPage.office}</dt>
                <dd className="m-0 font-semibold text-on-surface">{data.office}</dd>
              </div>
            ) : null}
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">{professorsPage.email}</dt>
              <dd className="m-0 font-semibold text-on-surface" dir="ltr">
                {data.email}
              </dd>
            </div>
            {data.website ? (
              <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
                <dt className="text-on-surface-variant">{professorsPage.website}</dt>
                <dd className="m-0">
                  <a
                    href={data.website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                    dir="ltr"
                  >
                    {data.website}
                  </a>
                </dd>
              </div>
            ) : null}
            <div className="flex justify-between gap-space-sm">
              <dt className="text-on-surface-variant">{common.statusLabel}</dt>
              <dd className="m-0">
                <Chip tone={data.is_active ? 'success' : 'neutral'}>
                  {data.is_active ? coursesPage.active : coursesPage.inactive}
                </Chip>
              </dd>
            </div>
          </dl>
          {data.bio ? (
            <div className="border-t border-outline-variant pt-space-sm">
              <span className="text-label-lg font-bold text-on-surface">{professorsPage.bio}</span>
              <p className="m-0 text-body-sm leading-relaxed text-on-surface-variant">{data.bio}</p>
            </div>
          ) : null}
        </section>

        <section className={`${cardCls} flex flex-col gap-space-md p-space-lg lg:col-span-8`}>
          <div className="flex flex-wrap items-center justify-between gap-space-sm">
            <h2 className="m-0 text-headline-md font-bold text-on-surface">
              {professorsPage.offerings}
            </h2>
            <FilterSelect
              icon="event"
              label={professorsPage.term}
              value={term}
              onChange={setTerm}
              className="w-52"
            >
              <option value="current">{common.filterCurrent}</option>
              <option value="all">{professorsPage.termAll}</option>
              {(terms.data?.results ?? [])
                .filter((row) => !row.is_current)
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
            </FilterSelect>
          </div>

          {offerings.isPending ? (
            <LoadingState />
          ) : offerings.isError ? (
            <ErrorState error={offerings.error} onRetry={() => void offerings.refetch()} />
          ) : rows.length === 0 ? (
            <EmptyState
              message={
                term === 'current' ? professorsPage.noCurrentOfferings : professorsPage.noOfferings
              }
              hint={coursesPage.noOfferingsHint}
            />
          ) : (
            <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
              {rows.map((offering) => (
                <li
                  key={offering.id}
                  className="flex flex-wrap items-center justify-between gap-space-sm rounded-xl bg-surface-container-low p-space-md"
                >
                  <div className="flex flex-col gap-0.5">
                    <Link
                      to={`/courses/${offering.course.id}`}
                      className="text-headline-sm font-bold text-on-surface hover:text-primary"
                    >
                      {offering.course.title} ({offering.course.code})
                    </Link>
                    <span className="text-label-sm text-on-surface-variant tnum">
                      {offering.term.name} — {coursesPage.section}{' '}
                      {toPersianDigits(offering.section_code)}
                    </span>
                    <span className="text-label-sm text-on-surface-variant tnum">
                      {professorsPage.schedule}:{' '}
                      {(offering.schedules ?? []).length > 0
                        ? (offering.schedules ?? [])
                            .map(
                              (slot) =>
                                `${slot.weekday_display} ${formatTimeFa(slot.start_time)}–${formatTimeFa(slot.end_time)}`,
                            )
                            .join(' | ')
                        : coursesPage.noSchedule}
                    </span>
                  </div>
                  <Chip tone="success">
                    {toPersianDigits(offering.course.credits)} {common.credits}
                  </Chip>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
