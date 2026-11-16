/**
 * /admin/announcements — announcement management (docs/api/admin.md). Full
 * CRUD over `/admin/announcements/`: title/body/priority, term + audience
 * (faculty/department) targeting, publish scheduling and expiry. Publishing
 * fans out user notifications server-side (Phase 12 behaviour, unchanged).
 * Expiry/broadcast semantics stay in Django — the form only sends ISO values.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { localInputToUtcIso, utcIsoToLocalInput } from '../../api/dates'
import {
  createAdminAnnouncement,
  deleteAdminAnnouncement,
  listAdminAnnouncements,
  updateAdminAnnouncement,
} from '../../api/admin'
import { academicApi } from '../../api/resources'
import { queryKeys } from '../../api/keys'
import {
  Chip,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  FieldError,
  FilterRow,
  FilterSelect,
  Modal,
  PageHeader,
  PaginationBar,
  SearchInput,
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
import { adminAnnouncementsPage as t, common } from '../../i18n/fa'
import { priorityLabels } from '../../i18n/labels'
import { formatJalaliDate } from '../../i18n/jalali'
import type { AnnouncementPriority } from '../../types/academic'

const PAGE_SIZE = 10
const PRIORITIES: AnnouncementPriority[] = ['LOW', 'NORMAL', 'HIGH', 'URGENT']

interface AnnouncementFormState {
  title: string
  body: string
  priority: AnnouncementPriority
  term_id: string
  audience_faculty_id: string
  audience_department_id: string
  published_at: string
  expires_at: string
  is_published: boolean
}

/** ISO (UTC) instant → the local `datetime-local` value the input expects. */
function inputDateTime(iso: string | null): string {
  return utcIsoToLocalInput(iso)
}

const EMPTY_FORM: AnnouncementFormState = {
  title: '',
  body: '',
  priority: 'NORMAL',
  term_id: '',
  audience_faculty_id: '',
  audience_department_id: '',
  published_at: '',
  expires_at: '',
  is_published: false,
}

