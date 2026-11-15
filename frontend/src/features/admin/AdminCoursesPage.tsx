/**
 * /admin/courses — course management (docs/api/admin.md "Academic structure"
 * + "Offerings"). Full CRUD for courses, prerequisites (nested edges at
 * `/admin/courses/{id}/prerequisites/`, DELETE via `/admin/prerequisites/{id}/`)
 * and offerings (`/admin/offerings/` with nested schedule rows). Deletes of
 * offered courses (409) surface the backend's Persian message verbatim.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  addCoursePrerequisite,
  createAdminCourse,
  createAdminOffering,
  createOfferingSchedule,
  deleteAdminCourse,
  deleteAdminOffering,
  deleteCoursePrerequisite,
  deleteOfferingSchedule,
  fetchCoursePrerequisites,
  fetchOfferingSchedules,
  listAdminCourses,
  listAdminOfferings,
  listAdminProfessors,
  updateAdminCourse,
  updateAdminOffering,
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
  inputCls,
  tableCls,
  tdCls,
  thCls,
  cardCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { toAsciiDigits, toPersianDigits } from '../../i18n/digits'
import { adminCoursesPage as t, common } from '../../i18n/fa'
import { offeringStatusLabels } from '../../i18n/labels'
import type { AcademicTerm, Course, CourseOffering } from '../../types/academic'

const PAGE_SIZE = 10

/* ── Course form (create/edit) ────────────────────────────────────────── */

interface CourseFormState {
  code: string
  title: string
  credits: string
  course_type: string
  department_id: string
  active: boolean
}

