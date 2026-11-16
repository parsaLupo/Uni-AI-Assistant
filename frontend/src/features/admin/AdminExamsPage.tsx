/**
 * /admin/exams — exam management (docs/api/admin.md "Offerings, schedules,
 * exams"). The exam of an offering is the nested resource
 * `/admin/offerings/{id}/exam/` (GET/PUT/PATCH; no DELETE by contract), so the
 * screen pairs a read-only exam list (public `/exams/` read, admin sees all)
 * with a "set exam" editor per offering. Historical terms are rejected with
 * the backend's own Persian 400/409 message.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { fetchOfferingExam, saveOfferingExam } from '../../api/admin'
import { localInputToUtcIso, utcIsoToLocalInput } from '../../api/dates'
import { academicApi } from '../../api/resources'
import { queryKeys } from '../../api/keys'
import {
  Chip,
  EmptyState,
  ErrorState,
  FieldError,
  FilterRow,
  FilterSelect,
  Modal,
  PageHeader,
  PaginationBar,
  SkeletonRows,
  btnPrimaryCls,
  btnSecondaryCls,
  cardCls,
  inputCls,
  tableCls,
  tdCls,
  thCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { toPersianDigits } from '../../i18n/digits'
import { adminExamsPage as t, common } from '../../i18n/fa'
import { examStatusLabels } from '../../i18n/labels'
import { formatJalaliDate, formatTimeFa } from '../../i18n/jalali'
import type { Exam } from '../../types/academic'

const PAGE_SIZE = 10
const EXAM_STATUSES = ['SCHEDULED', 'CHANGED', 'CANCELLED'] as const

interface ExamFormState {
  offering_id: string
  starts_at: string
  ends_at: string
  classroom: string
  status: (typeof EXAM_STATUSES)[number]
}

const EMPTY_FORM: ExamFormState = {
  offering_id: '',
  starts_at: '',
  ends_at: '',
  classroom: '',
  status: 'SCHEDULED',
}

export function AdminExamsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useUrlState<number>('page', 1)
  const [term, setTerm] = useUrlState<string>('term', '')

  const [editorOpen, setEditorOpen] = useState(false)
  const [editingOfferingId, setEditingOfferingId] = useState<number | null>(null)
  const [form, setForm] = useState<ExamFormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<unknown>(null)
  const [existingExam, setExistingExam] = useState<Exam | null>(null)
  const [savedNote, setSavedNote] = useState('')

  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 100 }),
  })

  const examsQuery = {
    page,
    page_size: PAGE_SIZE,
    ...(term ? { term } : {}),
  }
  const exams = useQuery({
    queryKey: queryKeys.exams(examsQuery),
    queryFn: () => academicApi.exams(examsQuery),
    placeholderData: (previous) => previous,
  })

  const rows = exams.data?.results ?? []
  const hasFilters = Boolean(term)
  const clearFilters = () => {
    setTerm('')
    setPage(1)
  }

  /* ── Editor: pick offering → load its exam → PUT/PATCH ─────────────── */

  const editorOfferings = useQuery({
    queryKey: ['admin', 'offerings', 'editor', term],
    queryFn: () => academicApi.offerings({ term: term || undefined, page_size: 100 }),
  })

  const offeringExam = useQuery({
    queryKey: queryKeys.offeringExam(form.offering_id),
    queryFn: () => fetchOfferingExam(form.offering_id),
    enabled: Boolean(form.offering_id),
    // A 404 means "no exam yet" — that is a normal create path.
    retry: false,
  })

  useEffect(() => {
    setExistingExam(offeringExam.data ?? null)
  }, [offeringExam.data])

  const save = useMutation({
    mutationFn: (payload: { body: Record<string, unknown>; partial: boolean }) =>
      // `partial` only applies to updates; a create is a full PUT.
      saveOfferingExam(form.offering_id, payload.body, payload.partial),
    onSuccess: () => {
      setEditorOpen(false)
      setFormError(null)
      setSavedNote(existingExam ? common.updated : common.created)
      void queryClient.invalidateQueries({ queryKey: ['exams'] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'offerings', 'exam'] })
    },
    onError: (error) => setFormError(error),
  })

  const openEditor = (exam?: Exam) => {
    setFormError(null)
    setFieldErrors({})
    setSavedNote('')
    if (exam) {
      setForm({
        offering_id: String(exam.course_offering.id),
        starts_at: utcIsoToLocalInput(exam.starts_at),
        ends_at: utcIsoToLocalInput(exam.ends_at),
        classroom: exam.classroom,
        status: exam.status,
      })
      setEditingOfferingId(exam.course_offering.id)
    } else {
      setForm(EMPTY_FORM)
      setEditingOfferingId(null)
    }
    setEditorOpen(true)
  }

  const submitExam = () => {
    const errors: Record<string, string> = {}
    if (!form.offering_id) errors.offering_id = t.pickOffering
    if (!form.starts_at) errors.starts_at = common.requiredField
    if (!form.ends_at) errors.ends_at = common.requiredField
    if (form.starts_at && form.ends_at && form.starts_at >= form.ends_at) {
      errors.ends_at = t.timeOrder
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setFormError(null)
    const body = {
      // Instant-preserving: the local wall time the admin picked, serialized
      // as a UTC ISO instant (same contract the announcements form uses).
      starts_at: localInputToUtcIso(form.starts_at) ?? '',
      ends_at: localInputToUtcIso(form.ends_at) ?? '',
      classroom: form.classroom.trim(),
      status: form.status,
      // PUT requires the FK on the wire (serializer write field).
      course_offering_id: Number(form.offering_id),
    }
    save.mutate({ body, partial: Boolean(existingExam) })
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-exams-page">
      <PageHeader
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <button type="button" className={btnPrimaryCls} onClick={() => openEditor()}>
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
              event_available
            </span>
            {t.configure}
          </button>
        }
      />

      {savedNote ? (
        <div role="status" className={`${cardCls} border-[#99F6E4] bg-[#F0FDFA] p-space-md text-body-sm text-[#0D9488]`}>
          {savedNote}
        </div>
      ) : null}

      <FilterRow>
        <FilterSelect
          icon="calendar_month"
          label={t.filterTerm}
          value={term}
          onChange={(next) => {
            setTerm(next)
            setPage(1)
          }}
          className="w-52"
        >
          <option value="">{common.filterAll}</option>
          <option value="current">{common.filterCurrent}</option>
          {(terms.data?.results ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.name}
            </option>
          ))}
        </FilterSelect>
        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}
        {exams.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(exams.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {exams.isPending ? (
        <SkeletonRows count={4} />
      ) : exams.isError ? (
        <ErrorState error={exams.error} onRetry={() => void exams.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={t.empty} hint={t.emptyHint} />
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.colCourse}</th>
                  <th className={thCls}>{t.colSection}</th>
                  <th className={thCls}>{t.colTerm}</th>
                  <th className={thCls}>{t.colDate}</th>
                  <th className={thCls}>{t.colClassroom}</th>
                  <th className={thCls}>{t.colStatus}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={tdCls}>
                      <span className="tnum font-semibold" dir="ltr">
                        {row.course_offering.course_code}
                      </span>{' '}
                      {row.course_offering.course_title}
                    </td>
                    <td className={`${tdCls} tnum`} dir="ltr">
                      {row.course_offering.section_code}
                    </td>
                    <td className={tdCls}>{row.course_offering.term.name}</td>
                    <td className={`${tdCls} tnum`}>
                      {formatJalaliDate(row.starts_at)} · {formatTimeFa(row.starts_at)}
                    </td>
                    <td className={tdCls}>{row.classroom || common.notSetFallback}</td>
                    <td className={tdCls}>
                      <Chip tone={row.status === 'CANCELLED' ? 'danger' : row.status === 'CHANGED' ? 'warning' : 'primary'}>
                        {examStatusLabels[row.status]}
                      </Chip>
                    </td>
                    <td className={tdCls}>
                      <button
                        type="button"
                        className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                        onClick={() => openEditor(row)}
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
            count={exams.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}

      <Modal open={editorOpen} onClose={() => setEditorOpen(false)} title={t.createTitle} wide>
        <div className="flex flex-col gap-space-md">
          <p className="m-0 text-body-sm text-on-surface-variant">{t.offeringHint}</p>
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.offeringSelect}</span>
            <select
              className={inputCls}
              value={form.offering_id}
              onChange={(event) => setForm({ ...form, offering_id: event.target.value })}
              disabled={Boolean(editingOfferingId) || Boolean(existingExam)}
            >
              <option value="">{common.notSetFallback}</option>
              {(editorOfferings.data?.results ?? []).map((row) => (
                <option key={row.id} value={row.id}>
                  {row.course.code} — {row.course.title} · {row.section_code} · {row.term.name}
                </option>
              ))}
            </select>
            <FieldError message={fieldErrors.offering_id} />
          </label>

          {form.offering_id && offeringExam.isPending ? (
            <SkeletonRows count={1} />
          ) : null}
          {form.offering_id && existingExam ? (
            <div className="rounded-xl border border-[#FDE68A] bg-[#FFFBEB] p-space-md text-body-sm text-[#92400E]">
              {t.examExists}
            </div>
          ) : null}

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.startsAt}</span>
              <input
                type="datetime-local"
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
                type="datetime-local"
                dir="ltr"
                className={inputCls}
                value={form.ends_at}
                onChange={(event) => setForm({ ...form, ends_at: event.target.value })}
              />
              <FieldError message={fieldErrors.ends_at} />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.classroom}</span>
              <input
                className={inputCls}
                value={form.classroom}
                onChange={(event) => setForm({ ...form, classroom: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{common.statusLabel}</span>
              <select
                className={inputCls}
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as ExamFormState['status'] })
                }
              >
                {EXAM_STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {examStatusLabels[value]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {formError ? <ErrorState error={formError} /> : null}

          <div className="flex items-center justify-end gap-space-sm pt-space-xs">
            <button type="button" className={btnSecondaryCls} onClick={() => setEditorOpen(false)}>
              {common.cancel}
            </button>
            <button
              type="button"
              className={btnPrimaryCls}
              disabled={save.isPending || !form.offering_id}
              onClick={submitExam}
            >
              {save.isPending
                ? common.saving
                : existingExam
                  ? t.saveExisting
                  : t.saveNew}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
