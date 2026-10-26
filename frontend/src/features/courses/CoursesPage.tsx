/**
 * /courses — the "Guide to Courses and Prerequisites" section.
 *
 * The mockup's lock/conflict indicators depend on the student's *passed-course
 * history*, which has no student-facing endpoint in Phase 04 (admin-managed),
 * so prerequisites render as factual chips instead of fabricated pass/fail
 * states — data comes from GET /courses/ only (docs/06 §8: no mock data).
 *
 * Filters map one-to-one to the documented query parameters
 * (docs/api/courses.md): `?search=`, `?department=`, `?credits=` and
 * `?course_type=`; page/filter state lives in the URL.
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
  SkeletonCards,
  btnSecondaryCls,
  cardCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { common, coursesPage } from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import type { ListQuery } from '../../types/academic'

const PAGE_SIZE = 12

const COURSE_TYPES = ['پایه', 'اصطلاحی', 'تخصصی الزامی', 'پروژه'] as const

export function CoursesPage() {
  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '', { debounce: 300 })
  const [credits, setCredits] = useUrlState<string>('credits', '')
  const [courseType, setCourseType] = useUrlState<string>('course_type', '')

  const query: ListQuery = {
    page,
    page_size: PAGE_SIZE,
    search: search.trim() || undefined,
    credits: credits ? Number(credits) : undefined,
    course_type: courseType || undefined,
  }
  const courses = useQuery({
    queryKey: queryKeys.courses(query),
    queryFn: () => academicApi.courses(query),
    placeholderData: (previous) => previous,
  })

  const hasFilters = Boolean(search.trim() || credits || courseType)
  const changeFilter = (setter: (value: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }
  const clearFilters = () => {
    setSearch('')
    setCredits('')
    setCourseType('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={coursesPage.title}
        subtitle={coursesPage.subtitle}
        actions={
          <SearchInput
            value={search}
            onChange={changeFilter(setSearch)}
            placeholder={coursesPage.searchPlaceholder}
            label={common.search}
          />
        }
      />

      <FilterRow>
        <FilterSelect
          icon="tag"
          label={coursesPage.credits}
          value={credits}
          onChange={changeFilter(setCredits)}
          className="w-40"
        >
          <option value="">{coursesPage.creditsAll}</option>
          {[1, 2, 3, 4].map((value) => (
            <option key={value} value={value}>
              {toPersianDigits(value)} {common.credits}
            </option>
          ))}
        </FilterSelect>

        <FilterSelect
          icon="label_important"
          label={coursesPage.courseType}
          value={courseType}
          onChange={changeFilter(setCourseType)}
          className="w-48"
        >
          <option value="">{coursesPage.courseTypeAll}</option>
          {COURSE_TYPES.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </FilterSelect>

        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}

        {courses.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {toPersianDigits(courses.data.count)} {coursesPage.resultsSummary}
          </span>
        ) : null}
      </FilterRow>

      {courses.isPending ? (
        <SkeletonCards />
      ) : courses.isError ? (
        <ErrorState error={courses.error} onRetry={() => void courses.refetch()} />
      ) : courses.data.results.length === 0 ? (
        <EmptyState
          message={coursesPage.empty}
          hint={coursesPage.emptyHint}
          action={
            hasFilters ? (
              <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
                {common.clearFilters}
              </button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-3">
            {courses.data.results.map((course) => (
              <Link
                key={course.id}
                to={`/courses/${course.id}`}
                className={`${cardCls} group flex flex-col gap-space-sm p-space-lg transition-all hover:shadow-md`}
              >
                <div className="flex items-start justify-between gap-space-sm">
                  <div className="flex flex-col gap-1">
                    <span className="text-label-sm text-on-surface-variant tnum">
                      {coursesPage.courseCode}: {course.code}
                    </span>
                    <span className="text-headline-sm font-bold text-on-surface group-hover:text-primary">
                      {course.title}
                    </span>
                  </div>
                  <span className="material-symbols-outlined text-[22px] text-outline transition-colors group-hover:text-primary">
                    chevron_left
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-space-xs">
                  <Chip tone="success">
                    {toPersianDigits(course.credits)} {common.credits}
                  </Chip>
                  {course.course_type ? <Chip>{course.course_type}</Chip> : null}
                  <Chip tone={course.active ? 'primary' : 'neutral'}>
                    {course.active ? coursesPage.active : coursesPage.inactive}
                  </Chip>
                </div>

                <div className="mt-auto flex flex-col gap-space-xs border-t border-outline-variant pt-space-sm">
                  <span className="text-label-sm font-bold text-on-surface-variant">
                    {coursesPage.prerequisites}
                  </span>
                  {course.prerequisites.length === 0 ? (
                    <span className="text-body-sm text-outline">
                      {coursesPage.noPrerequisites}
                    </span>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {course.prerequisites.map((prereq) => (
                        <span
                          key={prereq.id}
                          className="rounded-full bg-surface-container-high px-space-sm py-0.5 text-label-sm text-on-surface-variant tnum"
                        >
                          {prereq.code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
          <PaginationBar
            count={courses.data.count}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}
