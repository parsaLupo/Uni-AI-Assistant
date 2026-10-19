/**
 * /courses — the "Guide to Courses and Prerequisites" section.
 *
 * The mockup's lock/conflict indicators depend on the student's *passed-course
 * history*, which has no student-facing endpoint in Phase 04 (admin-managed),
 * so prerequisites render as factual chips instead of fabricated pass/fail
 * states — data comes from GET /courses/ only (docs/06 §8: no mock data).
 */

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
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
  inputCls,
} from '../../components/ui'
import { common, coursesPage } from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import type { ListQuery } from '../../types/academic'

const PAGE_SIZE = 12

export function CoursesPage() {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const query: ListQuery = { page, page_size: PAGE_SIZE, search: debounced || undefined }
  const courses = useQuery({
    queryKey: queryKeys.courses(query),
    queryFn: () => academicApi.courses(query),
    placeholderData: (previous) => previous,
  })

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={coursesPage.title}
        subtitle={coursesPage.subtitle}
        actions={
          <div className="relative w-full max-w-sm">
            <span className="material-symbols-outlined pointer-events-none absolute inset-y-0 right-3 my-auto text-[20px] text-outline">
              search
            </span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={coursesPage.searchPlaceholder}
              aria-label={common.search}
              className={`${inputCls} pr-10`}
            />
          </div>
        }
      />

      {courses.isPending ? (
        <LoadingState />
      ) : courses.isError ? (
        <ErrorState error={courses.error} onRetry={() => void courses.refetch()} />
      ) : courses.data.results.length === 0 ? (
        <EmptyState message={coursesPage.empty} />
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
                    <span className="text-body-sm text-outline">{coursesPage.noPrerequisites}</span>
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