export function AdminAnnouncementsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '')
  const [stateFilter, setStateFilter] = useUrlState<string>('state', '')
  const [termFilter, setTermFilter] = useUrlState<string>('term', '')

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<null | Record<string, unknown>>(null)
  const [form, setForm] = useState<AnnouncementFormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<unknown>(null)
  const [savedNote, setSavedNote] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; title: string } | null>(null)

  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 100 }),
  })
  const faculties = useQuery({
    queryKey: ['admin', 'faculties', 'options'] as const,
    queryFn: () => academicApi.adminFaculties({ page_size: 100 }),
  })
  const departments = useQuery({
    queryKey: queryKeys.departments({ page_size: 100 }),
    queryFn: () => academicApi.adminDepartments({ page_size: 100 }),
  })

  const query = {
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    term: termFilter || undefined,
    is_published: (stateFilter || undefined) as 'true' | 'false' | undefined,
  }
  const announcements = useQuery({
    queryKey: queryKeys.adminAnnouncements(query),
    queryFn: () => listAdminAnnouncements(query),
    placeholderData: (previous) => previous,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'announcements'] })
    void queryClient.invalidateQueries({ queryKey: ['announcements'] })
    void queryClient.invalidateQueries({ queryKey: ['admin', 'count'] })
    void queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing
        ? updateAdminAnnouncement(editing.id as number, payload)
        : createAdminAnnouncement(payload),
    onSuccess: () => {
      setFormOpen(false)
      setFormError(null)
      setSavedNote(editing ? common.updated : common.created)
      invalidate()
    },
    onError: (error) => setFormError(error),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteAdminAnnouncement(id),
    onSuccess: () => {
      setDeleteTarget(null)
      invalidate()
    },
  })

  interface AnnouncementRow {
    id: number
    title: string
    body: string
    priority: AnnouncementPriority
    term: { id: number; name: string } | null
    audience_faculty: { id: number; name: string } | null
    audience_department: { id: number; name: string } | null
    published_at: string | null
    expires_at: string | null
    is_published: boolean
  }

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const openEdit = (row: AnnouncementRow) => {
    setEditing(row as unknown as Record<string, unknown>)
    setForm({
      title: row.title,
      body: row.body,
      priority: row.priority,
      term_id: row.term ? String(row.term.id) : '',
      audience_faculty_id: row.audience_faculty ? String(row.audience_faculty.id) : '',
      audience_department_id: row.audience_department ? String(row.audience_department.id) : '',
      published_at: inputDateTime(row.published_at),
      expires_at: inputDateTime(row.expires_at),
      is_published: row.is_published,
    })
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const submit = () => {
    const errors: Record<string, string> = {}
    if (!form.title.trim()) errors.title = common.requiredField
    if (!form.body.trim()) errors.body = common.requiredField
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setFormError(null)
    save.mutate({
      title: form.title.trim(),
      body: form.body.trim(),
      priority: form.priority,
      term_id: form.term_id ? Number(form.term_id) : null,
      audience_faculty_id: form.audience_faculty_id ? Number(form.audience_faculty_id) : null,
      audience_department_id: form.audience_department_id
        ? Number(form.audience_department_id)
        : null,
      published_at: localInputToUtcIso(form.published_at),
      expires_at: localInputToUtcIso(form.expires_at),
      is_published: form.is_published,
    })
  }

  const rows = (announcements.data?.results ?? []) as unknown as AnnouncementRow[]
  const hasFilters = Boolean(search || stateFilter || termFilter)
  const clearFilters = () => {
    setSearch('')
    setStateFilter('')
    setTermFilter('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-announcements-page">
      <PageHeader
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <button type="button" className={btnPrimaryCls} onClick={openCreate}>
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
              campaign
            </span>
            {t.createTitle}
          </button>
        }
      />

      {savedNote ? (
        <div role="status" className={`${cardCls} border-[#99F6E4] bg-[#F0FDFA] p-space-md text-body-sm text-[#0D9488]`}>
          {savedNote}
        </div>
      ) : null}

      <FilterRow>
        <SearchInput
          value={search}
          onChange={(next) => {
            setSearch(next)
            setPage(1)
          }}
          placeholder={common.searchPlaceholder}
          label={common.search}
        />
        <FilterSelect
          icon="published_with_changes"
          label={t.filterState}
          value={stateFilter}
          onChange={(next) => {
            setStateFilter(next)
            setPage(1)
          }}
        >
          <option value="">{common.filterAll}</option>
          <option value="true">{t.statePublished}</option>
          <option value="false">{t.stateDraft}</option>
        </FilterSelect>
        <FilterSelect
          icon="calendar_month"
          label={common.filterTerm}
          value={termFilter}
          onChange={(next) => {
            setTermFilter(next)
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
        {announcements.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(announcements.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {announcements.isPending ? (
        <SkeletonRows count={4} />
      ) : announcements.isError ? (
        <ErrorState error={announcements.error} onRetry={() => void announcements.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={t.empty} hint={t.emptyHint} />
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{common.titleField}</th>
                  <th className={thCls}>{t.colPriority}</th>
                  <th className={thCls}>{t.colAudience}</th>
                  <th className={thCls}>{t.colPublished}</th>
                  <th className={thCls}>{t.colExpires}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={`${tdCls} font-semibold text-on-surface`}>
                      {row.title}
                      {row.is_published ? (
                        <span className="ms-2">
                          <Chip tone="success">{t.statePublished}</Chip>
                        </span>
                      ) : (
                        <span className="ms-2">
                          <Chip tone="neutral">{t.stateDraft}</Chip>
                        </span>
                      )}
                    </td>
                    <td className={tdCls}>
                      <Chip tone={row.priority === 'URGENT' || row.priority === 'HIGH' ? 'warning' : 'neutral'}>
                        {priorityLabels[row.priority]}
                      </Chip>
                    </td>
                    <td className={tdCls}>
                      {row.audience_department?.name ??
                        row.audience_faculty?.name ??
                        t.audienceEveryone}
                    </td>
                    <td className={`${tdCls} tnum`}>
                      {row.published_at ? formatJalaliDate(row.published_at) : common.notSetFallback}
                    </td>
                    <td className={`${tdCls} tnum`}>
                      {row.expires_at ? formatJalaliDate(row.expires_at) : common.notSetFallback}
                    </td>
                    <td className={tdCls}>
                      <div className="flex items-center gap-space-xs">
                        <button
                          type="button"
                          className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                          onClick={() => openEdit(row)}
                        >
                          {common.edit}
                        </button>
                        <button
                          type="button"
                          className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                          disabled={remove.isPending}
                          onClick={() =>
                            setDeleteTarget({ id: row.id, title: row.title })
                          }
                        >
                          {common.remove}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PaginationBar
            count={announcements.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? t.editTitle : t.createTitle}
        wide
      >
        <form
          className="flex flex-col gap-space-md"
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
          noValidate
        >
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.titleField}</span>
            <input
              className={inputCls}
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
            <FieldError message={fieldErrors.title} />
          </label>

          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.bodyField}</span>
            <textarea
              className={`${inputCls} min-h-28`}
              value={form.body}
              onChange={(event) => setForm({ ...form, body: event.target.value })}
            />
            <FieldError message={fieldErrors.body} />
          </label>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-4">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.priorityField}</span>
              <select
                className={inputCls}
                value={form.priority}
                onChange={(event) =>
                  setForm({ ...form, priority: event.target.value as AnnouncementPriority })
                }
              >
                {PRIORITIES.map((value) => (
                  <option key={value} value={value}>
                    {priorityLabels[value]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.termField}</span>
              <select
                className={inputCls}
                value={form.term_id}
                onChange={(event) => setForm({ ...form, term_id: event.target.value })}
              >
                <option value="">—</option>
                {(terms.data?.results ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.audienceFaculty}</span>
              <select
                className={inputCls}
                value={form.audience_faculty_id}
                onChange={(event) => setForm({ ...form, audience_faculty_id: event.target.value })}
              >
                <option value="">—</option>
                {(faculties.data?.results ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.audienceDepartment}</span>
              <select
                className={inputCls}
                value={form.audience_department_id}
                onChange={(event) =>
                  setForm({ ...form, audience_department_id: event.target.value })
                }
              >
                <option value="">—</option>
                {(departments.data?.results ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <span className="text-label-sm text-outline">{t.audienceHint}</span>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{common.publishedAt}</span>
              <input
                type="datetime-local"
                dir="ltr"
                className={inputCls}
                value={form.published_at}
                onChange={(event) => setForm({ ...form, published_at: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{common.expiresAt}</span>
              <input
                type="datetime-local"
                dir="ltr"
                className={inputCls}
                value={form.expires_at}
                onChange={(event) => setForm({ ...form, expires_at: event.target.value })}
              />
            </label>
          </div>
          <span className="text-label-sm text-outline">{t.expiresHint}</span>

          <label className="flex items-center gap-space-sm text-body-sm">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(event) => setForm({ ...form, is_published: event.target.checked })}
            />
            <span className="font-semibold text-on-surface">{t.isPublished}</span>
          </label>
          {form.is_published && !(editing?.is_published as boolean) ? (
            <span className="text-label-sm text-[#B45309]">{t.publishNotice}</span>
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

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={common.remove}
        message={t.deleteBody}
        busy={remove.isPending}
        error={remove.error}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
      />
    </div>
  )
}