export function AdminCoursesPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '')
  const [department, setDepartment] = useUrlState<string>('department', '')

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Course | null>(null)
  const [form, setForm] = useState<CourseFormState>(EMPTY_COURSE_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<unknown>(null)
  const [savedNote, setSavedNote] = useState('')
  const [prereqCourse, setPrereqCourse] = useState<Course | null>(null)
  const [offeringsCourse, setOfferingsCourse] = useState<Course | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Course | null>(null)

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
  const courses = useQuery({
    queryKey: queryKeys.adminCourses(query),
    queryFn: () => listAdminCourses(query),
    placeholderData: (previous) => previous,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'courses'] })
    void queryClient.invalidateQueries({ queryKey: ['courses'] })
    void queryClient.invalidateQueries({ queryKey: ['admin', 'count'] })
  }

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editing ? updateAdminCourse(editing.id, payload) : createAdminCourse(payload),
    onSuccess: () => {
      setFormOpen(false)
      setFormError(null)
      setSavedNote(editing ? common.updated : common.created)
      invalidate()
    },
    onError: (error) => setFormError(error),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteAdminCourse(id),
    onSuccess: () => {
      setDeleteTarget(null)
      invalidate()
    },
  })

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_COURSE_FORM)
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const openEdit = (row: Course) => {
    setEditing(row)
    setForm({
      code: row.code,
      title: row.title,
      credits: String(row.credits),
      course_type: row.course_type,
      department_id: String(row.department.id),
      active: row.active,
    })
    setFieldErrors({})
    setFormError(null)
    setFormOpen(true)
  }

  const submit = () => {
    const errors: Record<string, string> = {}
    if (!form.code.trim()) errors.code = common.requiredField
    if (!form.title.trim()) errors.title = common.requiredField
    const credits = Number(toAsciiDigits(form.credits.trim()))
    if (!Number.isInteger(credits) || credits < 1 || credits > 20) {
      errors.credits = t.unitsRange
    }
    if (!form.department_id) errors.department_id = common.requiredField
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setFormError(null)
    save.mutate({
      code: toAsciiDigits(form.code.trim()),
      title: form.title.trim(),
      credits,
      course_type: form.course_type.trim(),
      department_id: Number(form.department_id),
      active: form.active,
    })
  }

  const rows = courses.data?.results ?? []
  const hasFilters = Boolean(search || department)
  const clearFilters = () => {
    setSearch('')
    setDepartment('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-courses-page">
      <PageHeader
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <button type="button" className={btnPrimaryCls} onClick={openCreate}>
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
              add_circle
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
              {row.name}
            </option>
          ))}
        </FilterSelect>
        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}
        {courses.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(courses.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {courses.isPending ? (
        <SkeletonRows count={4} />
      ) : courses.isError ? (
        <ErrorState error={courses.error} onRetry={() => void courses.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState message={t.empty} hint={t.emptyHint} />
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.colCode}</th>
                  <th className={thCls}>{t.colTitle}</th>
                  <th className={thCls}>{t.colCredits}</th>
                  <th className={thCls}>{t.colDepartment}</th>
                  <th className={thCls}>{t.colState}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={`${tdCls} font-semibold tnum`} dir="ltr">
                      {row.code}
                    </td>
                    <td className={tdCls}>{row.title}</td>
                    <td className={`${tdCls} tnum`}>{toPersianDigits(row.credits)}</td>
                    <td className={tdCls}>{row.department.name}</td>
                    <td className={tdCls}>
                      {row.active ? (
                        <Chip tone="success">{common.active}</Chip>
                      ) : (
                        <Chip tone="danger">{common.inactive}</Chip>
                      )}
                    </td>
                    <td className={tdCls}>
                      <div className="flex flex-wrap items-center gap-space-xs">
                        <button
                          type="button"
                          className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                          onClick={() => setPrereqCourse(row)}
                        >
                          {t.prereqHeading}
                        </button>
                        <button
                          type="button"
                          className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                          onClick={() => setOfferingsCourse(row)}
                        >
                          {t.offeringsHeading}
                        </button>
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
                          onClick={() => setDeleteTarget(row)}
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
            count={courses.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}

      {/* Course create/edit */}
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
              <span className="font-semibold text-on-surface">{t.courseCode}</span>
              <input
                className={inputCls}
                dir="ltr"
                value={form.code}
                onChange={(event) => setForm({ ...form, code: event.target.value })}
              />
              <FieldError message={fieldErrors.code} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.courseTitle}</span>
              <input
                className={inputCls}
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
              <FieldError message={fieldErrors.title} />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-3">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{common.credits}</span>
              <input
                className={inputCls}
                dir="ltr"
                inputMode="numeric"
                value={form.credits}
                onChange={(event) => setForm({ ...form, credits: event.target.value })}
              />
              <FieldError message={fieldErrors.credits} />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm sm:col-span-2">
              <span className="font-semibold text-on-surface">{t.departmentField}</span>
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

          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.courseType}</span>
            <input
              className={inputCls}
              value={form.course_type}
              onChange={(event) => setForm({ ...form, course_type: event.target.value })}
            />
          </label>

          <label className="flex items-center gap-space-sm text-body-sm">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(event) => setForm({ ...form, active: event.target.checked })}
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

      {prereqCourse ? (
        <PrerequisitesModal
          course={prereqCourse}
          onClose={() => setPrereqCourse(null)}
        />
      ) : null}

      {offeringsCourse ? (
        <OfferingsModal
          course={offeringsCourse}
          onClose={() => setOfferingsCourse(null)}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={common.remove}
        message={t.deleteCourseBody}
        busy={remove.isPending}
        error={remove.error}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
      />
    </div>
  )
}

const EMPTY_COURSE_FORM: CourseFormState = {
  code: '',
  title: '',
  credits: '',
  course_type: '',
  department_id: '',
  active: true,
}

/* ── Prerequisites editor ─────────────────────────────────────────────── */

function PrerequisitesModal({ course, onClose }: { course: Course; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [selectValue, setSelectValue] = useState('')
  const [addingError, setAddingError] = useState<unknown>(null)
  const [deleteError, setDeleteError] = useState<unknown>(null)
  const [deleteEdge, setDeleteEdge] = useState<null | number>(null)

  const edges = useQuery({
    queryKey: queryKeys.coursePrerequisites(course.id),
    queryFn: () => fetchCoursePrerequisites(course.id),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: ['admin', 'courses', 'prerequisites', course.id],
    })
  }

  const add = useMutation({
    mutationFn: (prerequisiteCourseId: number) =>
      addCoursePrerequisite(course.id, prerequisiteCourseId),
    onSuccess: () => {
      setSelectValue('')
      setAddingError(null)
      invalidate()
    },
    onError: (error) => setAddingError(error),
  })

  // Course picker options: everything except this course and its existing
  // prerequisites. The endpoint paginates, so a generous page_size covers a
  // faculty-sized catalog; options stay grouped by department for scanning.
  const catalog = useQuery({
    queryKey: queryKeys.adminCourses({ page_size: 200 }),
    queryFn: () => listAdminCourses({ page_size: 200 }),
  })

  const removeEdge = useMutation({
    mutationFn: (edgeId: number) => deleteCoursePrerequisite(edgeId),
    onSuccess: () => {
      setDeleteEdge(null)
      setDeleteError(null)
      invalidate()
    },
    onError: (error) => setDeleteError(error),
  })

  const edgeRows = edges.data ?? []
  const edgeIds = new Set(edgeRows.map((edge) => edge.prerequisite_course.id))
  const candidates = (catalog.data?.results ?? []).filter(
    (row) => row.id !== course.id && !edgeIds.has(row.id),
  )

  return (
    <Modal open onClose={onClose} title={`${t.prereqHeading} — ${course.title}`} wide>
      <div className="flex flex-col gap-space-md">
        {edges.isPending ? (
          <SkeletonRows count={2} />
        ) : edges.isError ? (
          <ErrorState error={edges.error} onRetry={() => void edges.refetch()} />
        ) : edgeRows.length === 0 ? (
          <p className="m-0 text-body-sm text-on-surface-variant">{t.prereqEmpty}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
            {edgeRows.map((edge) => (
              <li
                key={edge.id}
                className="flex items-center justify-between gap-space-sm rounded-xl border border-outline-variant bg-surface-container-low/40 px-space-md py-space-sm"
              >
                <span className="text-body-sm text-on-surface">
                  <span className="tnum font-semibold" dir="ltr">
                    {edge.prerequisite_course.code}
                  </span>{' '}
                  {edge.prerequisite_course.title}
                  <span className="ms-2 text-label-sm text-outline tnum">
                    {toPersianDigits(edge.prerequisite_course.credits)} {common.credits}
                  </span>
                </span>
                <button
                  type="button"
                  className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                  disabled={removeEdge.isPending}
                  onClick={() => setDeleteEdge(edge.id)}
                >
                  {common.remove}
                </button>
              </li>
            ))}
          </ul>
        )}

        {deleteEdge !== null ? (
          <ConfirmDialog
            open
            title={common.remove}
            message={common.confirmDeleteBody}
            busy={removeEdge.isPending}
            error={deleteError}
            onCancel={() => setDeleteEdge(null)}
            onConfirm={() => deleteEdge !== null && removeEdge.mutate(deleteEdge)}
          />
        ) : null}

        <div className="flex flex-wrap items-end gap-space-sm border-t border-outline-variant pt-space-md">
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.prereqSelect}</span>
            <select
              className={`${inputCls} w-72`}
              value={selectValue}
              onChange={(event) => setSelectValue(event.target.value)}
            >
              <option value="">{common.notSetFallback}</option>
              {candidates.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.code} — {row.title}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={btnPrimaryCls}
            disabled={!selectValue || add.isPending}
            onClick={() => add.mutate(Number(selectValue))}
          >
            {t.prereqAdd}
          </button>
        </div>
        {addingError ? <ErrorState error={addingError} /> : null}
      </div>
    </Modal>
  )
}

