/**
 * /admin/analytics — Phase 13 admin dashboard (docs/api/admin.md).
 *
 * Everything below reads `GET /admin/analytics/dashboard/` (aggregate-only:
 * counts, means and titles; raw message content never leaves the server) and
 * `GET /admin/analytics/audit-log/` (read-only viewer over the append-only
 * audit source). adminPage labels are Persian (AGENTS.md §Language).
 */

import { useQuery } from '@tanstack/react-query'
import { fetchAdminAuditLog, fetchAdminDashboard } from '../../api/admin'
import { queryKeys } from '../../api/keys'
import {
  EmptyState,
  ErrorState,
  FilterSelect,
  PageHeader,
  SkeletonRows,
  cardCls,
  tdCls,
  thCls,
  tableCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { toPersianDigits } from '../../i18n/digits'
import { formatJalaliDate } from '../../i18n/jalali'
import { executionModeLabels, roleLabels } from '../../i18n/labels'
import { adminPage, common } from '../../i18n/fa'
import type { AuditLogQuery } from '../../api/admin'

const AUDIT_PAGE_SIZE = 15

export function AdminAnalyticsPage() {
  const dashboard = useQuery({
    queryKey: queryKeys.adminAnalytics(),
    queryFn: fetchAdminDashboard,
  })

  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader
        title={adminPage.analyticsTitle}
        subtitle={adminPage.analyticsSubtitle}
        actions={
          dashboard.data ? (
            <span className="text-label-sm text-outline tnum">
              {adminPage.generatedAt}: {formatJalaliDate(dashboard.data.generated_at.slice(0, 10))}
            </span>
          ) : undefined
        }
      />

      {dashboard.isPending ? (
        <SkeletonRows count={4} />
      ) : dashboard.isError ? (
        <ErrorState
          error={dashboard.error}
          onRetry={() => void dashboard.refetch()}
        />
      ) : dashboard.data ? (
        <DashboardSections dashboard={dashboard.data} />
      ) : null}

      <AuditLogSection />
    </div>
  )
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string
  value: number | string | null
  hint?: string
}) {
  return (
    <div className={`${cardCls} flex flex-col gap-1 p-space-md`}>
      <span className="text-label-md text-on-surface-variant">{label}</span>
      <span className="text-headline-lg font-bold text-on-surface tnum">
        {value === null || value === undefined ? (
          <span className="text-body-md font-medium text-[#B45309]">—</span>
        ) : typeof value === 'number' ? (
          toPersianDigits(value)
        ) : (
          value
        )}
      </span>
      {hint ? <span className="text-label-sm text-outline">{hint}</span> : null}
    </div>
  )
}

