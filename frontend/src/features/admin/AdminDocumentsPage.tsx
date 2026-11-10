/**
 * /admin/documents — document management (docs/api/documents.md contract).
 *
 * Multipart upload (POST /admin/documents/, multipart/form-data → 202 with
 * background processing), metadata/status PATCH, activate (supersedes the
 * previous active version), retry for failed processing, and DELETE with a
 * confirmation dialog. Status transitions are validated server-side; the
 * backend's Persian messages surface verbatim on 400/409.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  activateAdminDocument,
  deleteAdminDocument,
  listAdminDocuments,
  retryAdminDocument,
  updateAdminDocument,
  uploadAdminDocument,
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
  PersianNum,
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
import { adminDocumentsPage as t, common } from '../../i18n/fa'
import { documentStatusLabels, documentStatusTone } from '../../i18n/labels'
import { formatJalaliDate } from '../../i18n/jalali'
import type { AdminDocument, AdminDocumentsQuery, DocumentStatusValue } from '../../types/admin'

const PAGE_SIZE = 10
const STATUSES: DocumentStatusValue[] = [
  'UPLOADED',
  'VALIDATING',
  'PROCESSING',
  'INDEXED',
  'ACTIVE',
  'SUPERSEDED',
  'INACTIVE',
  'ARCHIVED',
  'FAILED',
]

interface UploadFormState {
  title: string
  document_type: string
  academic_year: string
  effective_from: string
  effective_to: string
  file: File | null
}

const EMPTY_UPLOAD: UploadFormState = {
  title: '',
  document_type: '',
  academic_year: '',
  effective_from: '',
  effective_to: '',
  file: null,
}

export function AdminDocumentsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '')
  const [statusFilter, setStatusFilter] = useUrlState<string>('status', '')
  const [typeFilter, setTypeFilter] = useUrlState<string>('type', '')
  const [yearFilter, setYearFilter] = useUrlState<string>('year', '')

  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadForm, setUploadForm] = useState<UploadFormState>(EMPTY_UPLOAD)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [uploadError, setUploadError] = useState<unknown>(null)
  const [savedNote, setSavedNote] = useState('')

  const [editTarget, setEditTarget] = useState<AdminDocument | null>(null)
  const [editForm, setEditForm] = useState({
    title: '',
    document_type: '',
    academic_year: '',
    effective_from: '',
    effective_to: '',
    status: '' as DocumentStatusValue | '',
  })
  const [editError, setEditError] = useState<unknown>(null)
  const [deleteTarget, setDeleteTarget] = useState<AdminDocument | null>(null)
  const [activateTarget, setActivateTarget] = useState<AdminDocument | null>(null)
  const [retryError, setRetryError] = useState<unknown>(null)

  const query: AdminDocumentsQuery = {
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    status: (statusFilter || undefined) as AdminDocumentsQuery['status'],
    document_type: typeFilter || undefined,
    academic_year: yearFilter || undefined,
  }
  const documents = useQuery({
    queryKey: queryKeys.adminDocuments(query),
    queryFn: () => listAdminDocuments(query),
    placeholderData: (previous) => previous,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin', 'documents'] })
    void queryClient.invalidateQueries({ queryKey: queryKeys.adminAnalytics() })
    void queryClient.invalidateQueries({ queryKey: ['admin', 'count'] })
  }

  const upload = useMutation({
    mutationFn: (form: FormData) => uploadAdminDocument(form),
    onSuccess: () => {
      setUploadOpen(false)
      setUploadForm(EMPTY_UPLOAD)
      setUploadError(null)
      setSavedNote(common.created)
      invalidate()
    },
    onError: (error) => setUploadError(error),
  })

  const editSave = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: Record<string, unknown> }) =>
      updateAdminDocument(id, patch),
    onSuccess: () => {
      setEditTarget(null)
      setEditError(null)
      setSavedNote(common.updated)
      invalidate()
    },
    onError: (error) => setEditError(error),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deleteAdminDocument(id),
    onSuccess: () => {
      setDeleteTarget(null)
      invalidate()
    },
  })

  const activate = useMutation({
    mutationFn: (id: number) => activateAdminDocument(id),
    onSuccess: () => {
      setActivateTarget(null)
      invalidate()
    },
    onError: (error) => {
      // Surface behind the still-open dialog state via the saved-note slot.
      setActivateTarget(null)
      setSavedNote('')
      setRetryError(error)
    },
  })

  const retry = useMutation({
    mutationFn: (id: number) => retryAdminDocument(id),
    onSuccess: () => {
      setRetryError(null)
      invalidate()
    },
    onError: (error) => {
      setRetryError(error)
      invalidate()
    },
  })

  const submitUpload = () => {
    const errors: Record<string, string> = {}
    if (!uploadForm.title.trim()) errors.title = common.requiredField
    if (!uploadForm.file) errors.file = common.requiredField
    else if (!uploadForm.file.name.toLowerCase().endsWith('.pdf')) errors.file = t.fileHint
    else if (uploadForm.file.size > 10 * 1024 * 1024) errors.file = t.fileHint
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }
    setFieldErrors({})
    setUploadError(null)
    const data = new FormData()
    data.append('title', uploadForm.title.trim())
    if (uploadForm.document_type.trim()) data.append('document_type', uploadForm.document_type.trim())
    if (uploadForm.academic_year.trim()) data.append('academic_year', uploadForm.academic_year.trim())
    if (uploadForm.effective_from) data.append('effective_from', uploadForm.effective_from)
    if (uploadForm.effective_to) data.append('effective_to', uploadForm.effective_to)
    data.append('file', uploadForm.file!)
    upload.mutate(data)
  }

  const openEdit = (row: AdminDocument) => {
    setEditTarget(row)
    setEditForm({
      title: row.title,
      document_type: row.document_type,
      academic_year: row.academic_year,
      effective_from: row.effective_from ?? '',
      effective_to: row.effective_to ?? '',
      status: row.status,
    })
    setEditError(null)
  }

  const submitEdit = () => {
    if (!editTarget) return
    if (!editForm.title.trim()) return
    editSave.mutate({
      id: editTarget.id,
      patch: {
        title: editForm.title.trim(),
        document_type: editForm.document_type.trim(),
        academic_year: editForm.academic_year.trim(),
        effective_from: editForm.effective_from || null,
        effective_to: editForm.effective_to || null,
        // Only send a status change when the admin actually moved it.
        ...(editForm.status !== editTarget.status && editForm.status
          ? { status: editForm.status }
          : {}),
      },
    })
  }

  const rows = documents.data?.results ?? []
  const hasFilters = Boolean(search || statusFilter || typeFilter || yearFilter)
  const clearFilters = () => {
    setSearch('')
    setStatusFilter('')
    setTypeFilter('')
    setYearFilter('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg" data-testid="admin-documents-page">
      <PageHeader
        title={t.title}
        subtitle={t.subtitle}
        actions={
          <button type="button" className={btnPrimaryCls} onClick={() => {
            setUploadError(null)
            setFieldErrors({})
            setUploadOpen(true)
          }}>
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
              upload_file
            </span>
            {t.uploadTitle}
          </button>
        }
      />

      {savedNote ? (
        <div role="status" className={`${cardCls} border-[#99F6E4] bg-[#F0FDFA] p-space-md text-body-sm text-[#0D9488]`}>
          {savedNote}
        </div>
      ) : null}
      {retryError ? <ErrorState error={retryError} onRetry={() => setRetryError(null)} /> : null}

      <FilterRow>
        <SearchInput
          value={search}
          onChange={(next) => {
            setSearch(next)
            setPage(1)
          }}
          placeholder={t.colTitle}
          label={common.search}
        />
        <FilterSelect
          icon="verified"
          label={t.filterStatus}
          value={statusFilter}
          onChange={(next) => {
            setStatusFilter(next)
            setPage(1)
          }}
        >
          <option value="">{common.filterAll}</option>
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {documentStatusLabels[value]}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect
          icon="description"
          label={t.filterType}
          value={typeFilter}
          onChange={(next) => {
            setTypeFilter(next)
            setPage(1)
          }}
        >
          <option value="">{t.typeAll}</option>
          {(documents.data ? [...new Set(rows.map((row) => row.document_type).filter(Boolean))] : []).map(
            (value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ),
          )}
        </FilterSelect>
        <input
          className={`${inputCls} w-40`}
          dir="ltr"
          placeholder={t.yearPlaceholder}
          value={yearFilter}
          aria-label={t.colYear}
          onChange={(event) => {
            setYearFilter(event.target.value)
            setPage(1)
          }}
        />
        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}
        {documents.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: <PersianNum value={documents.data.count} />
          </span>
        ) : null}
      </FilterRow>

      {documents.isPending ? (
        <SkeletonRows count={4} />
      ) : documents.isError ? (
        <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />
      ) : rows.length === 0 ? (
        <div className={`${cardCls} p-space-lg text-center text-body-md text-on-surface-variant`}>
          <p className="m-0">{t.empty}</p>
          <p className="m-0 text-label-sm text-outline">{t.emptyHint}</p>
        </div>
      ) : (
        <>
          <div className={`${cardCls} overflow-x-auto`}>
            <table className={tableCls}>
              <thead>
                <tr>
                  <th className={thCls}>{t.colTitle}</th>
                  <th className={thCls}>{t.colType}</th>
                  <th className={thCls}>{t.colYear}</th>
                  <th className={thCls}>{t.colVersion}</th>
                  <th className={thCls}>{t.colStatus}</th>
                  <th className={thCls}>{t.colUploaded}</th>
                  <th className={thCls}>{common.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={`${tdCls} font-semibold text-on-surface`}>
                      {row.title}
                      {row.status === 'FAILED' && row.processing_error ? (
                        <span className="ms-2 block text-label-sm text-error" title={t.processingError}>
                          {row.processing_error}
                        </span>
                      ) : null}
                    </td>
                    <td className={tdCls}>{row.document_type || common.notSetFallback}</td>
                    <td className={`${tdCls} tnum`}>{row.academic_year || common.notSetFallback}</td>
                    <td className={`${tdCls} tnum`}>
                      {t.versionOf} {toPersianDigits(row.version)}
                    </td>
                    <td className={tdCls}>
                      <Chip tone={documentStatusTone[row.status] ?? 'neutral'}>
                        {documentStatusLabels[row.status] ?? row.status}
                      </Chip>
                    </td>
                    <td className={`${tdCls} tnum`}>{formatJalaliDate(row.created_at)}</td>
                    <td className={tdCls}>
                      <div className="flex flex-wrap items-center gap-space-xs">
                        {(row.status === 'INDEXED' || row.status === 'INACTIVE') ? (
                          <button
                            type="button"
                            className={`${btnPrimaryCls} px-space-sm py-1 text-label-md`}
                            disabled={activate.isPending}
                            onClick={() => setActivateTarget(row)}
                          >
                            {t.activate}
                          </button>
                        ) : null}
                        {row.status === 'FAILED' ? (
                          <button
                            type="button"
                            className={`${btnSecondaryCls} px-space-sm py-1 text-label-md`}
                            disabled={retry.isPending}
                            onClick={() => retry.mutate(row.id)}
                          >
                            {t.retry}
                          </button>
                        ) : null}
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
            count={documents.data?.count ?? 0}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}

      {/* Upload dialog (multipart/form-data) */}
      <Modal open={uploadOpen} onClose={() => setUploadOpen(false)} title={t.uploadTitle}>
        <form
          className="flex flex-col gap-space-md"
          onSubmit={(event) => {
            event.preventDefault()
            submitUpload()
          }}
          noValidate
        >
          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.titleField}</span>
            <input
              className={inputCls}
              value={uploadForm.title}
              onChange={(event) => setUploadForm({ ...uploadForm, title: event.target.value })}
            />
            <FieldError message={fieldErrors.title} />
          </label>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.documentType}</span>
              <input
                className={inputCls}
                value={uploadForm.document_type}
                onChange={(event) =>
                  setUploadForm({ ...uploadForm, document_type: event.target.value })
                }
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.academicYear}</span>
              <input
                className={inputCls}
                dir="ltr"
                placeholder="1405-1406"
                value={uploadForm.academic_year}
                onChange={(event) =>
                  setUploadForm({ ...uploadForm, academic_year: event.target.value })
                }
              />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.effectiveFrom}</span>
              <input
                type="date"
                dir="ltr"
                className={inputCls}
                value={uploadForm.effective_from}
                onChange={(event) =>
                  setUploadForm({ ...uploadForm, effective_from: event.target.value })
                }
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.effectiveTo}</span>
              <input
                type="date"
                dir="ltr"
                className={inputCls}
                value={uploadForm.effective_to}
                onChange={(event) =>
                  setUploadForm({ ...uploadForm, effective_to: event.target.value })
                }
              />
            </label>
          </div>

          <label className="flex flex-col gap-space-xs text-body-sm">
            <span className="font-semibold text-on-surface">{t.fileField}</span>
            <input
              type="file"
              accept="application/pdf"
              className={inputCls}
              onChange={(event) =>
                setUploadForm({ ...uploadForm, file: event.target.files?.[0] ?? null })
              }
            />
            <FieldError message={fieldErrors.file} />
            <span className="text-label-sm text-outline">{t.fileHint}</span>
          </label>

          {uploadError ? <ErrorState error={uploadError} /> : null}

          <div className="flex items-center justify-end gap-space-sm pt-space-xs">
            <button type="button" className={btnSecondaryCls} onClick={() => setUploadOpen(false)}>
              {common.cancel}
            </button>
            <button type="submit" className={btnPrimaryCls} disabled={upload.isPending}>
              {upload.isPending ? t.uploading : t.uploadSubmit}
            </button>
          </div>
        </form>
      </Modal>

      {/* Metadata / status edit */}
      <Modal
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        title={t.editTitle}
      >
        {editTarget ? (
          <form
            className="flex flex-col gap-space-md"
            onSubmit={(event) => {
              event.preventDefault()
              submitEdit()
            }}
            noValidate
          >
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.titleField}</span>
              <input
                className={inputCls}
                value={editForm.title}
                onChange={(event) => setEditForm({ ...editForm, title: event.target.value })}
              />
            </label>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.documentType}</span>
              <input
                className={inputCls}
                value={editForm.document_type}
                onChange={(event) => setEditForm({ ...editForm, document_type: event.target.value })}
              />
            </label>
            <div className="grid grid-cols-1 gap-space-md sm:grid-cols-3">
              <label className="flex flex-col gap-space-xs text-body-sm">
                <span className="font-semibold text-on-surface">{t.academicYear}</span>
                <input
                  className={inputCls}
                  dir="ltr"
                  value={editForm.academic_year}
                  onChange={(event) =>
                    setEditForm({ ...editForm, academic_year: event.target.value })
                  }
                />
              </label>
              <label className="flex flex-col gap-space-xs text-body-sm">
                <span className="font-semibold text-on-surface">{t.effectiveFrom}</span>
                <input
                  type="date"
                  dir="ltr"
                  className={inputCls}
                  value={editForm.effective_from}
                  onChange={(event) =>
                    setEditForm({ ...editForm, effective_from: event.target.value })
                  }
                />
              </label>
              <label className="flex flex-col gap-space-xs text-body-sm">
                <span className="font-semibold text-on-surface">{t.effectiveTo}</span>
                <input
                  type="date"
                  dir="ltr"
                  className={inputCls}
                  value={editForm.effective_to}
                  onChange={(event) => setEditForm({ ...editForm, effective_to: event.target.value })}
                />
              </label>
            </div>
            <label className="flex flex-col gap-space-xs text-body-sm">
              <span className="font-semibold text-on-surface">{t.statusChange}</span>
              <select
                className={inputCls}
                value={editForm.status}
                onChange={(event) =>
                  setEditForm({ ...editForm, status: event.target.value as DocumentStatusValue })
                }
              >
                <option value={editTarget.status}>{documentStatusLabels[editTarget.status]}</option>
                {STATUSES.filter((value) => value !== editTarget.status).map((value) => (
                  <option key={value} value={value}>
                    {documentStatusLabels[value]}
                  </option>
                ))}
              </select>
            </label>

            {editError ? <ErrorState error={editError} /> : null}

            <div className="flex items-center justify-end gap-space-sm pt-space-xs">
              <button type="button" className={btnSecondaryCls} onClick={() => setEditTarget(null)}>
                {common.cancel}
              </button>
              <button type="submit" className={btnPrimaryCls} disabled={editSave.isPending}>
                {editSave.isPending ? common.saving : common.save}
              </button>
            </div>
          </form>
        ) : null}
      </Modal>

      <ConfirmDialog
        open={Boolean(activateTarget)}
        title={t.activate}
        message={t.activateBody}
        busy={activate.isPending}
        error={activate.error}
        onCancel={() => setActivateTarget(null)}
        onConfirm={() => activateTarget && activate.mutate(activateTarget.id)}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={common.remove}
        message={common.confirmDeleteBody}
        busy={remove.isPending}
        error={remove.error}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
      />
    </div>
  )
}