/* ── Offerings + schedules editor ─────────────────────────────────────── */

interface OfferingFormState {
  term_id: string
  professor_id: string
  section_code: string
  capacity: string
  status: string
}

export function OfferingFormFields({
  form,
  setForm,
  terms,
  professors,
  showCapacity = true,
}: {
  form: OfferingFormState
  setForm: (next: OfferingFormState) => void
  terms: AcademicTerm[]
  professors: Array<{ id: number; first_name: string; last_name: string }>
  showCapacity?: boolean
}) {
  return (
    <>
      <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.offeringTerm}</span>
          <select
            className={inputCls}
            value={form.term_id}
            onChange={(event) => setForm({ ...form, term_id: event.target.value })}
          >
            <option value="">{common.notSetFallback}</option>
            {terms.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
                {row.is_current ? ' ★' : ''}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.offeringProfessor}</span>
          <select
            className={inputCls}
            value={form.professor_id}
            onChange={(event) => setForm({ ...form, professor_id: event.target.value })}
          >
            <option value="">{t.offeringProfessorNone}</option>
            {professors.map((row) => (
              <option key={row.id} value={row.id}>
                {row.first_name} {row.last_name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-1 gap-space-md sm:grid-cols-3">
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.offeringSection}</span>
          <input
            className={inputCls}
            dir="ltr"
            value={form.section_code}
            onChange={(event) => setForm({ ...form, section_code: event.target.value })}
          />
        </label>
        {showCapacity ? (
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.offeringCapacity}</span>
            <input
              className={inputCls}
              dir="ltr"
              inputMode="numeric"
              value={form.capacity}
              onChange={(event) => setForm({ ...form, capacity: event.target.value })}
            />
          </label>
        ) : null}
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.offeringStatus}</span>
          <select
            className={inputCls}
            value={form.status}
            onChange={(event) => setForm({ ...form, status: event.target.value })}
          >
            {(['OPEN', 'CLOSED', 'CANCELLED'] as const).map((value) => (
              <option key={value} value={value}>
                {offeringStatusLabels[value]}
              </option>
            ))}
          </select>
        </label>
      </div>
    </>
  )
}

