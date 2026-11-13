/**
 * /admin — administrator overview.
 *
 * UI refinement: the admin rail now carries only the overview + the shared
 * AI assistant, so this page is the administrator's single home screen. It
 * follows the student dashboard's visual language (navy welcome banner,
 * bento metric cards, section cards) while every value comes from real
 * endpoints only — no mock or hardcoded statistics (docs/06 §8):
 *
 *   welcome banner     ← auth session + GET /admin/analytics/dashboard
 *   metric cards       ← analytics dashboard + list `count`s (page_size=1)
 *                        + documents list count (status=ACTIVE)
 *   system status      ← GET /health/
 *   AI statistics      ← analytics dashboard (aggregate-only fields)
 *   mode distribution  ← analytics dashboard.topic_distribution
 *   recent admin acts  ← GET /admin/analytics/audit-log/ (page_size=5)
 *   warnings           ← documents list count (status=FAILED) + health check
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  fetchAdminAuditLog,
  fetchAdminDashboard,
  listAdminDocuments,
  type AuditLogRow,
} from '../../api/admin'
import { fetchHealth } from '../../api/health'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  ErrorState,
  SkeletonRows,
  cardCls,
  tableCls,
  tdCls,
  thCls,
  trCls,
} from '../../components/ui'
import { toPersianDigits } from '../../i18n/digits'
import { formatJalaliDate } from '../../i18n/jalali'
import { executionModeLabels } from '../../i18n/labels'
import { adminPage, common } from '../../i18n/fa'
import { useAuth } from '../auth'
import { ADMIN_LINKS } from './links'

type AdminDashboard = Awaited<ReturnType<typeof fetchAdminDashboard>>
type HealthStatus = Awaited<ReturnType<typeof fetchHealth>>

/* ── Welcome banner (student-dashboard visual language) ──────────────── */

function AdminWelcomeBanner({ name, analytics, health }: {
  name: string
  analytics: { data?: AdminDashboard; isPending: boolean }
  health: { data?: HealthStatus; isPending: boolean; isError: boolean }
}) {
  const dbOk = health.data ? health.data.checks.database === 'ok' : null
  const statusLabel = health.isPending
    ? adminPage.systemStatus
    : health.isError || dbOk === false
      ? adminPage.systemIssue
      : adminPage.systemActive

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-l from-primary-container via-primary to-primary p-space-lg text-on-primary shadow-xl lg:p-space-xl">
      <div className="pointer-events-none absolute -top-24 -left-24 h-96 w-96 rounded-full bg-secondary-container/10 blur-3xl" />
      <div className="relative z-10 flex flex-col items-start gap-space-lg lg:flex-row lg:items-center lg:justify-between">
        <div className="flex max-w-2xl flex-col gap-space-xs">
          <div className="flex flex-wrap items-center gap-space-xs">
            <span className="flex items-center gap-1 rounded-full bg-secondary-container px-space-sm py-1 text-label-sm font-semibold text-on-secondary-container">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  health.isError || dbOk === false
                    ? 'bg-error'
                    : 'animate-pulse bg-secondary motion-reduce:animate-none'
                }`}
              />
              {statusLabel}
            </span>
          </div>
          <h1 className="m-0 mt-space-xs text-headline-xl font-bold text-on-primary">
            {adminPage.welcome}، {name}
          </h1>
          <p className="m-0 text-body-md leading-relaxed text-on-primary-container">
            {adminPage.overviewSubtitle}
          </p>
        </div>

        {/* Two mini totals mirror the student banner's stat block. */}
        <div className="flex w-full items-center gap-space-md rounded-xl bg-surface-container-lowest/10 p-space-md backdrop-blur-md shadow-sm lg:w-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-baseline gap-1.5">
              <span className="text-label-sm text-on-primary-container">
                {adminPage.aiRequests}:
              </span>
              <span className="text-headline-md font-bold text-secondary-fixed tnum">
                {analytics.isPending || !analytics.data ? (
                  '…'
                ) : (
                  toPersianDigits(analytics.data.ai.total_requests)
                )}
              </span>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-label-sm text-on-primary-container">
                {adminPage.documentsTotal}:
              </span>
              <span className="text-label-lg font-bold text-on-primary tnum">
                {analytics.isPending || !analytics.data ? (
                  '…'
                ) : (
                  toPersianDigits(analytics.data.documents_total)
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Bento metric card (same classes as the student dashboard's) ─────── */

function MetricCard({ label, value, unit, icon, iconTone, footer }: {
  label: string
  value: string | number
  unit?: string
  icon: string
  iconTone?: 'primary' | 'secondary' | 'danger'
  footer?: { text: string; tone?: 'muted' | 'success' | 'danger' }
}) {
  const iconTones = {
    primary: 'bg-surface-container-high text-primary',
    secondary: 'bg-secondary-container/40 text-on-secondary-container',
    danger: 'bg-error-container/60 text-on-error-container',
  }
  const footTones = {
    muted: 'bg-surface-container-low text-on-surface-variant',
    success: 'bg-secondary-container/20 text-on-secondary-container',
    danger: 'bg-error-container/40 text-on-error-container',
  }
  return (
    <div className={`${cardCls} flex flex-col justify-between p-space-md`}>
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
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconTones[iconTone ?? 'primary']}`}
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

