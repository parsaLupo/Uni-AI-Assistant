/**
 * /admin/<section> — guarded scaffold for the management sections.
 *
 * Phase 05 owns the route group + guards (docs/20); the full CRUD tables are
 * later phases (documents = 07, analytics = 13). Until then this page states
 * that honestly in Persian instead of showing fabricated data (docs/06 §8).
 */

import { Link } from 'react-router-dom'
import { PageHeader, cardCls } from '../../components/ui'
import { adminPage } from '../../i18n/fa'

export function AdminStubPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader title={title} subtitle={adminPage.stubSection} />
      <div className={`${cardCls} flex flex-col items-center gap-space-md p-space-xl text-center`}>
        <span aria-hidden="true" className="material-symbols-outlined text-[48px] text-outline">
          construction
        </span>
        <p className="m-0 max-w-xl text-body-md text-on-surface-variant">{adminPage.stubBody}</p>
        <Link
          to="/admin"
          className="inline-flex items-center gap-space-xs rounded bg-primary-container px-space-lg py-space-sm text-label-lg font-semibold text-on-primary transition-colors hover:bg-[#2563EB]"
        >
          {adminPage.quickLinks}
        </Link>
      </div>
    </div>
  )
}
