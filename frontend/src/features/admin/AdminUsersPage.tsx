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
import { useEffect, useState } from 'react'
import {
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  updateAdminUser,
} from '../../api/admin'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
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
import { toAsciiDigits, toPersianDigits } from '../../i18n/digits'
import { adminUsersPage as t, auth as authText, common } from '../../i18n/fa'
import { degreeLevelLabels, roleLabels } from '../../i18n/labels'
import { useAuth } from '../auth'
import type { Course, CourseOffering, Department } from '../../types/academic'
import type { AdminUser, AdminUserUpdatePayload, AdminUsersQuery } from '../../types/admin'
import type { UserRole } from '../../types/api'

const PAGE_SIZE = 10
const ROLES: UserRole[] = ['STUDENT', 'PROFESSOR', 'ADMIN', 'SUPERADMIN']
const PRIVILEGED: UserRole[] = ['ADMIN', 'SUPERADMIN']
const DEGREE_LEVELS = ['BACHELOR', 'MASTER', 'PHD'] as const

interface UserFormState {
  email: string
  password: string
  first_name: string
  last_name: string
  role: UserRole
  is_active: boolean
}

/** Student-only academic section (Part 3) — hidden for every other role. */
interface StudentFormState {
  student_number: string
  department_id: string
  degree_level: string
  entry_year: string
  passed: Array<{ code: string; title: string; credits: number }>
  current: Array<{
    id: number
    code: string
    title: string
    credits: number
    section: string
  }>
}

const EMPTY_FORM: UserFormState = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: '' as UserRole,
  is_active: true,
}

const EMPTY_STUDENT_FORM: StudentFormState = {
  student_number: '',
  department_id: '',
  degree_level: '',
  entry_year: '',
  passed: [],
  current: [],
}

function validateEmail(value: string): string | undefined {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim()) ? undefined : 'ایمیل معتبر وارد کنید.'
}

/** Small debounce so course/option searches hit the wire after typing stops. */
function useDebounced(value: string, ms = 300): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return debounced
}

interface MultiOption {
  key: string | number
  code: string
  title: string
  subtitle: string
}

/**
 * Searchable multi-select (Part 3.2 E/F). Options are already
 * filtered/excluded by the parent; the component renders the searchable list
 * and the selected chips, and reports toggles.
 */