/** Count card backed by a paginated admin list endpoint (`count`). */
function ListCountCard({ label, icon, query, queryFn, footer }: {
  label: string
  icon: string
  query: Record<string, unknown>
  queryFn: () => Promise<number>
  footer?: { text: string; tone?: 'muted' | 'success' | 'danger' }
}) {
  const count = useQuery({ queryKey: Object.values(query), queryFn })
  return (
    <MetricCard
      label={label}
      icon={icon}
      value={count.isPending ? '…' : count.isError ? '—' : toPersianDigits(count.data)}
      footer={footer}
    />
  )
}

/* ── AI statistics + mode distribution ───────────────────────────────── */

function AiStatsCard({ analytics }: { analytics: AdminDashboard }) {
  const stats: Array<{ label: string; value: number; hint?: string }> = [
    { label: adminPage.aiRequests, value: analytics.ai.total_requests },
    { label: adminPage.answersTotal, value: analytics.questions.answers },
    { label: adminPage.insufficientEvidence, value: analytics.questions.insufficient_evidence },
    { label: adminPage.errorsShort, value: analytics.ai.error_count },
  ]
  return (
    <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
      <div className="flex items-center justify-between">
        <h2 className="m-0 text-headline-md font-bold text-on-surface">{adminPage.aiRequests}</h2>
        <Chip tone={analytics.ai.error_count > 0 ? 'warning' : 'success'}>
          {adminPage.avgLatency}: {analytics.ai.avg_latency_ms === null ? '—' : toPersianDigits(analytics.ai.avg_latency_ms)}
        </Chip>
      </div>
      <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="flex flex-col gap-0.5 rounded-lg bg-surface-container-low px-space-sm py-space-xs">
            <span className="text-label-sm text-on-surface-variant">{stat.label}</span>
            <span className="tnum text-headline-md font-bold text-on-surface">
              {toPersianDigits(stat.value)}
            </span>
          </div>
        ))}
      </div>
      <h3 className="m-0 text-headline-sm font-bold text-on-surface">
        {adminPage.topicDistribution}
      </h3>
      {analytics.topic_distribution.length === 0 ? (
        <p className="m-0 text-body-sm text-on-surface-variant">{common.empty}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
          {analytics.topic_distribution.map((row) => (
            <li key={row.mode} className="flex items-center justify-between gap-space-sm">
              <span className="text-body-md text-on-surface">
                {executionModeLabels[row.mode] ?? row.mode}
              </span>
              <span className="text-body-md font-bold text-primary tnum">
                {toPersianDigits(row.count)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/* ── System status (GET /health/ only) ───────────────────────────────── */

function SystemStatusCard({ health }: { health: { data?: HealthStatus; isPending: boolean; isError: boolean } }) {
  if (health.isPending) {
    return (
      <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
        <h2 className="m-0 text-headline-md font-bold text-on-surface">{adminPage.systemStatus}</h2>
        <SkeletonRows count={3} />
      </section>
    )
  }
  const rows: Array<{ label: string; value: string; tone: 'success' | 'warning' | 'danger' | 'neutral' }> =
    health.isError || !health.data
      ? [{ label: adminPage.serviceStatusLabel, value: adminPage.databaseUnavailable, tone: 'danger' }]
      : [
          {
            label: adminPage.serviceStatusLabel,
            value: adminPage.databaseOk,
            tone: 'success',
          },
          {
            label: adminPage.databaseLabel,
            value:
              health.data.checks.database === 'ok'
                ? `${adminPage.databaseOk}${
                    health.data.checks.database_latency_ms === null
                      ? ''
                      : ` — ${toPersianDigits(health.data.checks.database_latency_ms)} ${adminPage.dbLatencyMs}`
                  }`
                : adminPage.databaseUnavailable,
            tone: health.data.checks.database === 'ok' ? 'success' : 'danger',
          },
          {
            label: adminPage.aiProviderLabel,
            value:
              health.data.checks.ai_provider === 'not_configured'
                ? adminPage.aiProviderNotConfigured
                : health.data.checks.ai_provider,
            tone: health.data.checks.ai_provider === 'not_configured' ? 'neutral' : 'success',
          },
        ]
  return (
    <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
      <h2 className="m-0 text-headline-md font-bold text-on-surface">{adminPage.systemStatus}</h2>
      <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-space-sm">
            <span className="text-body-md text-on-surface-variant">{row.label}</span>
            <Chip tone={row.tone}>{row.value}</Chip>
          </li>
        ))}
      </ul>
    </section>
  )
}

/* ── Recent administrative activities (audit log, page 1) ────────────── */

function ActionChip({ action }: { action: AuditLogRow['action'] }) {
  const tone =
    action === 'CREATE' ? 'success' : action === 'DELETE' ? 'danger' : action === 'UPDATE' ? 'primary' : 'neutral'
  return <Chip tone={tone}>{action}</Chip>
}

function RecentActivitiesCard() {
  const query = { page: 1, page_size: 5 }
  const audit = useQuery({
    queryKey: queryKeys.adminAuditLog(query),
    queryFn: () => fetchAdminAuditLog(query),
  })
  const rows = audit.data?.results ?? []

  return (
    <section className="flex flex-col gap-space-md">
      <div className="flex flex-wrap items-center justify-between gap-space-sm">
        <div className="flex flex-col">
          <h2 className="m-0 text-headline-md font-bold text-on-surface">
            {adminPage.recentActivities}
          </h2>
          <span className="text-label-sm text-outline">{adminPage.recentActivitiesHint}</span>
        </div>
        <Link to="/admin/analytics" className="flex items-center gap-1 text-label-md text-primary hover:underline">
          {adminPage.viewAllAudit}
          <span className="material-symbols-outlined text-[16px]">chevron_left</span>
        </Link>
      </div>

      {audit.isPending ? (
        <SkeletonRows count={3} />
      ) : audit.isError ? (
        <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
      ) : rows.length === 0 ? (
        <div className={`${cardCls} p-space-lg`}>
          <p className="m-0 text-body-md text-on-surface-variant">{adminPage.auditEmpty}</p>
        </div>
      ) : (
        <div className={`${cardCls} overflow-x-auto`}>
          <table className={tableCls}>
            <thead>
              <tr>
                <th className={thCls}>{adminPage.auditAt}</th>
                <th className={thCls}>{adminPage.auditAction}</th>
                <th className={thCls}>{adminPage.auditEntity}</th>
                <th className={thCls}>{adminPage.auditActor}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id} className={trCls(index)}>
                  <td className={`${tdCls} tnum`}>{formatJalaliDate(row.created_at)}</td>
                  <td className={tdCls}>
                    <ActionChip action={row.action} />
                  </td>
                  <td className={tdCls}>
                    {row.entity_type}
                    <span className="ms-1 tnum text-outline">#{row.entity_id}</span>
                  </td>
                  <td className={tdCls}>{row.actor_email ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

/* ── Page ────────────────────────────────────────────────────────────── */

export function AdminOverviewPage() {
  const { user } = useAuth()
  const name = user ? `${user.first_name} ${user.last_name}`.trim() || user.email : ''

  const analytics = useQuery({
    queryKey: queryKeys.adminAnalytics(),
    queryFn: fetchAdminDashboard,
  })
  const health = useQuery({
    queryKey: queryKeys.health(),
    queryFn: fetchHealth,
  })
  const failedDocs = useQuery({
    queryKey: queryKeys.adminDocuments({ status: 'FAILED', page_size: 1 }),
    queryFn: () => listAdminDocuments({ status: 'FAILED', page_size: 1 }).then((page) => page.count),
  })

  const failedCount = failedDocs.data ?? 0
  const dbDown = !health.isPending && (health.isError || health.data?.checks.database !== 'ok')

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <AdminWelcomeBanner name={name} analytics={analytics} health={health} />

      {/* Warnings — only from real signals (failed ingestion, DB check). */}
      {failedCount > 0 ? (
        <Link
          to="/admin/documents"
          className="flex items-center justify-between gap-space-md rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md transition-colors hover:bg-[#FEF3C7]"
        >
          <div className="flex items-center gap-space-sm text-[#92400E]">
            <span className="material-symbols-outlined text-[20px]">warning</span>
            <span className="text-body-sm">
              <span className="font-bold tnum">{toPersianDigits(failedCount)}</span>{' '}
              {adminPage.failedDocsWarningBody}
            </span>
          </div>
          <span className="flex items-center gap-1 text-label-md font-semibold text-[#B45309]">
            {adminPage.failedDocsWarningTitle}
            <span className="material-symbols-outlined text-[16px]">chevron_left</span>
          </span>
        </Link>
      ) : null}
      {dbDown ? (
        <div className="flex items-center gap-space-sm rounded-xl border border-error/30 bg-error-container/50 p-space-md text-on-error-container">
          <span className="material-symbols-outlined text-[20px]">error</span>
          <span className="text-body-sm">{adminPage.systemIssue}</span>
        </div>
      ) : null}

      {/* Summary cards — every value from a real endpoint. */}
      <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2 lg:grid-cols-3">
        <ListCountCard
          label={adminPage.kpiUsers}
          icon="group"
          query={{ resource: 'admin/users' }}
          queryFn={() => academicApi.adminCount('admin/users')}
          footer={{
            text: analytics.data
              ? `${adminPage.recentlyActive}: ${toPersianDigits(analytics.data.users.recently_active_users)}`
              : adminPage.recentlyActive,
          }}
        />
        <ListCountCard
          label={adminPage.kpiStudents}
          icon="school"
          query={{ resource: 'admin/students' }}
          queryFn={() => academicApi.adminCount('admin/students')}
        />
        <ListCountCard
          label={adminPage.kpiCourses}
          icon="menu_book"
          query={{ resource: 'admin/courses' }}
          queryFn={() => academicApi.adminCount('admin/courses')}
        />
        <ListCountCard
          label={adminPage.kpiProfessors}
          icon="co_present"
          query={{ resource: 'admin/professors' }}
          queryFn={() => academicApi.adminCount('admin/professors')}
        />
        <ListCountCard
          label={adminPage.activeDocuments}
          icon="description"
          query={{ status: 'ACTIVE', page_size: 1 }}
          queryFn={() => listAdminDocuments({ status: 'ACTIVE', page_size: 1 }).then((page) => page.count)}
          footer={{
            text: analytics.data
              ? `${adminPage.documentsTotal}: ${toPersianDigits(analytics.data.documents_total)}`
              : adminPage.documentsTotal,
          }}
        />
        <MetricCard
          label={adminPage.aiRequests}
          icon="psychology"
          iconTone="secondary"
          value={
            analytics.isPending ? '…' : analytics.isError ? '—'
              : toPersianDigits(analytics.data?.ai.total_requests ?? 0)
          }
          footer={
            analytics.data
              ? {
                  text: `${adminPage.errorsShort}: ${toPersianDigits(analytics.data.ai.error_count)}`,
                  tone: analytics.data.ai.error_count > 0 ? 'danger' : 'muted',
                }
              : undefined
          }
        />
      </div>

      {analytics.isPending ? (
        <SkeletonRows count={4} />
      ) : analytics.isError ? (
        <ErrorState error={analytics.error} onRetry={() => void analytics.refetch()} />
      ) : analytics.data ? (
        <div className="grid grid-cols-1 gap-space-md lg:grid-cols-12">
          <div className="lg:col-span-7">
            <AiStatsCard analytics={analytics.data} />
          </div>
          <div className="lg:col-span-5">
            <SystemStatusCard health={health} />
          </div>
        </div>
      ) : null}

      <RecentActivitiesCard />

      {/* Management screens stay reachable here — the simplified rail no
          longer lists them. */}
      <section className="flex flex-col gap-space-md">
        <h2 className="m-0 text-headline-md font-bold text-on-surface">{adminPage.quickLinks}</h2>
        <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2 xl:grid-cols-4">
          {ADMIN_LINKS.map(({ path, title }) => (
            <Link
              key={path}
              to={`/admin/${path}`}
              className={`${cardCls} group flex items-center justify-between gap-space-sm p-space-md transition-colors hover:border-primary/40 hover:bg-surface-container-low`}
            >
              <span className="text-body-md font-semibold text-on-surface">{title}</span>
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[20px] text-outline transition-colors group-hover:text-primary rtl:rotate-180"
              >
                arrow_back
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
