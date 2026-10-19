/**
 * /admin — AdminDashboardDESIGN.md overview wired to live counts.
 *
 * The mockup shows KPI tiles over real data; every tile below reads `count`
 * from the Phase 04 admin list endpoints (docs/api/admin.md, page_size=1 —
 * no mock values, docs/06 §8). Quick links deep-link into the guarded admin
 * route group. Full management tables + analytics land with their phases
 * (documents = Phase 07, analytics = Phase 13).
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import { PageHeader, PersianNum, cardCls } from '../../components/ui'
import { adminPage } from '../../i18n/fa'
import { ADMIN_LINKS } from './links'

interface Kpi {
  label: string
  resource: string
  icon: string
}

const KPIS: Kpi[] = [
  { label: adminPage.kpiUsers, resource: 'admin/users', icon: 'group' },
  { label: adminPage.kpiStudents, resource: 'admin/students', icon: 'school' },
  { label: adminPage.kpiCourses, resource: 'admin/courses', icon: 'menu_book' },
  { label: adminPage.kpiProfessors, resource: 'admin/professors', icon: 'co_present' },
  { label: adminPage.kpiTerms, resource: 'admin/terms', icon: 'calendar_month' },
  { label: adminPage.kpiOfferings, resource: 'admin/offerings', icon: 'event_note' },
  { label: adminPage.kpiEnrollments, resource: 'admin/enrollments', icon: 'how_to_reg' },
  { label: adminPage.kpiAnnouncements, resource: 'admin/announcements', icon: 'campaign' },
]

function KpiCard({ label, resource, icon }: Kpi) {
  const count = useQuery({
    queryKey: queryKeys.adminCount(resource),
    queryFn: () => academicApi.adminCount(resource),
  })

  return (
    <div className={`${cardCls} flex items-center gap-space-md p-space-md`}>
      <span
        aria-hidden="true"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"
      >
        <span className="material-symbols-outlined text-[24px]">{icon}</span>
      </span>
      <div className="flex min-w-0 flex-col">
        <span className="text-label-md text-on-surface-variant">{label}</span>
        <span className="text-headline-lg font-bold text-on-surface">
          {count.isPending ? (
            <span className="inline-block h-6 w-10 animate-pulse rounded bg-surface-container-high motion-reduce:animate-none" />
          ) : count.isError ? (
            <span className="text-body-md font-medium text-[#B45309]">—</span>
          ) : (
            <PersianNum value={count.data} />
          )}
        </span>
      </div>
    </div>
  )
}

export function AdminOverviewPage() {
  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader
        title={adminPage.title}
        subtitle={adminPage.subtitle}
        actions={
          <span className="rounded-full bg-secondary-container px-space-sm py-1 text-label-sm font-semibold text-on-secondary-container">
            {adminPage.liveCount}
          </span>
        }
      />

      <section aria-label={adminPage.title} className="grid grid-cols-1 gap-space-md sm:grid-cols-2 xl:grid-cols-4">
        {KPIS.map((kpi) => (
          <KpiCard key={kpi.resource} {...kpi} />
        ))}
      </section>

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
