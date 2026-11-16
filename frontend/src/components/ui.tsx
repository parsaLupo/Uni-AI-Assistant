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
import { useEffect, useRef } from 'react'
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

export function EmptyState({
  message = common.empty,
  hint,
  action,
}: {
  message?: string
  /** One sentence that tells the user what to do next, not just "no data". */
  hint?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-space-sm rounded-xl border border-dashed border-outline-variant bg-surface-container-low/50 px-space-lg py-space-xl text-center">
      <span className="material-symbols-outlined text-[32px] text-outline">inbox</span>
      <p className="m-0 text-body-md text-on-surface-variant">{message}</p>
      {hint ? <p className="m-0 max-w-md text-label-md text-outline">{hint}</p> : null}
      {action ? <div className="pt-space-xs">{action}</div> : null}
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

/** One row of list filters; pages own the controls inside it. */
export function FilterRow({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-space-sm">{children}</div>
}

/** Search box with the design-system input and an inline search icon. */
export function SearchInput({
  value,
  onChange,
  placeholder,
  label,
  className = 'w-full max-w-sm',
}: {
  value: string
  onChange: (next: string) => void
  placeholder: string
  label: string
  className?: string
}) {
  return (
    <div className={`relative ${className}`}>
      <span
        aria-hidden="true"
        className="material-symbols-outlined pointer-events-none absolute inset-y-0 right-3 flex items-center text-[20px] text-outline"
      >
        search
      </span>
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={label}
        className={`${inputCls} pr-10`}
      />
    </div>
  )
}

/** Labelled select used by the list filters (term, department, type …). */
export function FilterSelect({
  icon,
  label,
  value,
  onChange,
  children,
  className = 'w-44',
}: {
  icon: string
  label: string
  value: string
  onChange: (next: string) => void
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`relative ${className}`}>
      <span
        aria-hidden="true"
        className="material-symbols-outlined pointer-events-none absolute inset-y-0 right-3 flex items-center text-[18px] text-outline"
      >
        {icon}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label={label}
        className={`${inputCls} pr-10`}
      >
        {children}
      </select>
    </div>
  )
}

/** Skeleton card grid for list pages (no layout shift when data lands). */
export function SkeletonCards({ count = 6 }: { count?: number }) {
  return (
    <div
      aria-hidden="true"
      className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-3"
    >
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="h-40 animate-pulse rounded-xl border border-outline-variant bg-surface-container-low motion-reduce:animate-none"
        />
      ))}
    </div>
  )
}

/** Skeleton rows for table/list pages. */
export function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <div aria-hidden="true" className="flex flex-col gap-space-sm">
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="h-16 animate-pulse rounded-xl border border-outline-variant bg-surface-container-low motion-reduce:animate-none"
        />
      ))}
    </div>
  )
}

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

/** Inline validation message under a form field (Persian, ADR-010 style). */
export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <span role="alert" className="text-label-sm font-medium text-error">
      {message}
    </span>
  )
}

/* ── Dialogs ──────────────────────────────────────────────────────────── */

/**
 * Accessible modal for admin forms (Phase 13). Owns dismissal: backdrop
 * click and Escape both resolve to the caller's `onClose`; the dialog role
 * plus `aria-modal` and a labelled heading keep it readable for RTL screen
 * readers. Focus falls back to the dialog surface so Escape works without a
 * focusable child.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  /** Two-column forms pick the wider shell. */
  wide?: boolean
}) {
  const surfaceRef = useRef<HTMLDivElement>(null)
  // Inline `onClose` arrows change identity on every parent render (each
  // keystroke in a controlled form field). Keeping the latest callback in a
  // ref lets the open/close effects depend on `open` alone — otherwise the
  // initial-focus call below would re-run and steal focus after every
  // keystroke typed inside the dialog.
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  // Runs once per open/close transition: scroll lock + initial focus.
  useEffect(() => {
    if (!open) return
    // Keep the page behind the overlay still while the dialog is open.
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    // Move focus into the dialog so Escape/Tab behave from the right place.
    surfaceRef.current?.focus()
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  // Escape always closes through the freshest callback.
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  if (!open) return null
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center p-space-md"
    >
      <button
        type="button"
        aria-label={common.closeDialog}
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-[#0F172A]/45"
      />
      <div
        ref={surfaceRef}
        tabIndex={-1}
        className={`relative z-10 max-h-[90vh] w-full overflow-y-auto rounded-xl border border-outline-variant bg-surface-container-lowest shadow-lg focus:outline-none ${
          wide ? 'max-w-3xl' : 'max-w-xl'
        }`}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between gap-space-sm border-b border-outline-variant bg-surface-container-lowest px-space-lg py-space-md">
          <h2 className="m-0 text-headline-md font-bold text-on-surface">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={common.closeDialog}
            className="flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high"
          >
            <span aria-hidden="true" className="material-symbols-outlined text-[20px]">
              close
            </span>
          </button>
        </div>
        <div className="p-space-lg">{children}</div>
      </div>
    </div>
  )
}

/** Destructive-action confirmation — never a bare button click. */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = common.confirmDelete,
  busy = false,
  error,
  onCancel,
  onConfirm,
}: {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  busy?: boolean
  error?: unknown
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <Modal open={open} onClose={busy ? () => undefined : onCancel} title={title}>
      <div className="flex flex-col gap-space-md">
        <div className="flex items-start gap-space-sm">
          <span aria-hidden="true" className="material-symbols-outlined text-[24px] text-error">
            warning
          </span>
          <p className="m-0 text-body-md leading-relaxed text-on-surface">{message}</p>
        </div>
        {error ? <ErrorState error={error} /> : null}
        <div className="flex items-center justify-end gap-space-sm pt-space-xs">
          <button type="button" className={btnSecondaryCls} disabled={busy} onClick={onCancel}>
            {common.cancel}
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-space-xs rounded bg-error px-space-lg py-space-sm text-on-error-container text-label-lg font-semibold shadow-sm transition-all hover:opacity-90 active:scale-[0.99] disabled:opacity-75"
            disabled={busy}
            onClick={onConfirm}
          >
            {busy ? <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-on-error-container border-t-transparent motion-reduce:animate-none" /> : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
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