function SearchableMultiSelect({
  label,
  hint,
  searchValue,
  onSearch,
  searchPlaceholder,
  options,
  selectedKeys,
  onToggle,
  onClear,
  loading,
  emptyLabel,
  disabled,
  testId,
}: {
  label: string
  hint?: string
  searchValue: string
  onSearch: (value: string) => void
  searchPlaceholder: string
  options: MultiOption[]
  selectedKeys: Set<string | number>
  onToggle: (option: MultiOption) => void
  onClear: () => void
  loading: boolean
  emptyLabel: string
  disabled: boolean
  testId: string
}) {
  const selected = options.filter((option) => selectedKeys.has(option.key))
  return (
    <div className="flex flex-col gap-space-xs text-body-sm" data-testid={testId}>
      <span className="font-semibold text-on-surface">{label}</span>
      {hint ? <span className="text-label-sm text-outline">{hint}</span> : null}
      <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
        <div className="border-b border-outline-variant p-space-sm">
          <SearchInput
            value={searchValue}
            onChange={onSearch}
            placeholder={searchPlaceholder}
            label={common.search}
          />
        </div>
        <div className="max-h-48 overflow-y-auto">
          {disabled ? (
            <div className="px-space-md py-space-sm text-label-md text-on-surface-variant">
              {t.pickDepartmentFirst}
            </div>
          ) : loading ? (
            <div className="px-space-md py-space-sm text-label-md text-on-surface-variant">
              {t.loadingOptions}
            </div>
          ) : options.length === 0 ? (
            <div className="px-space-md py-space-sm text-label-md text-on-surface-variant">
              {emptyLabel}
            </div>
          ) : (
            options.map((option) => (
              <label
                key={option.key}
                className="flex cursor-pointer items-center gap-space-sm border-b border-outline-variant/50 px-space-md py-space-sm text-body-sm last:border-b-0 hover:bg-surface-container-high"
              >
                <input
                  type="checkbox"
                  checked={selectedKeys.has(option.key)}
                  onChange={() => onToggle(option)}
                />
                <span className="font-body-sm">
                  <span dir="ltr" className="tnum">
                    {option.code}
                  </span>{' '}
                  — {option.title}
                </span>
                <span className="ms-auto shrink-0 text-label-sm text-on-surface-variant">
                  {option.subtitle}
                </span>
              </label>
            ))
          )}
        </div>
        {selected.length > 0 ? (
          <div className="flex flex-wrap items-center gap-space-xs border-t border-outline-variant p-space-sm">
            <span className="text-label-sm text-on-surface-variant">{t.selectedCourses}:</span>
            {selected.map((option) => (
              <Chip key={option.key} tone="primary">
                <span dir="ltr" className="tnum">
                  {option.code}
                </span>
              </Chip>
            ))}
            <button
              type="button"
              className={`${btnSecondaryCls} px-space-sm py-1 text-label-sm`}
              onClick={onClear}
            >
              {t.clearSelection}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
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
  const [studentForm, setStudentForm] = useState<StudentFormState>(EMPTY_STUDENT_FORM)
  const [formError, setFormError] = useState<unknown>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [target, setTarget] = useState<AdminUser | null>(null)
  const [passedSearch, setPassedSearch] = useState('')
  const [currentSearch, setCurrentSearch] = useState('')

  const debouncedPassedSearch = useDebounced(passedSearch)
  const debouncedCurrentSearch = useDebounced(currentSearch)
  const studentSectionOpen = !editing && form.role === 'STUDENT'

  // Student-section option sources (Part 3.2): department catalog for the
  // passed-course select, actual active-term offerings for the current one.
  const departmentsQuery = useQuery({
    queryKey: ['departments', 'options'] as const,
    queryFn: () => academicApi.departments({ page_size: 100 }),
    enabled: studentSectionOpen,
  })
  const departmentId = studentForm.department_id
  const coursesQuery = useQuery({
    queryKey: queryKeys.courses({
      department: departmentId ? Number(departmentId) : undefined,
      page_size: 100,
      search: debouncedPassedSearch || undefined,
    }),
    queryFn: () =>
      academicApi.courses({
        department: departmentId ? Number(departmentId) : undefined,
        page_size: 100,
        search: debouncedPassedSearch || undefined,
      }),
    enabled: studentSectionOpen && Boolean(departmentId),
  })
  const offeringsQuery = useQuery({
    queryKey: queryKeys.offerings({
      term: 'current',
      department: departmentId ? Number(departmentId) : undefined,
      page_size: 100,
      search: debouncedCurrentSearch || undefined,
    }),
    queryFn: () =>
      academicApi.offerings({
        term: 'current',
        department: departmentId ? Number(departmentId) : undefined,
        page_size: 100,
        search: debouncedCurrentSearch || undefined,
      }),
    enabled: studentSectionOpen && Boolean(departmentId),
  })

  const passedCourseCodes = new Set(studentForm.passed.map((course) => course.code))
  const passedOptions: MultiOption[] = (coursesQuery.data?.results ?? []).map((course) => ({
    key: course.code,
    code: course.code,
    title: course.title,
    subtitle: `${toPersianDigits(course.credits)} ${t.creditsUnit}`,
  }))
  const currentOptions: MultiOption[] = (offeringsQuery.data?.results ?? [])
    // A course cannot be simultaneously passed and currently taken.
    .filter((offering) => !passedCourseCodes.has(offering.course.code))
    .map((offering) => ({
      key: offering.id,
      code: offering.course.code,
      title: offering.course.title,
      subtitle: `${toPersianDigits(offering.course.credits)} ${t.creditsUnit} — ${t.groupUnit} ${toPersianDigits(offering.section_code)}`,
    }))
  const currentSelectedKeys = new Set(studentForm.current.map((offering) => offering.id))

  const togglePassed = (course: Course) => {
    setStudentForm((previous) => {
      const already = previous.passed.some((row) => row.code === course.code)
      return {
        ...previous,
        // Selecting a pass immediately removes it from the current-term list.
        passed: already
          ? previous.passed.filter((row) => row.code !== course.code)
          : [...previous.passed, { code: course.code, title: course.title, credits: course.credits }],
        current: previous.current.filter((row) => row.code !== course.code || already),
      }
    })
  }

  const toggleCurrent = (offering: CourseOffering) => {
    setStudentForm((previous) => {
      const already = previous.current.some((row) => row.id === offering.id)
      return {
        ...previous,
        current: already
          ? previous.current.filter((row) => row.id !== offering.id)
          : [
              ...previous.current,
              {
                id: offering.id,
                code: offering.course.code,
                title: offering.course.title,
                credits: offering.course.credits,
                section: offering.section_code,
              },
            ],
      }
    })
  }

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
    setForm({ ...EMPTY_FORM })
    setStudentForm(EMPTY_STUDENT_FORM)
    setPassedSearch('')
    setCurrentSearch('')
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
    setStudentForm(EMPTY_STUDENT_FORM)
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
      if (!form.role) {
        errors.role = t.selectRoleRequired
      } else if (form.role === 'STUDENT') {
        if (!studentForm.student_number.trim()) errors.student_number = t.studentNumberRequired
        if (!studentForm.department_id) errors.department_id = t.departmentRequired
        if (!studentForm.degree_level) errors.degree_level = t.degreeLevelRequired
        const entryYear = toAsciiDigits(studentForm.entry_year.trim())
        if (!entryYear) errors.entry_year = t.entryYearRequired
        else if (!/^[0-9]{4}$/.test(entryYear)) errors.entry_year = t.invalidEntryYear
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
      if (form.role === 'STUDENT') {
        // Student academic identity + selections (Part 3); the backend
        // validates and creates user/profile/enrollments atomically.
        payload.student_number = toAsciiDigits(studentForm.student_number.trim())
        payload.department_id = Number(studentForm.department_id)
        payload.degree_level = studentForm.degree_level
        payload.entry_year = toAsciiDigits(studentForm.entry_year.trim())
        payload.passed_course_codes = studentForm.passed.map((course) => course.code)
        payload.current_offering_ids = studentForm.current.map((offering) => offering.id)
      }
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
              onChange={(event) => {
                const role = event.target.value as UserRole
                setForm({ ...form, role })
                // Student academic fields exist only for the student role:
                // switching roles hides the section and clears its state.
                if (role !== 'STUDENT') setStudentForm(EMPTY_STUDENT_FORM)
              }}
            >
              <option value="">{t.selectRole}</option>
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

          {studentSectionOpen ? (
            <section
              className="flex flex-col gap-space-md rounded-xl border border-outline-variant bg-surface-container p-space-md"
              data-testid="student-academic-section"
            >
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.studentSection}</h3>
              <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
                <label className="flex flex-col gap-space-xs text-body-sm">
                  <span className="font-semibold text-on-surface">{t.studentNumber}</span>
                  <input
                    className={inputCls}
                    dir="ltr"
                    inputMode="numeric"
                    value={studentForm.student_number}
                    onChange={(event) =>
                      setStudentForm({ ...studentForm, student_number: event.target.value })
                    }
                  />
                  <FieldError message={fieldErrors.student_number} />
                </label>
                <label className="flex flex-col gap-space-xs text-body-sm">
                  <span className="font-semibold text-on-surface">{t.studentEntryYear}</span>
                  <input
                    className={inputCls}
                    dir="ltr"
                    inputMode="numeric"
                    placeholder="۱۴۰۲"
                    value={studentForm.entry_year}
                    onChange={(event) =>
                      setStudentForm({ ...studentForm, entry_year: event.target.value })
                    }
                  />
                  <span className="text-label-sm text-outline">{t.studentEntryYearHint}</span>
                  <FieldError message={fieldErrors.entry_year} />
                </label>
                <label className="flex flex-col gap-space-xs text-body-sm">
                  <span className="font-semibold text-on-surface">{t.studentDepartment}</span>
                  <select
                    className={inputCls}
                    value={studentForm.department_id}
                    onChange={(event) =>
                      setStudentForm({
                        ...studentForm,
                        department_id: event.target.value,
                        // New major → new catalog scope: selections no longer
                        // apply, so both course lists reset.
                        passed: [],
                        current: [],
                      })
                    }
                  >
                    <option value="">{t.pickDepartmentFirst}</option>
                    {(departmentsQuery.data?.results ?? []).map((department: Department) => (
                      <option key={department.id} value={department.id}>
                        {department.name}
                      </option>
                    ))}
                  </select>
                  <FieldError message={fieldErrors.department_id} />
                </label>
                <label className="flex flex-col gap-space-xs text-body-sm">
                  <span className="font-semibold text-on-surface">{t.studentDegreeLevel}</span>
                  <select
                    className={inputCls}
                    value={studentForm.degree_level}
                    onChange={(event) =>
                      setStudentForm({ ...studentForm, degree_level: event.target.value })
                    }
                  >
                    <option value="">{common.filterAll}</option>
                    {DEGREE_LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {degreeLevelLabels[level]}
                      </option>
                    ))}
                  </select>
                  <FieldError message={fieldErrors.degree_level} />
                </label>
              </div>

              <SearchableMultiSelect
                label={t.passedCourses}
                hint={t.passedCoursesHint}
                searchValue={passedSearch}
                onSearch={setPassedSearch}
                searchPlaceholder={t.searchCoursePlaceholder}
                options={passedOptions}
                selectedKeys={passedCourseCodes}
                onToggle={(option) => {
                  const course = (coursesQuery.data?.results ?? []).find(
                    (row) => row.code === option.key,
                  )
                  if (course) togglePassed(course)
                }}
                onClear={() => setStudentForm({ ...studentForm, passed: [] })}
                loading={coursesQuery.isFetching}
                emptyLabel={
                  departmentId ? t.noCourseOptions : t.pickDepartmentFirst
                }
                disabled={!departmentId}
                testId="passed-courses"
              />

              <SearchableMultiSelect
                label={t.currentCourses}
                hint={t.currentCoursesHint}
                searchValue={currentSearch}
                onSearch={setCurrentSearch}
                searchPlaceholder={t.searchCoursePlaceholder}
                options={currentOptions}
                selectedKeys={currentSelectedKeys}
                onToggle={(option) => {
                  const offering = (offeringsQuery.data?.results ?? []).find(
                    (row) => row.id === option.key,
                  )
                  if (offering) toggleCurrent(offering)
                }}
                onClear={() => setStudentForm({ ...studentForm, current: [] })}
                loading={offeringsQuery.isFetching}
                emptyLabel={
                  departmentId
                    ? t.noOfferingOptions
                    : t.pickDepartmentFirst
                }
                disabled={!departmentId}
                testId="current-courses"
              />
            </section>
          ) : null}

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

          <div className="sticky bottom-0 flex items-center justify-end gap-space-sm border-t border-outline-variant bg-surface-container-lowest pt-space-sm">
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
