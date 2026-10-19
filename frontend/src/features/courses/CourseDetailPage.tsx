/**
 * /courses/:id — course facts, its prerequisite chain, and every offering
 * (GET /courses/{id}/ + GET /course-offerings/?course=<id>).
 *
 * Schedule/exam cells render the nested detail payload of the offering, so
 * nothing here is fabricated — statuses map through i18n/labels.
 */

import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  cardCls,
  tableCls,
  tdCls,
  thCls,
  trCls,
} from '../../components/ui'
import { common, coursesPage } from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import { formatJalaliDate, formatTimeFa } from '../../i18n/jalali'
import { offeringStatusLabels } from '../../i18n/labels'
import type { CourseOffering } from '../../types/academic'

function ScheduleCell({ offering }: { offering: CourseOffering }) {
  const schedules = offering.schedules ?? []
  if (schedules.length === 0) {
    return <span className="text-outline">{coursesPage.noSchedule}</span>
  }
  return (
    <div className="flex flex-col gap-0.5 text-body-sm">
      {schedules.map((slot) => (
        <span key={slot.id} className="tnum">
          {slot.weekday_display} {slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}
          {slot.classroom ? ` | ${slot.classroom}` : ''}
        </span>
      ))}
    </div>
  )
}

function ExamCell({ offering }: { offering: CourseOffering }) {
  const exam = offering.exam
  if (!exam) {
    return <span className="text-outline">{coursesPage.noExam}</span>
  }
  return (
    <div className="flex flex-col gap-0.5 text-body-sm tnum">
      <span>{formatJalaliDate(exam.starts_at)}</span>
      <span className="text-on-surface-variant">
        {formatTimeFa(new Date(exam.starts_at))} – {formatTimeFa(new Date(exam.ends_at))}
      </span>
    </div>
  )
}

export function CourseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const courseId = Number(id)

  const course = useQuery({
    queryKey: queryKeys.course(courseId),
    queryFn: () => academicApi.course(courseId),
    enabled: Number.isFinite(courseId),
  })
  const offerings = useQuery({
    queryKey: queryKeys.offerings({ course: courseId }),
    queryFn: () => academicApi.offerings({ course: courseId, page_size: 50 }),
    enabled: Number.isFinite(courseId),
  })

  if (course.isPending) {
    return (
      <div className="px-gutter-desktop pt-space-lg">
        <LoadingState />
      </div>
    )
  }
  if (course.isError) {
    const status = (course.error as { status?: number }).status
    return (
      <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
        <ErrorState
          error={course.error}
          onRetry={status === 404 ? undefined : () => void course.refetch()}
        />
        <Link to="/courses" className="w-fit text-label-lg text-primary hover:underline">
          {coursesPage.title}
        </Link>
      </div>
    )
  }

  const data = course.data
  const rows = offerings.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <Link
        to="/courses"
        className="flex w-fit items-center gap-1 text-label-lg text-primary hover:underline"
      >
        <span className="material-symbols-outlined text-[18px]">chevron_right</span>
        {common.back}
      </Link>

      <PageHeader
        title={data.title}
        subtitle={`${coursesPage.courseCode}: ${data.code} — ${data.department.name}`}
        actions={
          <Chip tone="success">
            {toPersianDigits(data.credits)} {common.credits}
          </Chip>
        }
      />

      <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
        <section className={`${cardCls} flex flex-col gap-space-md p-space-lg lg:col-span-4`}>
          <h2 className="m-0 text-headline-md font-bold text-on-surface">
            {coursesPage.courseInfo}
          </h2>
          <dl className="m-0 flex flex-col gap-space-sm text-body-sm">
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">{coursesPage.department}</dt>
              <dd className="m-0 font-semibold text-on-surface">{data.department.name}</dd>
            </div>
            <div className="flex justify-between gap-space-sm border-b border-outline-variant pb-2">
              <dt className="text-on-surface-variant">{coursesPage.courseType}</dt>
              <dd className="m-0 font-semibold text-on-surface">
                {data.course_type || common.notSetFallback}
              </dd>
            </div>
            <div className="flex justify-between gap-space-sm">
              <dt className="text-on-surface-variant">{common.statusLabel}</dt>
              <dd className="m-0">
                <Chip tone={data.active ? 'success' : 'neutral'}>
                  {data.active ? coursesPage.active : coursesPage.inactive}
                </Chip>
              </dd>
            </div>
          </dl>

          <div className="flex flex-col gap-space-sm border-t border-outline-variant pt-space-sm">
            <span className="text-label-lg font-bold text-on-surface">
              {coursesPage.prerequisites}
            </span>
            {data.prerequisites.length === 0 ? (
              <span className="text-body-sm text-outline">{coursesPage.noPrerequisites}</span>
            ) : (
              <ul className="m-0 flex list-none flex-col gap-space-xs p-0">
                {data.prerequisites.map((prereq) => (
                  <li key={prereq.id} className="flex items-center gap-space-xs text-body-sm">
                    <span className="material-symbols-outlined text-[18px] text-secondary">
                      check_circle
                    </span>
                    <span className="tnum">{prereq.code}</span>
                    <span className="text-on-surface-variant">{prereq.title}</span>
                    <span className="text-outline tnum">({toPersianDigits(prereq.credits)})</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className={`${cardCls} flex flex-col gap-space-md p-space-lg lg:col-span-8`}>
          <h2 className="m-0 text-headline-md font-bold text-on-surface">
            {coursesPage.offerings}
          </h2>
          {offerings.isPending ? (
            <LoadingState />
          ) : offerings.isError ? (
            <ErrorState error={offerings.error} onRetry={() => void offerings.refetch()} />
          ) : rows.length === 0 ? (
            <EmptyState message={coursesPage.noOfferings} />
          ) : (
            <div className="overflow-x-auto">
              <table className={tableCls}>
                <thead>
                  <tr>
                    <th className={`${thCls} rounded-r-lg`}>{common.filterTerm}</th>
                    <th className={thCls}>{coursesPage.section}</th>
                    <th className={thCls}>{coursesPage.professor}</th>
                    <th className={thCls}>{coursesPage.schedule}</th>
                    <th className={thCls}>{coursesPage.exam}</th>
                    <th className={thCls}>{coursesPage.capacity}</th>
                    <th className={`${thCls} rounded-l-lg`}>{common.statusLabel}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((offering, index) => (
                    <tr key={offering.id} className={trCls(index)}>
                      <td className={`${tdCls} text-on-surface-variant`}>{offering.term.name}</td>
                      <td className={`${tdCls} tnum`}>{toPersianDigits(offering.section_code)}</td>
                      <td className={tdCls}>
                        {offering.professor?.full_name ?? coursesPage.noProfessor}
                      </td>
                      <td className={tdCls}>
                        <ScheduleCell offering={offering} />
                      </td>
                      <td className={tdCls}>
                        <ExamCell offering={offering} />
                      </td>
                      <td className={`${tdCls} tnum`}>
                        {toPersianDigits(offering.enrolled_count)} /{' '}
                        {toPersianDigits(offering.capacity)}
                      </td>
                      <td className={tdCls}>
                        <Chip
                          tone={
                            offering.status === 'OPEN'
                              ? 'success'
                              : offering.status === 'CANCELLED'
                                ? 'danger'
                                : 'neutral'
                          }
                        >
                          {offeringStatusLabels[offering.status]}
                        </Chip>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}