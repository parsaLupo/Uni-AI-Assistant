/**
 * /admin/users — user + role management (docs/api/admin.md "Users").
 *
 * Full CRUD over `/admin/users/`: list with search/role/state filters and
 * pagination, create (password validated server-side by Django's validators),
 * edit (email immutable per contract), and DELETE = soft-deactivate with a
 * confirmation dialog. Role administration is RBAC-aware in the UI: granting
 * ADMIN/SUPERADMIN or touching a privileged account needs the caller to be
 * SUPERADMIN — the server still re-checks every rule (ADR-015).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  updateAdminUser,
} from '../../api/admin'
import { queryKeys } from '../../api/keys'
import {
  Chip,
  ConfirmDialog,
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
import { adminUsersPage as t, auth as authText, common } from '../../i18n/fa'
import { roleLabels } from '../../i18n/labels'
import { useAuth } from '../auth'
import type { AdminUser, AdminUserUpdatePayload, AdminUsersQuery } from '../../types/admin'
import type { UserRole } from '../../types/api'

const PAGE_SIZE = 10
const ROLES: UserRole[] = ['STUDENT', 'PROFESSOR', 'ADMIN', 'SUPERADMIN']
const PRIVILEGED: UserRole[] = ['ADMIN', 'SUPERADMIN']

interface UserFormState {
  email: string
  password: string
  first_name: string
  last_name: string
  role: UserRole
  is_active: boolean
}

const EMPTY_FORM: UserFormState = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'STUDENT',
  is_active: true,
}

function validateEmail(value: string): string | undefined {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim()) ? undefined : 'ایمیل معتبر وارد کنید.'
}

function FullName({ row }: { row: AdminUser }) {
  const name = `${row.first_name} ${row.last_name}`.trim()
  return name || common.notSetFallback
}

export function AdminUsersPage() {
  const { user: me } = useAuth()
  const isSuperAdmin = me?.role === 'SUPERADMIN'
  const queryClient = useQueryClient()

  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '')
  const [roleFilter, setRoleFilter] = useUrlState<string>('role', '')
  const [stateFilter, setStateFilter] = useUrlState<string>('state', '')

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<AdminUser | null>(null)
  const [form, setForm] = useState<UserFormState>(EMPTY_FORM)
  const [formError, setFormError] = useState<unknown>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [target, setTarget] = useState<AdminUser | null>(null)

  const query: AdminUsersQuery = {
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    role: (roleFilter || undefined) as AdminUsersQuery['role'],
    is_active: (stateFilter || undefined) as AdminUsersQuery['is_active'],
  }
  const users = useQuery({
    queryKey: queryKeys.adminUsers(query),
    queryFn: () => listAdminUsers(query),
    placeholderData: (previous) => previous,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    void queryClient.invalidateQueries({ queryKey: ['admin', 'count'] })
  }

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing
        ? updateAdminUser(editing.id, payload as AdminUserUpdatePayload)
        : createAdminUser(payload as never),
    onSuccess: () => {
      setFormOpen(false)
      setFormError(null)
      setFieldErrors({})
      invalidate()
    },
    onError: (error) => setFormError(error),
  })

  const deactivate = useMutation({
    mutationFn: (id: number) => deleteAdminUser(id),
    onSuccess: () => {
      setTarget(null)
      invalidate()
    },
  })

  const openCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_FORM, role: 'STUDENT' })
    setFormError(null)
    setFieldErrors({})
    setFormOpen(true)
  }

  const openEdit = (row: AdminUser) => {
    setEditing(row)
    setForm({
      email: row.email,
      password: '',
      first_name: row.first_name,
      last_name: row.last_name,
      role: row.role,
      is_active: row.is_active,
    })
    setFormError(null)
    setFieldErrors({})
    setFormOpen(true)
  }

  const submit = () => {
    const errors: Record<string, string> = {}
    // Email validates on create only: the contract keeps it immutable.
    if (!editing) {
      const emailError = validateEmail(form.email)
      if (emailError) errors.email = emailError
      if (!form.password || form.password.length < 8) {
        errors.password = 'گذرواژه حداقل ۸ نویسه است.'
      }
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setFormError(null)
    const payload: Record<string, unknown> = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      role: form.role,
      is_active: form.is_active,
    }
    if (!editing) {
      payload.email = form.email.trim().toLowerCase()
      payload.password = form.password
    }
    save.mutate(payload)
  }

  const rows = users.data?.results ?? []
  const hasFilters = Boolean(search || roleFilter || stateFilter)
  const clearFilters = () => {
    setSearch('')
    setRoleFilter('')
    setStateFilter('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-users-page">
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
          icon="badge"
          label={t.filterRole}
          value={roleFilter}
          onChange={(next) => {
            setRoleFilter(next)
            setPage(1)
          }}
        >
          <option value="">{common.filterAll}</option>
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {roleLabels[role]}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect
          icon="toggle_on"
          label={t.filterState}
          value={stateFilter}
          onChange={(next) => {
            setStateFilter(next)
            setPage(1)
          }}
        >
          <option value="">{t.stateAll}</option>
          <option value="true">{t.stateActive}</option>
          <option value="false">{t.stateInactive}</option>
        </FilterSelect>
        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}
        {users.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(users.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {users.isPending ? (
        <SkeletonRows count={4} />
      ) : users.isError ? (
        <ErrorState error={users.error} onRetry={() => void users.refetch()} />
      ) : rows.length === 0 ? (
        <div className={`${cardCls} p-space-lg text-center text-body-md text-on-surface-variant`}>
          {t.empty}
        </div>
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.colEmail}</th>
                  <th className={thCls}>{t.colName}</th>
                  <th className={thCls}>{t.colRole}</th>
                  <th className={thCls}>{t.colActive}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const protectedRow = PRIVILEGED.includes(row.role) && !isSuperAdmin
                  const isSelf = row.id === me?.id
                  return (
                    <tr key={row.id}>
                      <td className={`${tdCls} font-body-sm`} dir="ltr">
                        {row.email}
                      </td>
                      <td className={tdCls}>
                        <FullName row={row} />
                        {isSelf ? <Chip tone="primary">{roleLabels[me!.role]}</Chip> : null}
                      </td>
                      <td className={tdCls}>
                        <Chip tone={row.role === 'STUDENT' ? 'neutral' : 'primary'}>
                          {roleLabels[row.role]}
                        </Chip>
                      </td>
                      <td className={tdCls}>
                        {row.is_active ? (
                          <Chip tone="success">{t.stateActive}</Chip>
                        ) : (
                          <Chip tone="danger">{t.stateInactive}</Chip>
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
                            disabled={isSelf || protectedRow || deactivate.isPending}
                            onClick={() => {
                              setFormError(null)
                              setTarget(row)
                            }}
                            title={isSelf ? t.deactivateSelf : undefined}
                          >
                            {common.remove}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <PaginationBar
            count={users.data?.count ?? 0}
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
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.colEmail}</span>
            <input
              type="email"
              dir="ltr"
              className={inputCls}
              value={form.email}
              disabled={Boolean(editing)}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
            <FieldError message={fieldErrors.email} />
            {editing ? <span className="text-label-sm text-outline">ایمیل قابل ویرایش نیست.</span> : null}
          </label>

          {!editing ? (
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.password}</span>
              <input
                type="password"
                dir="ltr"
                className={inputCls}
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
              />
              <FieldError message={fieldErrors.password} />
              <span className="text-label-sm text-outline">{t.passwordHint}</span>
            </label>
          ) : null}

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{authText.firstName}</span>
              <input
                className={inputCls}
                value={form.first_name}
                onChange={(event) => setForm({ ...form, first_name: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{authText.lastName}</span>
              <input
                className={inputCls}
                value={form.last_name}
                onChange={(event) => setForm({ ...form, last_name: event.target.value })}
              />
            </label>
          </div>

          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.colRole}</span>
            <select
              className={inputCls}
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value as UserRole })}
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {roleLabels[role]}
                </option>
              ))}
            </select>
            {PRIVILEGED.includes(form.role) && !isSuperAdmin ? (
              <span className="text-label-sm text-[#B45309]">{t.roleHint}</span>
            ) : null}
          </label>

          {editing ? (
            <label className="flex items-center gap-space-sm text-body-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                disabled={Boolean(editing && editing.id === me?.id)}
              />
              <span className="font-semibold text-on-surface">{t.colActive}</span>
            </label>
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
        open={Boolean(target)}
        title={t.deactivateTitle}
        message={t.deactivateBody}
        busy={deactivate.isPending}
        error={deactivate.error}
        onCancel={() => setTarget(null)}
        onConfirm={() => target && deactivate.mutate(target.id)}
      />
    </div>
  )
}
