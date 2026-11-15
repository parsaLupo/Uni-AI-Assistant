/**
 * /admin/terms — academic-term management (docs/api/admin.md "Academic
 * structure"). PATCH-only by contract: a historical term is immutable and
 * DELETE is not exposed (http_method_names minus delete), so the table has no
 * delete column and the form says so honestly. `is_current` is DB-guarded:
 * at most one current term — the resulting 409 surfaces as Persian text.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { listAdminTerms, createAdminTerm, updateAdminTerm } from '../../api/admin'
import { queryKeys } from '../../api/keys'
import {
  Chip,
  EmptyState,
  ErrorState,
  FieldError,
  Modal,
  PageHeader,
  PaginationBar,
  btnPrimaryCls,
  btnSecondaryCls,
  cardCls,
  inputCls,
  tableCls,
  tdCls,
  thCls,
  SkeletonRows,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { toAsciiDigits, toPersianDigits } from '../../i18n/digits'
import { adminTermsPage as t, common } from '../../i18n/fa'
import { formatJalaliDate } from '../../i18n/jalali'
import { semesterLabels } from '../../i18n/labels'
import type { AcademicTerm, SemesterType } from '../../types/academic'

const PAGE_SIZE = 10

interface TermFormState {
  name: string
  academic_year: string
  semester_type: SemesterType
  starts_at: string
  ends_at: string
  is_current: boolean
}

const EMPTY_FORM: TermFormState = {
  name: '',
  academic_year: '',
  semester_type: 'FIRST',
  starts_at: '',
  ends_at: '',
  is_current: false,
}

/** The serializer does not expose `is_past`; compare the ISO `ends_at`. */
function isPastRow(endsAt: string): boolean {
  return endsAt < new Date().toISOString().slice(0, 10)
}