function OfferingsModal({ course, onClose }: { course: Course; onClose: () => void }) {
  const [editingOffering, setEditingOffering] = useState<CourseOffering | null>(null)
  const [creatingOffering, setCreatingOffering] = useState(false)

  const query = { course: String(course.id), page_size: 100 }
  const offerings = useQuery({
    queryKey: queryKeys.adminOfferings(query),
    queryFn: () => listAdminOfferings(query),
  })

  const rows = offerings.data?.results ?? []

  return (
    <Modal open onClose={onClose} title={`${t.offeringsHeading} — ${course.title}`} wide>
      <div className="flex flex-col gap-space-md">
        <div className="flex items-center justify-between gap-space-sm">
          <span className="text-label-sm text-outline">
            {t.offeringEnrolled}: {toPersianDigits(offerings.data?.count ?? 0)}
          </span>
          <button type="button" className={btnPrimaryCls} onClick={() => setCreatingOffering(true)}>
            {t.offeringAdd}
          </button>
        </div>

        {offerings.isPending ? (
          <SkeletonRows count={2} />
        ) : offerings.isError ? (
          <ErrorState error={offerings.error} onRetry={() => void offerings.refetch()} />
        ) : rows.length === 0 ? (
          <p className="m-0 text-body-sm text-on-surface-variant">{t.scheduleEmpty}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.offeringTerm}</th>
                  <th className={thCls}>{t.offeringSection}</th>
                  <th className={thCls}>{t.offeringCapacity}</th>
                  <th className={thCls}>{t.offeringEnrolled}</th>
                  <th className={thCls}>{t.offeringStatus}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={tdCls}>{row.term.name}</td>
                    <td className={`${tdCls} tnum`} dir="ltr">
                      {row.section_code}
                    </td>
                    <td className={`${tdCls} tnum`}>{toPersianDigits(row.capacity)}</td>
                    <td className={`${tdCls} tnum`}>{toPersianDigits(row.enrolled_count)}</td>
                    <td className={tdCls}>{offeringStatusLabels[row.status]}</td>
                    <td className={tdCls}>
                      <button
                        type="button"
                        className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                        onClick={() => setEditingOffering(row)}
                      >
                        {common.edit}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {creatingOffering ? (
        <OfferingEditor
          courseId={course.id}
          offering={null}
          onClose={() => setCreatingOffering(false)}
        />
      ) : null}
      {editingOffering ? (
        <OfferingEditor
          courseId={course.id}
          offering={editingOffering}
          onClose={() => setEditingOffering(null)}
        />
      ) : null}
    </Modal>
  )
}

function OfferingEditor({
  courseId,
  offering,
  onClose,
}: {
  courseId: number
  offering: CourseOffering | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 100 }),
  })
  const professors = useQuery({
    queryKey: queryKeys.professors({ page_size: 100 }),
    queryFn: () => listAdminProfessors({ page_size: 100 }),
  })

  const [form, setForm] = useState<OfferingFormState>({
    term_id: String(offering?.term.id ?? ''),
    professor_id: offering?.professor ? String(offering.professor.id) : '',
    section_code: offering?.section_code ?? '',
    capacity: String(offering?.capacity ?? 0),
    status: offering?.status ?? 'OPEN',
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<unknown>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'offerings'] })
    void queryClient.invalidateQueries({ queryKey: ['offerings'] })
  }

  const save = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      offering
        ? updateAdminOffering(offering.id, payload)
        : createAdminOffering({ ...payload, course_id: courseId }),
    onSuccess: () => {
      setFormError(null)
      invalidate()
      onClose()
    },
    onError: (error) => setFormError(error),
  })

  const remove = useMutation({
    mutationFn: () => deleteAdminOffering(offering!.id),
    onSuccess: () => {
      invalidate()
      onClose()
    },
    onError: (error) => {
      // 409 (historical term / enrollments) must surface, not close silently.
      setConfirmDelete(false)
      setFormError(error)
    },
  })

  const submit = () => {
    const errors: Record<string, string> = {}
    if (!form.term_id) errors.term_id = common.requiredField
    if (!form.section_code.trim()) errors.section_code = common.requiredField
    const capacity = Number(toAsciiDigits(form.capacity.trim()))
    if (!Number.isInteger(capacity) || capacity < 0) errors.capacity = common.invalidNumber
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    save.mutate({
      term_id: Number(form.term_id),
      professor_id: form.professor_id ? Number(form.professor_id) : null,
      section_code: toAsciiDigits(form.section_code.trim()),
      capacity,
      status: form.status,
    })
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={offering ? `${t.offeringSection} — ${offering.course.code}` : t.offeringAdd}
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
        <OfferingFormFields
          form={form}
          setForm={setForm}
          terms={terms.data?.results ?? []}
          professors={professors.data?.results ?? []}
        />
        {fieldErrors.term_id ? <FieldError message={fieldErrors.term_id} /> : null}
        {fieldErrors.section_code ? <FieldError message={fieldErrors.section_code} /> : null}
        {fieldErrors.capacity ? <FieldError message={fieldErrors.capacity} /> : null}

        {offering && offering.id ? <SchedulesSection offeringId={offering.id} /> : null}

        {formError ? <ErrorState error={formError} /> : null}

        <div className="flex items-center justify-between gap-space-sm border-t border-outline-variant pt-space-sm">
          {offering ? (
            <button
              type="button"
              className={`${btnSecondaryCls} text-error`}
              disabled={remove.isPending}
              onClick={() => setConfirmDelete(true)}
            >
              {common.remove}
            </button>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-space-sm">
            <button type="button" className={btnSecondaryCls} onClick={onClose}>
              {common.cancel}
            </button>
            <button type="submit" className={btnPrimaryCls} disabled={save.isPending}>
              {save.isPending ? common.saving : common.save}
            </button>
          </div>
        </div>
      </form>

      <ConfirmDialog
        open={confirmDelete}
        title={common.remove}
        message={t.deleteOfferingBody}
        busy={remove.isPending}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => remove.mutate()}
      />
    </Modal>
  )
}

