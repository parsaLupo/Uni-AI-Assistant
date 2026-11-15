/**
 * /dashboard — the student home from UI/Dashboard.html, wired to real data.
 *
 * Mockup → API mapping (no mock data in a production path — docs/06 §8):
 *   banner term badge  ← /terms/ (is_current)      student line/GPA ← /students/me/
 *   metric cards       ← /students/planner/ + /exams/?term=current
 *   schedule + table   ← /students/planner/ schedules
 *   announcements      ← /announcements/
 * The mockup's "passed credits ring" has no student-facing API in Phase 04
 * (history is admin-managed), so that tile degrades to GPA + term number
 * instead of inventing numbers.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  LoadingState,
  cardCls,
  tableCls,
  tdCls,
  thCls,
  trCls,
} from '../../components/ui'
import { useAuth } from '../auth'
import {
  announcementsPage,
  common,
  coursesPage,
  dashboard,
  examsPage,
} from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import {
  daysUntil,
  formatJalaliDate,
  formatJalaliShort,
  formatTimeFa,
  weekdayFa,
} from '../../i18n/jalali'
import { degreeLevelLabels, priorityLabels, semesterLabels } from '../../i18n/labels'
import type { Announcement, Exam } from '../../types/academic'
import { examRowsFromPlanner, todaySessions } from './schedule'

const PAGE_SIZE = 50

function useDashboardData(enabled: boolean) {
  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms(),
  })
  const profile = useQuery({
    queryKey: queryKeys.studentProfile(),
    queryFn: academicApi.studentProfile,
    enabled,
  })
  const planner = useQuery({
    queryKey: queryKeys.planner(),
    queryFn: () => academicApi.planner(),
    enabled,
  })
  const exams = useQuery({
    queryKey: queryKeys.exams({ term: 'current' }),
    queryFn: () => academicApi.exams({ term: 'current', page_size: PAGE_SIZE }),
  })
  const announcements = useQuery({
    queryKey: queryKeys.announcements({ page_size: 6 }),
    queryFn: () => academicApi.announcements({ page_size: 6 }),
  })
  return { terms, profile, planner, exams, announcements }
}

function WelcomeBanner({
  name,
  termLabel,
  termMeta,
  studentLine,
  gpa,
  termNumber,
}: {
  name: string
  termLabel: string | null
  termMeta: string | null
  studentLine: string | null
  gpa: string | null
  termNumber: number | null
}) {
  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-l from-primary-container via-primary to-primary p-space-lg text-on-primary shadow-xl lg:p-space-xl">
      <div className="pointer-events-none absolute -top-24 -left-24 h-96 w-96 rounded-full bg-secondary-container/10 blur-3xl" />
      <div className="relative z-10 flex flex-col items-start gap-space-lg lg:flex-row lg:items-center lg:justify-between">
        <div className="flex max-w-2xl flex-col gap-space-xs">
          <div className="flex flex-wrap items-center gap-space-xs">
            <span className="flex items-center gap-1 rounded-full bg-secondary-container px-space-sm py-1 text-label-sm font-semibold text-on-secondary-container">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-secondary" />
              {termLabel ? dashboard.currentTermActive : dashboard.noTerm}
            </span>
            {termMeta ? (
              <span className="text-label-md text-on-primary-container">{termMeta}</span>
            ) : null}
          </div>
          <h1 className="m-0 mt-space-xs text-headline-xl font-bold text-on-primary">
            {dashboard.welcome}، {name}
          </h1>
          {studentLine ? (
            <p className="m-0 text-body-md leading-relaxed text-on-primary-container">
              {studentLine}
            </p>
          ) : null}
        </div>

        {(gpa || termNumber) && (
          <div className="flex w-full items-center gap-space-md rounded-xl bg-surface-container-lowest/10 p-space-md backdrop-blur-md shadow-sm lg:w-auto">
            <div className="flex flex-col gap-1">
              <div className="flex items-baseline gap-1.5">
                <span className="text-label-sm text-on-primary-container">{dashboard.gpa}:</span>
                <span className="text-headline-md font-bold text-secondary-fixed tnum">
                  {gpa ? toPersianDigits(gpa) : dashboard.notAvailable}
                </span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-label-sm text-on-primary-container">
                  {dashboard.currentTermNumber}:
                </span>
                <span className="text-label-lg font-bold text-on-primary tnum">
                  {termNumber ? toPersianDigits(termNumber) : dashboard.notAvailable}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** One bento metric card from the mockup (label, big value, icon, footer strip). */
