/**
 * /exams — end-of-term exam schedule.
 *
 * Data: GET /exams/ with the documented filters (docs/api/exams.md):
 * `?term=current|<id>`, `?course=<id|code>` and `?student=me`. The API nests
 * the offering's term, so every row shows its term context; dates render in
 * Jalali and numbers in Persian digits.
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
  SearchInput,
  SkeletonRows,
  btnSecondaryCls,
  cardCls,
  tableCls,
  tdCls,
  thCls,
  trCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { common, coursesPage, examsPage } from '../../i18n/fa'
import { useAuth } from '../auth'
import { toAsciiDigits, toPersianDigits } from '../../i18n/digits'
import { daysUntil, formatJalaliDate, formatTimeFa } from '../../i18n/jalali'
import { examStatusLabels } from '../../i18n/labels'
import type { ListQuery } from '../../types/academic'

const PAGE_SIZE = 25

export function ExamsPage() {
  const { user } = useAuth()
  const isStudent = user?.role === 'STUDENT'

  const [page, setPage] = useUrlState<number>('page', 1)
  const [term, setTerm] = useUrlState<string>('term', 'current')
  const [course, setCourse] = useUrlState<string>('course', '', { debounce: 300 })
  const [studentFilter, setStudentFilter] = useUrlState<string>('student', '')

  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 50 }),
  })

  const courseCode = toAsciiDigits(course.trim())
  const onlyMine = studentFilter === 'me'

  const query: ListQuery = {
    term: term === 'all' ? undefined : term,
    course: courseCode || undefined,
    student: onlyMine ? 'me' : undefined,
    page,
    page_size: PAGE_SIZE,
  }
  const exams = useQuery({
    queryKey: queryKeys.exams(query),
    queryFn: () => academicApi.exams(query),
    placeholderData: (previous) => previous,
  })

  const hasFilters = term !== 'current' || Boolean(courseCode) || onlyMine
  const changeFilter = (setter: (value: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }
  const clearFilters = () => {
    setTerm('current')
    setCourse('')
    setStudentFilter('')
    setPage(1)
  }

  const rows = exams.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={examsPage.title}
        subtitle={examsPage.subtitle}
        actions={
          isStudent ? (
            <SearchInput
              value={course}
              onChange={changeFilter(setCourse)}
              placeholder={examsPage.courseCodePlaceholder}
              label={examsPage.courseCode}
              className="w-full max-w-xs"
            />
          ) : undefined
        }
      />

      <FilterRow>
        <FilterSelect
          icon="event"
          label={examsPage.term}
          value={term}
          onChange={changeFilter(setTerm)}
          className="w-52"
        >
          <option value="current">{examsPage.termCurrent}</option>
          <option value="all">{examsPage.termAll}</option>
          {(terms.data?.results ?? [])
            .filter((row) => !row.is_current)
            .map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
        </FilterSelect>

        {isStudent ? (
          <label className="flex items-center gap-space-xs text-body-sm text-on-surface-variant">
            <input
              type="checkbox"
              checked={onlyMine}
              onChange={(event) => {
                setStudentFilter(event.target.checked ? 'me' : '')
                setPage(1)
              }}
              className="h-4 w-4 rounded border-outline-variant text-primary focus:ring-2 focus:ring-primary/30"
            />
            {examsPage.onlyMine}
          </label>
        ) : null}

        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}

        {exams.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(exams.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {exams.isPending ? (
        <SkeletonRows count={6} />
      ) : exams.isError ? (
        <ErrorState error={exams.error} onRetry={() => void exams.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          message={examsPage.empty}
          hint={examsPage.emptyHint}
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
          <div className={`${cardCls} overflow-x-auto p-space-lg`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={`${thCls} rounded-r-lg`}>{examsPage.colExam}</th>
                  <th className={thCls}>{examsPage.colDate}</th>
                  <th className={thCls}>{examsPage.colTime}</th>
                  <th className={thCls}>{examsPage.colClassroom}</th>
                  <th className={thCls}>{common.statusLabel}</th>
                  <th className={`${thCls} rounded-l-lg`}>{examsPage.daysLeft}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((exam, index) => {
                  const days = daysUntil(exam.starts_at)
                  return (
                    <tr key={exam.id} className={trCls(index)}>
                      <td className={`${tdCls} font-semibold text-on-surface`}>
                        <span>{exam.course_offering.course_title}</span> (
                        <span className="tnum">{exam.course_offering.course_code}</span>)
                        <span className="block text-label-sm text-on-surface-variant tnum">
                          {examsPage.section} {toPersianDigits(exam.course_offering.section_code)}{' '}
                          — {exam.course_offering.term.name}
                        </span>
                      </td>
                      <td className={`${tdCls} tnum`}>{formatJalaliDate(exam.starts_at)}</td>
                      <td className={`${tdCls} tnum`}>
                        {formatTimeFa(new Date(exam.starts_at))} –{' '}
                        {formatTimeFa(new Date(exam.ends_at))}
                      </td>
                      <td className={tdCls}>
                        {exam.classroom || (
                          <span className="text-outline">{examsPage.noClassroom}</span>
                        )}
                      </td>
                      <td className={tdCls}>
                        <Chip
                          tone={
                            exam.status === 'CANCELLED'
                              ? 'danger'
                              : exam.status === 'CHANGED'
                                ? 'warning'
                                : 'primary'
                          }
                        >
                          {examStatusLabels[exam.status]}
                        </Chip>
                      </td>
                      <td className={tdCls}>
                        <span
                          className={`tnum ${days < 0 ? 'text-outline' : days <= 7 ? 'font-bold text-error' : 'text-on-surface-variant'}`}
                        >
                          {days < 0
                            ? examsPage.past
                            : days === 0
                              ? examsPage.today
                              : `${toPersianDigits(days)} ${examsPage.daysLeft}`}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <PaginationBar
            count={exams.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}
