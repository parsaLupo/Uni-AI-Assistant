/**
 * /admin/professors — professor management (docs/api/admin.md). Full CRUD:
 * list with search + department filter, create/edit form (department select,
 * optional contact fields), delete with confirmation. Departments come from
 * the existing admin read (academicApi.adminDepartments).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  createAdminProfessor,
  deleteAdminProfessor,
  listAdminProfessors,
  updateAdminProfessor,
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
import { adminProfessorsPage as t, common } from '../../i18n/fa'
import type { Professor } from '../../types/academic'

const PAGE_SIZE = 10

const EMPTY_FORM: ProfessorFormState = {
  first_name: '',
  last_name: '',
  academic_title: '',
  email: '',
  office: '',
  website: '',
  bio: '',
  department_id: '',
  is_active: true,
}

interface ProfessorFormState {
  first_name: string
  last_name: string
  academic_title: string
  email: string
  office: string
  website: string
  bio: string
  department_id: string
  is_active: boolean
}

export function AdminProfessorsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '')
  const [department, setDepartment] = useUrlState<string>('department', '')

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Professor | null>(null)
  const [form, setForm] = useState<ProfessorFormState>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<unknown>(null)
  const [savedNote, setSavedNote] = useState('')
  const [target, setTarget] = useState<Professor | null>(null)

  const departments = useQuery({
    queryKey: queryKeys.departments({ page_size: 100 }),
    queryFn: () => academicApi.adminDepartments({ page_size: 100 }),
  })

  const query = {
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    department: department || undefined,
  }
  const professors = useQuery({
    queryKey: queryKeys.adminProfessors(query),
    queryFn: () => listAdminProfessors(query),
    placeholderData: (previous) => previous,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'professors'] })
    void queryClient.invalidateQueries({ queryKey: ['professors'] })
    void queryClient.invalidateQueries({ queryKey: ['admin', 'count'] })
  }

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing ? updateAdminProfessor(editing.id, payload) : createAdminProfessor(payload),
    onSuccess: () => {
      setFormOpen(false)
      setFormError(null)
      setSavedNote(editing ? common.updated : common.created)
      invalidate()
    },
    onError: (error) => setFormError(error),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteAdminProfessor(id),
    onSuccess: () => {
      setTarget(null)
      invalidate()
    },
  })

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const openEdit = (row: Professor) => {
    setEditing(row)
    setForm({
      first_name: row.first_name,
      last_name: row.last_name,
      academic_title: row.academic_title,
      email: row.email,
      office: row.office,
      website: row.website ?? '',
      bio: row.bio,
      department_id: String(row.department.id),
      is_active: row.is_active,
    })
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const submit = () => {
    const errors: Record<string, string> = {}
    if (!form.first_name.trim()) errors.first_name = common.requiredField
    if (!form.last_name.trim()) errors.last_name = common.requiredField
    if (!form.department_id) errors.department_id = common.requiredField
    if (form.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) {
      errors.email = 'ایمیل معتبر وارد کنید.'
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setFormError(null)
    save.mutate({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      academic_title: form.academic_title.trim(),
      email: form.email.trim(),
      office: form.office.trim(),
      website: form.website.trim(),
      bio: form.bio.trim(),
      department_id: Number(form.department_id),
      is_active: form.is_active,
    })
  }

  const rows = professors.data?.results ?? []
  const hasFilters = Boolean(search || department)
  const clearFilters = () => {
    setSearch('')
    setDepartment('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-professors-page">
      <PageHeader
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <button type="button" className={btnPrimaryCls} onClick={openCreate}>
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
              person_add
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

      <FilterRow>
        <SearchInput
          value={search}
          onChange={(next) => {
            setSearch(next)
            setPage(1)
          }}
          placeholder={t.searchPlaceholder}
          label={common.search}
        />
        <FilterSelect
          icon="account_tree"
          label={t.filterDepartment}
          value={department}
          onChange={(next) => {
            setDepartment(next)
            setPage(1)
          }}
          className="w-52"
        >
          <option value="">{t.departmentAll}</option>
          {(departments.data?.results ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.name} ({row.faculty.name})
            </option>
          ))}
        </FilterSelect>
        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}
        {professors.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(professors.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {professors.isPending ? (
        <SkeletonRows count={4} />
      ) : professors.isError ? (
        <ErrorState error={professors.error} onRetry={() => void professors.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={t.empty} />
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.colName}</th>
                  <th className={thCls}>{t.colTitle}</th>
                  <th className={thCls}>{t.colDepartment}</th>
                  <th className={thCls}>{t.colEmail}</th>
                  <th className={thCls}>{common.statusLabel}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={`${tdCls} font-semibold text-on-surface`}>
                      {row.first_name} {row.last_name}
                    </td>
                    <td className={tdCls}>{row.academic_title || common.notSetFallback}</td>
                    <td className={tdCls}>{row.department.name}</td>
                    <td className={`${tdCls} font-body-sm`} dir="ltr">
                      {row.email || common.notSetFallback}
                    </td>
                    <td className={tdCls}>
                      {row.is_active ? (
                        <Chip tone="success">{common.active}</Chip>
                      ) : (
                        <Chip tone="danger">{common.inactive}</Chip>
                      )}
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
                          onClick={() => setTarget(row)}
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
            count={professors.data?.count ?? 0}
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
      >
        <form
          className="flex flex-col gap-space-md"
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
          noValidate
        >
          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.firstName}</span>
              <input
                className={inputCls}
                value={form.first_name}
                onChange={(event) => setForm({ ...form, first_name: event.target.value })}
              />
              <FieldError message={fieldErrors.first_name} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.lastName}</span>
              <input
                className={inputCls}
                value={form.last_name}
                onChange={(event) => setForm({ ...form, last_name: event.target.value })}
              />
              <FieldError message={fieldErrors.last_name} />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.academicTitle}</span>
              <input
                className={inputCls}
                value={form.academic_title}
                onChange={(event) => setForm({ ...form, academic_title: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.filterDepartment}</span>
              <select
                className={inputCls}
                value={form.department_id}
                onChange={(event) => setForm({ ...form, department_id: event.target.value })}
              >
                <option value="">{common.notSetFallback}</option>
                {(departments.data?.results ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
              <FieldError message={fieldErrors.department_id} />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.emailField}</span>
              <input
                type="email"
                dir="ltr"
                className={inputCls}
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
              />
              <FieldError message={fieldErrors.email} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.office}</span>
              <input
                className={inputCls}
                value={form.office}
                onChange={(event) => setForm({ ...form, office: event.target.value })}
              />
            </label>
          </div>

          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.website}</span>
            <input
              type="url"
              dir="ltr"
              className={inputCls}
              value={form.website}
              onChange={(event) => setForm({ ...form, website: event.target.value })}
            />
          </label>

          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.bio}</span>
            <textarea
              className={`${inputCls} min-h-24`}
              value={form.bio}
              onChange={(event) => setForm({ ...form, bio: event.target.value })}
            />
          </label>

          <label className="flex items-center gap-space-sm text-body-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
            />
            <span className="font-semibold text-on-surface">{t.isActive}</span>
          </label>

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
        open={Boolean(target)}
        title={common.remove}
        message={t.deleteBody}
        busy={remove.isPending}
        error={remove.error}
        onCancel={() => setTarget(null)}
        onConfirm={() => target && remove.mutate(target.id)}
      />
    </div>
  )
}