export function AdminTermsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useUrlState<number>('page', 1)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<AcademicTerm | null>(null)
  const [form, setForm] = useState<TermFormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<unknown>(null)
  const [savedNote, setSavedNote] = useState('')

  const query = { page, page_size: PAGE_SIZE }
  const terms = useQuery({
    queryKey: queryKeys.adminTerms(query),
    queryFn: () => listAdminTerms(query),
    placeholderData: (previous) => previous,
  })

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing ? updateAdminTerm(editing.id, payload) : createAdminTerm(payload),
    onSuccess: () => {
      setFormOpen(false)
      setFormError(null)
      setSavedNote(editing ? common.updated : common.created)
      void queryClient.invalidateQueries({ queryKey: ['admin', 'terms'] })
      void queryClient.invalidateQueries({ queryKey: ['terms'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'count'] })
    },
    onError: (error) => setFormError(error),
  })

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const openEdit = (row: AcademicTerm) => {
    setEditing(row)
    setForm({
      name: row.name,
      academic_year: row.academic_year,
      semester_type: row.semester_type,
      starts_at: row.starts_at,
      ends_at: row.ends_at,
      is_current: row.is_current,
    })
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const submit = () => {
    const errors: Record<string, string> = {}
    if (!form.name.trim()) errors.name = common.requiredField
    if (!form.academic_year.trim()) errors.academic_year = common.requiredField
    if (!form.starts_at) errors.starts_at = common.requiredField
    if (!form.ends_at) errors.ends_at = common.requiredField
    if (form.starts_at && form.ends_at && form.starts_at >= form.ends_at) {
      errors.ends_at = t.datesOrder
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setFormError(null)
    save.mutate({
      name: form.name.trim(),
      academic_year: toAsciiDigits(form.academic_year.trim()),
      semester_type: form.semester_type,
      starts_at: form.starts_at,
      ends_at: form.ends_at,
      is_current: form.is_current,
    })
  }

  const rows = terms.data?.results ?? []

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-terms-page">
      <PageHeader
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <button type="button" className={btnPrimaryCls} onClick={openCreate}>
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
              calendar_add_on
            </span>
            {common.create}
          </button>
        }
      />

      {savedNote ? (
        <div role="status" className={`${cardCls} border-[#99F6E4] bg-[#F0FDFA] p-space-md text-body-sm text-[#0D9488]`}>
          {savedNote}
        </div>
      ) : null}

      {terms.isPending ? (
        <SkeletonRows count={4} />
      ) : terms.isError ? (
        <ErrorState error={terms.error} onRetry={() => void terms.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={t.empty} />
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.colName}</th>
                  <th className={thCls}>{t.colYear}</th>
                  <th className={thCls}>{t.colSemester}</th>
                  <th className={thCls}>{t.colDates}</th>
                  <th className={thCls}>{t.colCurrent}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={`${tdCls} font-semibold text-on-surface`}>{row.name}</td>
                    <td className={`${tdCls} tnum`}>{toPersianDigits(row.academic_year)}</td>
                    <td className={tdCls}>{semesterLabels[row.semester_type]}</td>
                    <td className={`${tdCls} tnum`}>
                      {formatJalaliDate(row.starts_at)} ← {formatJalaliDate(row.ends_at)}
                    </td>
                    <td className={tdCls}>
                      {row.is_current ? <Chip tone="success">{t.currentChip}</Chip> : '—'}
                    </td>
                    <td className={tdCls}>
                      <button
                        type="button"
                        className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                        onClick={() => openEdit(row)}
                      >
                        {common.edit}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PaginationBar
            count={terms.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}

      <span className="text-label-sm text-outline">{t.deleteNotSupported}</span>

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? t.editTitle : t.createTitle}
      >
        {editing && isPastRow(editing.ends_at) ? (
          <div className="mb-space-md rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md text-body-sm text-[#92400E]">
            {t.pastHint}
          </div>
        ) : null}
        <form
          className="flex flex-col gap-space-md"
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
          noValidate
        >
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.nameField}</span>
            <input
              className={inputCls}
              value={form.name}
              placeholder={t.namePlaceholder}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
            />
            <FieldError message={fieldErrors.name} />
          </label>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.academicYear}</span>
              <input
                className={inputCls}
                dir="ltr"
                value={form.academic_year}
                placeholder={t.yearPlaceholder}
                onChange={(event) => setForm({ ...form, academic_year: event.target.value })}
              />
              <FieldError message={fieldErrors.academic_year} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.semesterType}</span>
              <select
                className={inputCls}
                value={form.semester_type}
                onChange={(event) =>
                  setForm({ ...form, semester_type: event.target.value as SemesterType })
                }
              >
                {(['FIRST', 'SECOND', 'SUMMER'] as const).map((value) => (
                  <option key={value} value={value}>
                    {semesterLabels[value]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.startsAt}</span>
              <input
                type="date"
                dir="ltr"
                className={inputCls}
                value={form.starts_at}
                onChange={(event) => setForm({ ...form, starts_at: event.target.value })}
              />
              <FieldError message={fieldErrors.starts_at} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.endsAt}</span>
              <input
                type="date"
                dir="ltr"
                className={inputCls}
                value={form.ends_at}
                onChange={(event) => setForm({ ...form, ends_at: event.target.value })}
              />
              <FieldError message={fieldErrors.ends_at} />
            </label>
          </div>

          <label className="flex items-center gap-space-sm text-body-sm">
            <input
              type="checkbox"
              checked={form.is_current}
              onChange={(event) => setForm({ ...form, is_current: event.target.checked })}
            />
            <span className="font-semibold text-on-surface">{t.isCurrent}</span>
          </label>
          {form.is_current && !(editing?.is_current ?? false) ? (
            <span className="text-label-sm text-[#B45309]">{t.isCurrentHint}</span>
          ) : null}

          {formError ? <ErrorState error={formError} /> : null}

          <div className="flex items-center justify-end gap-space-sm pt-space-xs">
            <button type="button" className={btnSecondaryCls} onClick={() => setFormOpen(false)}>
              {common.cancel}
            </button>
            <button type="submit" className={btnPrimaryCls} disabled={save.isPending}>
              {save.isPending ? common.saving : common.save}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
