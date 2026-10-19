/** /exams — current-term exam schedule (GET /exams/?term=current). */

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
  tableCls,
  tdCls,
  thCls,
  trCls,
} from '../../components/ui'
import { common, examsPage } from '../../i18n/fa'
import { daysUntil, formatJalaliDate, formatTimeFa } from '../../i18n/jalali'
import { examStatusLabels } from '../../i18n/labels'
import type { ListQuery } from '../../types/academic'

const PAGE_SIZE = 25

export function ExamsPage() {
  const [term, setTerm] = useState<'current' | 'all'>('current')
  const [page, setPage] = useState(1)

  const query: ListQuery = {
    term: term === 'current' ? 'current' : undefined,
    page,
    page_size: PAGE_SIZE,
  }
  const exams = useQuery({
    queryKey: queryKeys.exams(query),
    queryFn: () => academicApi.exams(query),
    placeholderData: (previous) => previous,
  })

  const rows = exams.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={examsPage.title}
        subtitle={examsPage.subtitle}
        actions={
          <select
            value={term}
            onChange={(event) => {
              setTerm(event.target.value as 'current' | 'all')
              setPage(1)
            }}
            aria-label={common.filterTerm}
            className="rounded-xl border border-[#CBD5E1] bg-white px-space-sm py-2 text-body-sm text-[#0F172A] focus:border-[#2563EB] focus:outline-none"
          >
            <option value="current">{common.filterCurrent}</option>
            <option value="all">{common.filterAll}</option>
          </select>
        }
      />

      {exams.isPending ? (
        <LoadingState />
      ) : exams.isError ? (
        <ErrorState error={exams.error} onRetry={() => void exams.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={examsPage.empty} />
      ) : (
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
                      {exam.course_offering.course_title} (
                      <span className="tnum">{exam.course_offering.course_code}</span>)
                      <span className="block text-label-sm text-on-surface-variant tnum">
                        {common.filterTerm} {exam.course_offering.section_code}
                      </span>
                    </td>
                    <td className={`${tdCls} tnum`}>{formatJalaliDate(exam.starts_at)}</td>
                    <td className={`${tdCls} tnum`}>
                      {formatTimeFa(new Date(exam.starts_at))} –{' '}
                      {formatTimeFa(new Date(exam.ends_at))}
                    </td>
                    <td className={tdCls}>
                      {exam.classroom || <span className="text-outline">{examsPage.noClassroom}</span>}
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
                            : `${days} ${examsPage.daysLeft}`}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}