function ModeDistribution({ rows }: { rows: Array<{ mode: string; count: number }> }) {
  return (
    <section className={`${cardCls} flex flex-col gap-space-sm p-space-lg`}>
      <h3 className="m-0 text-headline-sm font-bold text-on-surface">
        {adminPage.topicDistribution}
      </h3>
      {rows.length === 0 ? (
        <p className="m-0 text-body-sm text-on-surface-variant">{common.empty}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
          {rows.map((row) => (
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

function TopDocuments({
  rows,
  documentsTotal,
}: {
  rows: Array<{
    id: number
    title: string
    document_type: string
    academic_year: string
    citation_count: number
  }>
  documentsTotal: number
}) {
  return (
    <section className={`${cardCls} flex flex-col gap-space-sm p-space-lg`}>
      <h3 className="m-0 text-headline-sm font-bold text-on-surface">
        {adminPage.topDocuments}
      </h3>
      {rows.length === 0 ? (
        <p className="m-0 text-body-sm text-on-surface-variant">{common.empty}</p>
      ) : (
        <table className={tableCls}>
          <thead>
            <tr>
              <th className={thCls}>{adminPage.documentColumn}</th>
              <th className={thCls}>{adminPage.citationCount}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className={tdCls}>
                  {row.title}
                  <span className="ms-2 text-label-sm text-outline tnum">
                    {row.academic_year}
                  </span>
                </td>
                <td className={`${tdCls} tnum`}>{toPersianDigits(row.citation_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <span className="text-label-sm text-outline tnum">
        {adminPage.documentsTotal}: {toPersianDigits(documentsTotal)}
      </span>
    </section>
  )
}

function DashboardSections({ dashboard }: { dashboard: Awaited<ReturnType<typeof fetchAdminDashboard>> }) {
  return (
    <div className="flex flex-col gap-space-lg" data-testid="dashboard-sections">
      <section aria-label={adminPage.analyticsTitle} className="grid grid-cols-1 gap-space-md sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label={adminPage.activeUsers}
          value={dashboard.users.active_users}
          hint={`${adminPage.recentlyActive}: ${toPersianDigits(dashboard.users.recently_active_users)}`}
        />
        <MetricCard
          label={adminPage.questionsTotal}
          value={dashboard.questions.total}
          hint={`${adminPage.questionsLast7Days}: ${toPersianDigits(dashboard.questions.last_7_days)}`}
        />
        <MetricCard label={adminPage.answersTotal} value={dashboard.questions.answers} />
        <MetricCard
          label={adminPage.aiRequests}
          value={dashboard.ai.total_requests}
          hint={`${adminPage.aiErrors}: ${toPersianDigits(dashboard.ai.error_count)}`}
        />
        <MetricCard
          label={adminPage.avgLatency}
          value={dashboard.ai.avg_latency_ms === null ? null : toPersianDigits(dashboard.ai.avg_latency_ms)}
        />
        <MetricCard label={adminPage.insufficientEvidence} value={dashboard.questions.insufficient_evidence} />
        <MetricCard label={adminPage.documentsTotal} value={dashboard.documents_total} />
      </section>

      <div className="grid grid-cols-1 gap-space-md xl:grid-cols-2">
        <ModeDistribution rows={dashboard.topic_distribution} />
        <section className={`${cardCls} flex flex-col gap-space-sm p-space-lg`}>
          <h3 className="m-0 text-headline-sm font-bold text-on-surface">{adminPage.roleCounts}</h3>
          <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
            {dashboard.users.by_role.length === 0 ? (
              <li className="text-body-sm text-on-surface-variant">{common.empty}</li>
            ) : (
              dashboard.users.by_role.map((row) => (
                <li key={row.role} className="flex items-center justify-between gap-space-sm">
                  <span className="text-body-md text-on-surface">
                    {roleLabels[row.role as keyof typeof roleLabels] ?? row.role}
                  </span>
                  <span className="text-body-md font-bold text-primary tnum">
                    {toPersianDigits(row.count)}
                  </span>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>

      <TopDocuments rows={dashboard.top_documents} documentsTotal={dashboard.documents_total} />
    </div>
  )
}

const AUDIT_ACTION_OPTIONS = [
  { value: '', label: adminPage.auditAllActions },
  { value: 'CREATE', label: adminPage.auditCreate },
  { value: 'UPDATE', label: adminPage.auditUpdate },
  { value: 'DELETE', label: adminPage.auditDelete },
] as const

/** Persian label per audit action; unknown server values fall through raw. */
const AUDIT_ACTION_LABELS: Record<string, string> = Object.fromEntries(
  AUDIT_ACTION_OPTIONS.filter((option) => option.value).map((option) => [option.value, option.label]),
)

function AuditLogSection() {
  const [page, setPage] = useUrlState<number>('auditPage', 1)
  const [action, setAction] = useUrlState<string>('auditAction', '')

  const query: AuditLogQuery = {
    page,
    page_size: AUDIT_PAGE_SIZE,
    ...(action ? { action: action.toUpperCase() } : {}),
  }
  const audit = useQuery({
    queryKey: queryKeys.adminAuditLog(query),
    queryFn: () => fetchAdminAuditLog(query),
    placeholderData: (previous) => previous,
  })

  const rows = audit.data?.results ?? []

  return (
    <section className="flex flex-col gap-space-md" data-testid="audit-log-section">
      <div className="flex flex-wrap items-center gap-space-sm">
        <h2 className="m-0 text-headline-md font-bold text-on-surface">
          {adminPage.auditLogTitle}
        </h2>
        <span className="text-label-sm text-outline">{adminPage.auditLogSubtitle}</span>
        <div className="ms-auto w-44">
          <FilterSelect
            icon="history"
            label={adminPage.auditAction}
            value={action}
            onChange={(next) => {
              setAction(next)
              setPage(1)
            }}
          >
            {AUDIT_ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </FilterSelect>
        </div>
      </div>

      {audit.isPending ? (
        <SkeletonRows count={3} />
      ) : audit.isError ? (
        <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={adminPage.auditEmpty} />
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
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className={`${tdCls} tnum`}>{formatJalaliDate(row.created_at)}</td>
                  <td className={tdCls}>{AUDIT_ACTION_LABELS[row.action] ?? row.action}</td>
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
