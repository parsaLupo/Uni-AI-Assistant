/**
 * Shared presentational building blocks (Phase 05: "Reusable table/card/form
 * components where appropriate").
 *
 * Class strings follow the DESIGN.md component specs (buttons, inputs, data
 * tables, academic cards, citation chips) so every page inherits the design
 * system instead of re-deriving it. State components own the Persian
 * loading/empty/error copy required by docs/20 and docs/12.
 */

import type { ReactNode } from 'react'
import { ApiError } from '../api/client'
import { common, persianErrorText } from '../i18n/fa'
import { toPersianDigits } from '../i18n/digits'

/* ── Design-system class constants (DESIGN.md → components) ───────────── */

export const cardCls = 'rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm'

export const btnPrimaryCls =
  'inline-flex items-center justify-center gap-space-xs rounded bg-primary-container px-space-lg py-space-sm text-on-primary text-label-lg font-semibold shadow-sm transition-all hover:bg-[#2563EB] active:scale-[0.99] disabled:opacity-75 disabled:cursor-not-allowed'

export const btnSecondaryCls =
  'inline-flex items-center justify-center gap-space-xs rounded border border-outline-variant bg-surface-container-lowest px-space-lg py-space-sm text-primary text-label-lg font-semibold transition-colors hover:bg-[#F8FAFC] hover:border-[#CBD5E1] disabled:opacity-60'

export const inputCls =
  'w-full rounded-xl border border-[#CBD5E1] bg-white px-space-md py-3 text-body-sm text-[#0F172A] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15 transition-all'

export const tableCls = 'w-full border border-outline-variant text-right font-body-sm text-body-sm'
export const thCls =
  'bg-[#F8FAFC] px-space-md py-space-sm text-start text-primary font-label-md font-bold border-b border-outline-variant'
export const tdCls = 'px-space-md py-space-sm border-b border-outline-variant align-middle'

/** Zebra + hover row treatment for the data tables (DESIGN.md). */
export function trCls(index: number): string {
  return index % 2 === 1
    ? 'bg-surface-container-low/40 hover:bg-surface-container-low transition-colors'
    : 'hover:bg-surface-container-low transition-colors'
}

/* ── State components ─────────────────────────────────────────────────── */

export function LoadingState({ label = common.loading }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-center gap-space-sm py-space-xl text-body-md text-on-surface-variant"
    >
      <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-outline-variant border-t-primary motion-reduce:animate-none" />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ message = common.empty }: { message?: string }) {
  return (
    <div className="flex flex-col items-center gap-space-sm rounded-xl border border-dashed border-outline-variant bg-surface-container-low/50 px-space-lg py-space-xl text-center">
      <span className="material-symbols-outlined text-[32px] text-outline">inbox</span>
      <p className="m-0 text-body-md text-on-surface-variant">{message}</p>
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = error instanceof ApiError ? error : null
  const code = apiError?.code ?? 'INTERNAL_ERROR'
  const message = persianErrorText(code, apiError?.message)
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-space-sm rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md"
    >
      <div className="flex items-center gap-space-sm">
        <span className="material-symbols-outlined text-[20px] text-[#B45309]">error</span>
        <span className="text-label-lg font-bold text-[#B45309]">{common.errorTitle}</span>
      </div>
      <p className="m-0 text-body-sm text-[#92400E]">{message}</p>
      {apiError?.requestId ? (
        <p className="m-0 text-label-sm text-outline tnum">شناسه درخواست: {apiError.requestId}</p>
      ) : null}
      {onRetry ? (
        <button type="button" onClick={onRetry} className={btnSecondaryCls}>
          {common.retry}
        </button>
      ) : null}
    </div>
  )
}

/* ── Page furniture ───────────────────────────────────────────────────── */

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-space-md">
      <div className="flex flex-col gap-1">
        <h1 className="m-0 text-headline-lg font-bold text-on-surface">{title}</h1>
        {subtitle ? <p className="m-0 text-body-sm text-on-surface-variant">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-space-sm">{actions}</div> : null}
    </div>
  )
}

/** Design-system pill for statuses/priorities (emerald/amber/navy/neutral). */
export function Chip({
  tone = 'neutral',
  children,
}: {
  tone?: 'success' | 'warning' | 'primary' | 'neutral' | 'danger'
  children: ReactNode
}) {
  const tones: Record<string, string> = {
    success: 'bg-[#F0FDFA] text-[#0D9488] border border-[#99F6E4]',
    warning: 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]',
    danger: 'bg-error-container/50 text-on-error-container border border-error/30',
    primary: 'bg-primary/10 text-primary',
    neutral: 'bg-surface-container-high text-on-surface-variant',
  }
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-space-sm py-0.5 text-label-sm font-medium tnum ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function PersianNum({ value, suffix }: { value: string | number; suffix?: string }) {
  return (
    <span className="tnum">
      {toPersianDigits(value)}
      {suffix ? ` ${suffix}` : ''}
    </span>
  )
}

/** Pagination bar for paginated list endpoints (count/page contract). */
export function PaginationBar({
  count,
  page,
  pageSize,
  onPage,
}: {
  count: number
  page: number
  pageSize: number
  onPage: (page: number) => void
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  if (totalPages <= 1) return null
  return (
    <div className="flex items-center justify-between gap-space-sm pt-space-sm">
      <span className="text-label-sm text-on-surface-variant tnum">
        {common.resultsCount}: {toPersianDigits(count)} — {common.page} {toPersianDigits(page)} از{' '}
        {toPersianDigits(totalPages)}
      </span>
      <div className="flex items-center gap-space-xs">
        <button
          type="button"
          className={btnSecondaryCls}
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          {common.prev}
        </button>
        <button
          type="button"
          className={btnSecondaryCls}
          disabled={page >= totalPages}
          onClick={() => onPage(page + 1)}
        >
          {common.next}
        </button>
      </div>
    </div>
  )
}