function SchedulesSection({ offeringId }: { offeringId: number }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ weekday: '5', start_time: '', end_time: '', classroom: '' })
  const [fieldError, setFieldError] = useState('')

  const schedules = useQuery({
    queryKey: queryKeys.offeringSchedules(offeringId),
    queryFn: () => fetchOfferingSchedules(offeringId),
  })

  const invalidate = () =>
    void queryClient.invalidateQueries({
      queryKey: ['admin', 'offerings', 'schedules', offeringId],
    })

  const add = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      createOfferingSchedule(offeringId, payload),
    onSuccess: () => {
      setFieldError('')
      setForm({ ...form, start_time: '', end_time: '', classroom: '' })
      invalidate()
    },
  })

  const removeRow = useMutation({
    mutationFn: (scheduleId: number) => deleteOfferingSchedule(scheduleId),
    onSuccess: invalidate,
  })

  const rows = schedules.data ?? []

  const submitSchedule = () => {
    if (!form.start_time || !form.end_time || form.start_time >= form.end_time) {
      setFieldError(t.scheduleTimeError)
      return
    }
    setFieldError('')
    add.mutate({
      weekday: Number(form.weekday),
      start_time: form.start_time,
      end_time: form.end_time,
      classroom: form.classroom.trim(),
    })
  }

  return (
    <section className="flex flex-col gap-space-sm rounded-xl border border-outline-variant p-space-md">
      <h3 className="m-0 text-headline-sm font-bold text-on-surface">{t.scheduleHeading}</h3>
      {schedules.isPending ? (
        <SkeletonRows count={2} />
      ) : rows.length === 0 ? (
        <p className="m-0 text-body-sm text-on-surface-variant">{t.scheduleEmpty}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-space-xs p-0">
          {rows.map((row) => (
            <li key={row.id} className="flex items-center justify-between gap-space-sm text-body-sm">
              <span>
                {row.weekday_display} · {row.start_time.slice(0, 5)} تا {row.end_time.slice(0, 5)}
                {row.classroom ? ` · ${row.classroom}` : ''}
              </span>
              <button
                type="button"
                className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                disabled={removeRow.isPending}
                onClick={() => removeRow.mutate(row.id)}
              >
                {common.remove}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-4">
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.scheduleWeekday}</span>
          <select
            className={inputCls}
            value={form.weekday}
            onChange={(event) => setForm({ ...form, weekday: event.target.value })}
          >
            <option value="5">شنبه</option>
            <option value="0">یکشنبه</option>
            <option value="1">دوشنبه</option>
            <option value="2">سه‌شنبه</option>
            <option value="3">چهارشنبه</option>
            <option value="4">پنجشنبه</option>
            <option value="6">جمعه</option>
          </select>
        </label>
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.scheduleStart}</span>
          <input
            type="time"
            dir="ltr"
            className={inputCls}
            value={form.start_time}
            onChange={(event) => setForm({ ...form, start_time: event.target.value })}
          />
        </label>
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.scheduleEnd}</span>
          <input
            type="time"
            dir="ltr"
            className={inputCls}
            value={form.end_time}
            onChange={(event) => setForm({ ...form, end_time: event.target.value })}
          />
        </label>
        <label className="flex flex-col gap-space-xs text-body-sm">
          <span className="font-semibold text-on-surface">{t.scheduleClassroom}</span>
          <input
            className={inputCls}
            value={form.classroom}
            onChange={(event) => setForm({ ...form, classroom: event.target.value })}
          />
        </label>
      </div>
      {fieldError ? <FieldError message={fieldError} /> : null}
      <div>
        <button type="button" className={btnPrimaryCls} disabled={add.isPending} onClick={submitSchedule}>
          {t.scheduleAdd}
        </button>
      </div>
      {add.error ? <ErrorState error={add.error} /> : null}
      {removeRow.isPending ? <span className="text-label-sm text-outline">{common.saving}</span> : null}
    </section>
  )
}