function MetricCard({
  label,
  value,
  unit,
  icon,
  iconTone,
  footer,
}: {
  label: string
  value: string | number
  unit?: string
  icon: string
  iconTone?: 'primary' | 'secondary' | 'danger'
  footer?: { text: string; tone?: 'muted' | 'success' | 'danger' }
}) {
  const iconTones = {
    primary: 'bg-surface-container-high text-primary group-hover:bg-primary group-hover:text-on-primary',
    secondary: 'bg-secondary-container/40 text-on-secondary-container group-hover:bg-secondary group-hover:text-on-secondary',
    danger: 'bg-error-container/60 text-on-error-container',
  }
  const footTones = {
    muted: 'bg-surface-container-low text-on-surface-variant',
    success: 'bg-secondary-container/20 text-on-secondary-container',
    danger: 'bg-error-container/40 text-on-error-container',
  }
  return (
    <div
      className={`${cardCls} flex flex-col justify-between p-space-md transition-all group hover:shadow-md`}
    >
      <div className="flex items-start justify-between gap-space-sm">
        <div className="flex flex-col">
          <span className="text-label-sm text-on-surface-variant">{label}</span>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="tnum text-headline-xl font-bold text-primary">{value}</span>
            {unit ? (
              <span className="text-label-md font-normal text-on-surface-variant">{unit}</span>
            ) : null}
          </div>
        </div>
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors ${iconTones[iconTone ?? 'primary']}`}
        >
          <span className="material-symbols-outlined text-[22px]">{icon}</span>
        </div>
      </div>
      {footer ? (
        <div
          className={`mt-space-sm flex items-center justify-between rounded-lg px-space-sm py-1 text-label-sm ${footTones[footer.tone ?? 'muted']}`}
        >
          <span className="tnum">{footer.text}</span>
        </div>
      ) : null}
    </div>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const isStudent = user?.role === 'STUDENT'
  const { terms, profile, planner, exams, announcements } = useDashboardData(isStudent)

  const currentTerm = terms.data?.results.find((term) => term.is_current) ?? null
  const student = profile.data ?? null
  const plannerItems = planner.data ?? []
  const examRows = exams.data?.results ?? []
  const announcementRows = announcements.data?.results ?? []

  const name = user ? `${user.first_name} ${user.last_name}`.trim() || user.email : ''
  const studentLine = student
    ? [
        `${dashboard.studentNumber}: ${toPersianDigits(student.student_number ?? '—')}`,
        student.faculty?.name ?? dashboard.notSet,
        student.degree_level ? degreeLevelLabels[student.degree_level] : dashboard.notSet,
      ].join(' • ')
    : null

  const enrolledCredits = plannerItems.reduce((sum, item) => sum + item.total_credits, 0)
  // Students read both sections from their own current-term planner rows
  // (today's sessions + announced/missing exams). Non-students keep the
  // public exam feed.
  const sessions = isStudent ? todaySessions(plannerItems, new Date()) : []
  const plannerExamRows = isStudent ? examRowsFromPlanner(plannerItems) : []
  const examViewRows: ExamViewRow[] = isStudent
    ? plannerExamRows.map((row) => ({
        itemKey: row.item.id,
        exam: row.exam,
        courseTitle: row.item.course_offering.course.title,
        section: row.item.course_offering.section_code,
        termName: row.item.course_offering.term.name,
      }))
    : examRows.map((exam) => ({
        itemKey: exam.id,
        exam,
        courseTitle: exam.course_offering.course_title,
        section: exam.course_offering.section_code,
        termName: exam.course_offering.term.name,
      }))
  const nextExam = examViewRows.find(
    (row): row is ExamViewRow & { exam: Exam } =>
      row.exam !== null && daysUntil(row.exam.starts_at) >= 0,
  )
  const upcomingExams = examViewRows.filter(
    (row) => row.exam && daysUntil(row.exam.starts_at) >= 0,
  )

  const loading = terms.isPending || (isStudent && (profile.isPending || planner.isPending))

  if (loading) {
    return (
      <div className="px-gutter-desktop pt-space-lg">
        <LoadingState />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      {terms.isError ? <ErrorState error={terms.error} onRetry={() => void terms.refetch()} /> : null}

      <WelcomeBanner
        name={name}
        termLabel={currentTerm ? currentTerm.name : null}
        termMeta={
          currentTerm
            ? `${semesterLabels[currentTerm.semester_type]} ${toPersianDigits(currentTerm.academic_year)}`
            : null
        }
        studentLine={studentLine}
        gpa={student?.current_gpa ?? null}
        termNumber={student?.current_term_number ?? null}
      />

      {student && !student.onboarding_complete ? (
        <div className="flex items-center justify-between gap-space-md rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md">
          <div className="flex items-center gap-space-sm text-[#92400E]">
            <span className="material-symbols-outlined text-[20px]">warning</span>
            <span className="text-body-sm">{dashboard.profileIncomplete}</span>
          </div>
          <Link
            to="/profile"
            className="rounded-lg bg-[#B45309] px-space-md py-1.5 text-label-md font-semibold text-white transition-colors hover:bg-[#92400E]"
          >
            {dashboard.completeProfile}
          </Link>
        </div>
      ) : null}

      {isStudent ? (
        <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label={dashboard.enrolledCredits}
            value={toPersianDigits(enrolledCredits)}
            unit={common.credits}
            icon="menu_book"
            footer={{ text: dashboard.creditCap }}
          />
          <MetricCard
            label={dashboard.todayClasses}
            value={toPersianDigits(sessions.length)}
            unit={dashboard.todaySessions}
            icon="meeting_room"
            iconTone="secondary"
            footer={{
              text:
                sessions.length > 0
                  ? (sessions[0].schedule.classroom || dashboard.noTodayClasses).slice(0, 40)
                  : dashboard.noTodayClasses,
              tone: sessions.length > 0 ? 'success' : 'muted',
            }}
          />
          <MetricCard
            label={dashboard.upcomingExams}
            value={toPersianDigits(upcomingExams.length)}
            unit={dashboard.examCountUnit}
            icon="assignment_turned_in"
            footer={{
              text: nextExam
                ? `${toPersianDigits(daysUntil(nextExam.exam.starts_at))} ${dashboard.daysLeft}`
                : dashboard.noExams,
              tone: nextExam ? 'danger' : 'muted',
            }}
          />
          <MetricCard
            label={dashboard.academicStatus}
            value={student?.onboarding_complete ? dashboard.statusNormal : dashboard.statusNotSet}
            icon="verified_user"
            iconTone="secondary"
            footer={{
              text: student?.onboarding_complete
                ? 'مجاز به انتخاب واحد و فراغت'
                : dashboard.completeProfile,
              tone: student?.onboarding_complete ? 'success' : 'muted',
            }}
          />
        </div>
      ) : null}

      {/* Interactive AI Knowledge Assistant banner (mockup section 3). */}
      <div className="rounded-xl bg-gradient-to-r from-surface-container-high via-surface-container to-surface-container-high p-space-md shadow-sm lg:p-space-lg">
        <div className="flex flex-col items-start justify-between gap-space-md md:flex-row md:items-center">
          <div className="flex items-center gap-space-md">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary shadow-sm">
              <span className="material-symbols-outlined text-[26px]">psychology</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <div className="flex flex-wrap items-center gap-space-xs">
                <span className="text-headline-sm font-bold text-primary">
                  {dashboard.assistantBannerTitle}
                </span>
                <span className="rounded bg-secondary-container px-1 py-0.5 text-label-sm text-on-secondary-container">
                  {currentTerm
                    ? `RAG ${toPersianDigits(currentTerm.academic_year.split('-')[0])}`
                    : 'RAG'}
                </span>
              </div>
              <p className="m-0 text-body-md text-on-surface-variant">
                {dashboard.assistantBannerBody}
              </p>
            </div>
          </div>
          <Link
            to="/assistant"
            className="flex w-full items-center justify-center gap-space-xs rounded bg-primary px-space-lg py-space-sm text-label-lg font-semibold text-on-primary shadow-sm transition-all hover:bg-primary-container active:scale-95 md:w-auto"
          >
            <span className="material-symbols-outlined text-[20px]">smart_toy</span>
            {dashboard.assistantBannerAction}
          </Link>
        </div>
      </div>

      {/* Two-column body: today schedule + courses table | exams + announcements. */}
      <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
        <div className="flex flex-col gap-space-md lg:col-span-7">
          <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
            <div className="flex items-center justify-between">
              <h2 className="m-0 text-headline-md font-bold text-on-surface">
                {dashboard.todaySchedule}
              </h2>
              <Chip tone="primary">{weekdayFa(new Date())}</Chip>
            </div>
            {sessions.length === 0 ? (
              <EmptyState message={dashboard.noTodayClasses} />
            ) : (
              <div className="flex flex-col gap-space-sm">
                {sessions.map(({ item, schedule }) => (
                  <div
                    key={schedule.id}
                    className="flex items-center justify-between gap-space-sm rounded-xl bg-surface-container-low p-space-md transition-all hover:shadow-sm"
                  >
                    <div className="flex items-center gap-space-sm">
                      <div className="flex min-w-[70px] flex-col items-center justify-center rounded-lg bg-primary-container px-space-sm py-space-xs text-on-primary">
                        <span className="text-label-lg font-bold tnum">
                          {formatTimeFa(schedule.start_time)}
                        </span>
                        <span className="text-label-sm text-on-primary-container tnum">
                          {formatTimeFa(schedule.end_time)}
                        </span>
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <div className="flex flex-wrap items-center gap-space-xs">
                          <span className="text-headline-sm font-bold text-on-surface">
                            {item.course_offering.course.title}
                          </span>
                          <Chip tone="success">
                            {toPersianDigits(item.course_offering.course.credits)} {common.credits}
                          </Chip>
                        </div>
                        <span className="text-body-sm text-on-surface-variant">
                          {item.course_offering.professor?.full_name ?? coursesPage.noProfessor}
                        </span>
                        {schedule.classroom ? (
                          <span className="mt-1 flex items-center gap-1 text-label-sm text-outline">
                            <span className="material-symbols-outlined text-[16px]">
                              location_on
                            </span>
                            {schedule.classroom}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <Chip tone="neutral">
                      گروه {toPersianDigits(item.course_offering.section_code)}
                    </Chip>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Enrolled courses table */}
          <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
            <h2 className="m-0 text-headline-md font-bold text-on-surface">
              {dashboard.enrolledTableTitle}
            </h2>
            {plannerItems.length === 0 ? (
              <EmptyState message={dashboard.plannerEmpty} />
            ) : (
              <div className="overflow-x-auto">
                <table className={tableCls}>
                  <thead>
                    <tr>
                      <th className={`${thCls} rounded-r-lg`}>{dashboard.colCourse}</th>
                      <th className={thCls}>{dashboard.colCredits}</th>
                      <th className={thCls}>{dashboard.colProfessor}</th>
                      <th className={thCls}>{dashboard.colSection}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plannerItems.map((item, index) => (
                      <tr key={item.id} className={trCls(index)}>
                        <td className={`${tdCls} font-semibold text-on-surface`}>
                          {item.course_offering.course.title} (
                          <span className="tnum">{item.course_offering.course.code}</span>)
                        </td>
                        <td className={`${tdCls} tnum`}>
                          {toPersianDigits(item.course_offering.course.credits)}
                        </td>
                        <td className={`${tdCls} text-on-surface-variant`}>
                          {item.course_offering.professor?.full_name ?? coursesPage.noProfessor}
                        </td>
                        <td className={tdCls}>
                          <Chip>{toPersianDigits(item.course_offering.section_code)}</Chip>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        {/* Left column: exams countdown + announcements */}
        <div className="flex flex-col gap-space-md lg:col-span-5">
          <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[24px] text-primary">
                  event_upcoming
                </span>
                <h2 className="m-0 text-headline-lg font-bold text-on-surface">
                  {dashboard.examsTitle}
                </h2>
              </div>
              {currentTerm ? (
                <Chip tone="primary">{toPersianDigits(currentTerm.academic_year)}</Chip>
              ) : null}
            </div>
            {!isStudent && exams.isError ? (
              <ErrorState error={exams.error} onRetry={() => void exams.refetch()} />
            ) : isStudent && planner.isError ? (
              <ErrorState error={planner.error} onRetry={() => void planner.refetch()} />
            ) : examViewRows.length === 0 ? (
              <EmptyState message={dashboard.noExams} />
            ) : (
              <div className="flex flex-col gap-space-sm">
                {examViewRows.map((row) => (
                  <ExamRow key={row.itemKey} row={row} />
                ))}
              </div>
            )}
          </section>

          <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[24px] text-primary">campaign</span>
                <h2 className="m-0 text-headline-md font-bold text-on-surface">
                  {dashboard.announcementsTitle}
                </h2>
              </div>
              <Link
                to="/announcements"
                className="flex items-center gap-1 text-label-md text-primary hover:underline"
              >
                {common.viewDetails}
                <span className="material-symbols-outlined text-[16px]">chevron_left</span>
              </Link>
            </div>
            {announcements.isError ? (
              <ErrorState error={announcements.error} onRetry={() => void announcements.refetch()} />
            ) : announcementRows.length === 0 ? (
              <EmptyState message={announcementsPage.empty} />
            ) : (
              <div className="flex flex-col gap-space-sm">
                {announcementRows.slice(0, 4).map((row, index) => (
                  <AnnouncementRow key={row.id} row={row} index={index} />
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

/* ── Row helpers ──────────────────────────────────────────────────────── */

/** One final-exam row: an imported exam or an unannounced-date offering. */
interface ExamViewRow {
  itemKey: number
  exam: Exam | null
  courseTitle: string
  section: string
  termName: string
}

function ExamRow({ row }: { row: ExamViewRow }) {
  const exam = row.exam
  if (!exam) {
    // Real offering of the student's current term with no imported exam —
    // state it honestly instead of inventing a date (docs/06 §8).
    return (
      <div className="flex items-center justify-between gap-space-sm rounded-xl bg-surface-container-low p-space-md transition-all hover:shadow-sm">
        <div className="flex items-center gap-space-sm">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-container-high text-on-surface-variant">
            <span className="material-symbols-outlined text-[20px]">event_busy</span>
          </div>
          <div className="flex flex-col">
            <span className="text-label-lg font-bold text-on-surface">{row.courseTitle}</span>
            <span className="text-label-sm text-on-surface-variant">{row.termName}</span>
          </div>
        </div>
        <Chip tone="neutral">{dashboard.examNotAnnounced}</Chip>
      </div>
    )
  }
  const days = daysUntil(exam.starts_at)
  const short = formatJalaliShort(exam.starts_at).split(' ')
  return (
    <div className="flex items-center justify-between gap-space-sm rounded-xl bg-surface-container-low p-space-md transition-all hover:shadow-sm">
      <div className="flex items-center gap-space-sm">
        <div className="flex h-10 w-10 shrink-0 flex-col items-center justify-center rounded-xl bg-error-container/60 text-on-error-container">
          <span className="text-label-sm font-bold leading-none tnum">{short[0]}</span>
          <span className="text-[10px] leading-tight">{short[1]}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-label-lg font-bold text-on-surface">{row.courseTitle}</span>
          <span className="text-label-sm text-on-surface-variant tnum">
            {formatJalaliDate(exam.starts_at)} — {formatTimeFa(new Date(exam.starts_at))} تا{' '}
            {formatTimeFa(new Date(exam.ends_at))}
          </span>
          {exam.classroom ? (
            <span className="flex items-center gap-1 text-label-sm text-on-surface-variant">
              <span className="material-symbols-outlined text-[14px]">location_on</span>
              {exam.classroom}
            </span>
          ) : null}
          <span className="text-label-sm text-on-surface-variant tnum">{row.termName}</span>
        </div>
      </div>
      <span
        className={`text-label-sm font-bold tnum ${days <= 7 && days >= 0 ? 'text-error' : 'text-on-surface-variant'}`}
      >
        {days < 0
          ? examsPage.past
          : days === 0
            ? examsPage.today
            : `${toPersianDigits(days)} ${dashboard.daysLeft}`}
      </span>
    </div>
  )
}

function AnnouncementRow({ row, index }: { row: Announcement; index: number }) {
  const tone = row.priority === 'HIGH' || row.priority === 'URGENT' ? 'warning' : 'primary'
  return (
    <div
      className={`flex flex-col gap-space-xs rounded-lg border border-outline-variant p-space-sm ${index % 2 === 1 ? 'bg-surface-container-low/40' : 'bg-surface-container-lowest'}`}
    >
      <div className="flex items-center justify-between gap-space-sm">
        <span className="text-label-lg font-bold text-on-surface">{row.title}</span>
        <Chip tone={tone}>{priorityLabels[row.priority]}</Chip>
      </div>
      <p className="m-0 line-clamp-2 text-body-sm text-on-surface-variant">{row.body}</p>
      {row.published_at ? (
        <span className="text-label-sm text-outline tnum">
          {announcementsPage.publishedAt}: {formatJalaliDate(row.published_at)}
        </span>
      ) : null}
    </div>
  )
}