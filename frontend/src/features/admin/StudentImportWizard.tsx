/**
 * Admin → Users → «افزودن گروهی دانشجویان».
 *
 * Four steps mirror the API: download/choose a workbook → map sheets and
 * columns (never auto-confirmed when ambiguous) → preview + validate → confirm
 * and read the result. Validation is stateless: the chosen `File` is re-sent
 * on every step and `confirm` carries the preview's `file_hash`, so what is
 * executed is exactly what was reviewed.
 */

import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  confirmStudentImport,
  downloadIssuesCsv,
  downloadStudentImportTemplate,
  inspectStudentImport,
  listStudentImportReports,
  validateStudentImport,
} from '../../api/studentImport'
import type {
  ImportCreatedCredential,
  ImportInspection,
  ImportIssue,
  ImportMapping,
  ImportMode,
  ImportPreview,
  ImportResult,
  ImportRole,
  ImportSheetMapping,
} from '../../api/studentImport'
import {
  Chip,
  EmptyState,
  FieldError,
  Modal,
  SkeletonRows,
  btnPrimaryCls,
  btnSecondaryCls,
  cardCls,
  inputCls,
  tableCls,
  tdCls,
  thCls,
} from '../../components/ui'
import { formatJalaliDate } from '../../i18n/jalali'
import { toPersianDigits } from '../../i18n/digits'
import { adminStudentImport as t, common } from '../../i18n/fa'
import { ApiError as ApiErrorClass } from '../../api/client'

type Step = 'file' | 'map' | 'preview' | 'result'

const ROLE_FIELDS: Record<
  ImportRole,
  { label: string; required: string[]; optional: string[] }
> = {
  students: {
    label: t.roleStudents,
    required: [
      'student_id',
      'first_name',
      'last_name',
      'email',
      'department',
      'degree',
      'entry_year',
    ],
    optional: ['current_term', 'gpa'],
  },
  passed_courses: {
    label: t.rolePassed,
    required: ['student_id', 'course_code', 'grade', 'term'],
    optional: [],
  },
  current_enrollments: {
    label: t.roleEnrollments,
    required: ['student_id', 'course_code', 'group_code', 'term'],
    optional: [],
  },
}

const FIELD_LABELS: Record<string, string> = {
  student_id: 'کد دانشجویی',
  first_name: 'نام',
  last_name: 'نام خانوادگی',
  email: 'ایمیل',
  department: 'گروه آموزشی (رشته)',
  degree: 'مقطع',
  entry_year: 'سال ورود',
  current_term: 'شماره ترم جاری',
  gpa: 'معدل',
  course_code: 'کد درس',
  grade: 'نمره',
  term: 'ترم',
  group_code: 'شماره گروه',
}

const ROLES: ImportRole[] = ['students', 'passed_courses', 'current_enrollments']
const MODE_CREATE: ImportMode = 'create_only'
const MODE_UPSERT: ImportMode = 'upsert'
const SUMMARY_ERROR_LIMIT = 100

interface SheetState {
  name: string
  headers: string[]
  rowCount: number
  role: ImportRole | ''
  columns: Record<string, string>
  sampleRows: string[][]
  suggestedRole: ImportRole | null
}

function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field
}

function roleLabel(role: ImportRole): string {
  return ROLE_FIELDS[role].label
}

function outcomeLabel(outcome: string): string {
  switch (outcome) {
    case 'create':
    case 'created':
      return outcome === 'created' ? t.outcomeCreated : t.outcomeCreate
    case 'update':
    case 'updated':
      return outcome === 'updated' ? t.outcomeUpdated : t.outcomeUpdate
    case 'skip':
    case 'skipped':
      return outcome === 'skipped' ? t.outcomeSkipped : t.outcomeSkip
    default:
      return t.outcomeFailed
  }
}

function outcomeTone(outcome: string): 'success' | 'warning' | 'primary' | 'danger' | 'neutral' {
  switch (outcome) {
    case 'created':
      return 'success'
    case 'updated':
      return 'primary'
    case 'skipped':
      return 'neutral'
    case 'failed':
      return 'danger'
    case 'error':
      return 'danger'
    case 'skip':
      return 'warning'
    default:
      return 'primary'
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiErrorClass) return error.message
  if (error instanceof Error && error.message) return error.message
  return t.requestFailed
}

function identityColumns(role: ImportRole, headers: string[]): Record<string, string> {
  const allowed = [...ROLE_FIELDS[role].required, ...ROLE_FIELDS[role].optional]
  const columns: Record<string, string> = {}
  for (const field of allowed) {
    const header = headers.find((item) => item.trim() === field)
    if (header) columns[field] = header
  }
  return columns
}

function suggestedSheetState(sheet: ImportInspection['sheets'][number], taken: Set<ImportRole>): SheetState {
  const suggested = sheet.suggested_role
  const role = suggested && !taken.has(suggested) ? suggested : ''
  if (role) taken.add(role)
  return {
    name: sheet.name,
    headers: sheet.headers,
    rowCount: sheet.row_count,
    role,
    columns: role ? { ...sheet.suggested_mapping } : {},
    sampleRows: sheet.sample_rows,
    suggestedRole: suggested,
  }
}

function downloadCredentialsCsv(credentials: ImportCreatedCredential[]): void {
  const escape = (value: string) =>
    /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value
  const lines = [
    'email,password',
    ...credentials.map((row) => `${escape(row.email)},${escape(row.password)}`),
  ]
  const blob = new Blob(['\ufeff' + lines.join('\n')], {
    type: 'text/csv;charset=utf-8;',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'student-import-passwords.csv'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div
      className={`rounded-xl border border-outline-variant px-space-md py-space-sm ${
        tone ?? 'bg-surface-container-lowest'
      }`}
    >
      <div className="text-label-sm text-on-surface-variant">{label}</div>
      <div className="tnum text-headline-sm font-bold text-on-surface">
        {toPersianDigits(value)}
      </div>
    </div>
  )
}

function IssueTable({ issues, testId }: { issues: ImportIssue[]; testId: string }) {
  if (issues.length === 0) {
    return <p className="text-body-sm text-on-surface-variant">{t.noErrors}</p>
  }
  return (
    <div className="max-h-64 overflow-auto rounded-xl border border-outline-variant">
      <table className={tableCls} data-testid={testId}>
        <thead>
          <tr>
            <th className={thCls}>{t.colRow}</th>
            <th className={thCls}>{t.colName}</th>
            <th className={thCls}>فیلد</th>
            <th className={thCls}>پیام</th>
          </tr>
        </thead>
        <tbody>
          {issues.slice(0, SUMMARY_ERROR_LIMIT).map((issue, index) => (
            <tr key={`${issue.sheet}-${issue.row}-${issue.code}-${index}`}>
              <td className={`${tdCls} tnum whitespace-nowrap`}>
                {issue.sheet ? `${issue.sheet} / ${toPersianDigits(issue.row)}` : '—'}
              </td>
              <td className={`${tdCls} whitespace-nowrap`}>
                {issue.field ? fieldLabel(issue.field) : '—'}
              </td>
              <td className={`${tdCls} tnum whitespace-nowrap`}>{issue.code}</td>
              <td className={tdCls}>{issue.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function StudentImportWizard({
  open,
  onClose,
  onImported,
}: {
  open: boolean
  onClose: () => void
  onImported: () => void
}) {
  const [step, setStep] = useState<Step>('file')
  const [file, setFile] = useState<File | null>(null)
  const [sheets, setSheets] = useState<SheetState[]>([])
  const [mode, setMode] = useState<ImportMode>(MODE_CREATE)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [validatedMapping, setValidatedMapping] = useState<ImportMapping | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState<'inspect' | 'validate' | 'confirm' | 'template' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reports = useQuery({
    queryKey: ['admin', 'student-import', 'reports'],
    queryFn: () => listStudentImportReports(1),
    enabled: open,
    retry: false,
  })

  // Every opening starts a clean wizard; stale state from a previous run must
  // never leak into a new file (the hash check would reject it anyway).
  useEffect(() => {
    if (!open) return
    setStep('file')
    setFile(null)
    setSheets([])
    setMode(MODE_CREATE)
    setPreview(null)
    setValidatedMapping(null)
    setResult(null)
    setBusy(null)
    setError(null)
    setConfirmed(false)
    setCopied(null)
  }, [open])

  const mappingProblems = useMemo(() => {
    const problems: string[] = []
    const chosen = sheets.filter((sheet) => sheet.role !== '')
    const students = chosen.filter((sheet) => sheet.role === 'students')
    if (students.length !== 1) problems.push(t.mapErrorRole)
    const seen = new Set<ImportRole>()
    for (const sheet of chosen) {
      if (seen.has(sheet.role as ImportRole)) problems.push(t.mapErrorRole)
      seen.add(sheet.role as ImportRole)
      const missing = ROLE_FIELDS[sheet.role as ImportRole].required.filter(
        (field) => !sheet.columns[field],
      )
      if (missing.length > 0) {
        problems.push(
          t.mapErrorMissing
            .replace('{role}', roleLabel(sheet.role as ImportRole))
            .replace('{fields}', missing.map(fieldLabel).join('، ')),
        )
      }
    }
    return problems
  }, [sheets])

  const buildMapping = (source: SheetState[] = sheets): ImportMapping => ({
    sheets: source
      .filter((sheet) => sheet.role !== '')
      .map<ImportSheetMapping>((sheet) => ({
        role: sheet.role as ImportRole,
        sheet: sheet.name,
        columns: sheet.columns,
      })),
  })

  const resetToFile = () => {
    setStep('file')
    setPreview(null)
    setValidatedMapping(null)
    setConfirmed(false)
    setError(null)
  }

  const handleTemplate = async () => {
    setBusy('template')
    setError(null)
    try {
      await downloadStudentImportTemplate()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(null)
    }
  }

  const handleFile = async (picked: File | null) => {
    if (!picked) return
    if (!/\.xlsx$/i.test(picked.name)) {
      setError(t.fileTypeError)
      return
    }
    setFile(picked)
    setBusy('inspect')
    setError(null)
    setPreview(null)
    setConfirmed(false)
    try {
      const inspection = await inspectStudentImport(picked)
      const taken = new Set<ImportRole>()
      const next = inspection.sheets.map((sheet) => suggestedSheetState(sheet, taken))
      setSheets(next)
      setStep('map')
    } catch (cause) {
      setError(errorMessage(cause))
      setStep('file')
    } finally {
      setBusy(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const updateRole = (name: string, role: ImportRole | '') => {
    setSheets((current) =>
      current.map((sheet) => {
        if (sheet.name !== name) return sheet
        return {
          ...sheet,
          role,
          columns: role ? identityColumns(role, sheet.headers) : {},
        }
      }),
    )
    setPreview(null)
    setConfirmed(false)
  }

  const updateColumn = (name: string, field: string, header: string) => {
    setSheets((current) =>
      current.map((sheet) => {
        if (sheet.name !== name) return sheet
        const columns = { ...sheet.columns }
        if (header) columns[field] = header
        else delete columns[field]
        return { ...sheet, columns }
      }),
    )
    setPreview(null)
    setConfirmed(false)
  }

  const runValidate = async (nextMode: ImportMode) => {
    if (!file || mappingProblems.length > 0) return
    const mapping = buildMapping()
    setBusy('validate')
    setError(null)
    try {
      const body = await validateStudentImport(file, mapping, nextMode)
      setPreview(body)
      setValidatedMapping(mapping)
      setMode(nextMode)
      setConfirmed(false)
      setStep('preview')
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(null)
    }
  }

  const changeMode = (nextMode: ImportMode) => {
    if (nextMode === mode) return
    setMode(nextMode)
    if (preview) void runValidate(nextMode)
  }

  const runConfirm = async () => {
    if (!file || !preview || !validatedMapping || !confirmed) return
    setBusy('confirm')
    setError(null)
    try {
      const body = await confirmStudentImport(
        file,
        validatedMapping,
        mode,
        preview.file_hash,
      )
      setResult(body)
      setStep('result')
      onImported()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(null)
    }
  }

  const copyValue = async (value: string) => {
    try {
      await navigator.clipboard?.writeText(value)
      setCopied(value)
    } catch {
      setCopied(null)
    }
  }

  const summary = preview?.summary
  const steps: Array<{ key: Step; label: string }> = [
    { key: 'file', label: t.stepFile },
    { key: 'map', label: t.stepMap },
    { key: 'preview', label: t.stepPreview },
    { key: 'result', label: t.stepResult },
  ]
  const activeIndex = steps.findIndex((item) => item.key === step)

  return (
    <Modal open={open} onClose={onClose} title={t.title} wide>
      <div className="flex flex-col gap-space-md" data-testid="student-import-wizard">
        <p className="m-0 text-body-sm text-on-surface-variant">{t.subtitle}</p>

        <ol className="m-0 flex list-none flex-wrap items-center gap-space-sm p-0 text-label-sm">
          {steps.map((item, index) => (
            <li key={item.key} className="flex items-center gap-space-xs">
              <span
                className={`rounded-full px-space-sm py-1 ${
                  index === activeIndex
                    ? 'bg-primary-container text-on-primary'
                    : index < activeIndex
                      ? 'bg-[#DCFCE7] text-[#166534]'
                      : 'bg-surface-container-low text-on-surface-variant'
                }`}
              >
                {item.label}
              </span>
              {index < steps.length - 1 ? (
                <span aria-hidden="true" className="text-outline">
                  ←
                </span>
              ) : null}
            </li>
          ))}
        </ol>

        {error ? (
          <div
            role="alert"
            className="rounded-xl border border-[#FCA5A5] bg-[#FEF2F2] px-space-md py-space-sm text-body-sm text-[#991B1B]"
          >
            {error}
          </div>
        ) : null}

        {step === 'file' ? (
          <div className="flex flex-col gap-space-md">
            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.downloadTemplate}</h3>
              <p className="m-0 text-body-sm text-on-surface-variant">{t.templateHint}</p>
              <div>
                <button
                  type="button"
                  className={btnSecondaryCls}
                  onClick={handleTemplate}
                  disabled={busy === 'template'}
                >
                  <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
                    download
                  </span>
                  {busy === 'template' ? t.downloadingTemplate : t.downloadTemplate}
                </button>
              </div>
            </section>

            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.chooseFile}</h3>
              <p className="m-0 text-body-sm text-on-surface-variant">{t.fileHint}</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                data-testid="student-import-file-input"
                aria-label={t.chooseFile}
                onChange={(event) => void handleFile(event.target.files?.[0] ?? null)}
              />
              <div className="flex flex-wrap items-center gap-space-sm">
                <button
                  type="button"
                  className={btnPrimaryCls}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={busy === 'inspect'}
                >
                  <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
                    upload_file
                  </span>
                  {file ? t.replaceFile : t.chooseFile}
                </button>
                {file ? (
                  <span className="text-body-sm text-on-surface-variant">
                    {t.selectedFile}: <span className="font-semibold">{file.name}</span>
                  </span>
                ) : null}
                {busy === 'inspect' ? (
                  <span className="text-body-sm text-on-surface-variant">{t.reading}</span>
                ) : null}
              </div>
            </section>

            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.reportsTitle}</h3>
              {reports.isLoading ? (
                <SkeletonRows count={2} />
              ) : reports.isError ? (
                <EmptyState message={t.reportsEmpty} />
              ) : (reports.data?.results.length ?? 0) === 0 ? (
                <EmptyState message={t.reportsEmpty} />
              ) : (
                <ul className="m-0 flex list-none flex-col gap-space-xs p-0 text-body-sm">
                  {reports.data?.results.map((report) => (
                    <li
                      key={report.id}
                      className="flex flex-wrap items-center justify-between gap-space-sm border-b border-outline-variant pb-space-xs last:border-b-0"
                    >
                      <span className="tnum">{formatJalaliDate(report.created_at)}</span>
                      <span className="text-on-surface-variant">
                        {report.mode === MODE_UPSERT ? t.reportModeUpsert : t.reportModeCreate}
                      </span>
                      <span className="tnum">
                        {t.resultCreated}: {toPersianDigits(report.summary.created ?? 0)} ·{' '}
                        {t.resultUpdated}: {toPersianDigits(report.summary.updated ?? 0)} ·{' '}
                        {t.resultFailed}: {toPersianDigits(report.summary.failed ?? 0)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        ) : null}

        {step === 'map' ? (
          <div className="flex flex-col gap-space-md">
            <p className="m-0 text-body-sm text-on-surface-variant">{t.mappingIntro}</p>
            {sheets.map((sheet) => (
              <section
                key={sheet.name}
                className={`${cardCls} flex flex-col gap-space-sm p-space-md`}
                data-testid={`import-sheet-${sheet.name}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-space-sm">
                  <h3 className="m-0 text-title-md font-bold text-on-surface">
                    {t.sheetMeta
                      .replace('{sheet}', sheet.name)
                      .replace('{rows}', String(sheet.rowCount))}
                  </h3>
                  <label className="flex items-center gap-space-xs text-label-md">
                    <span className="text-on-surface-variant">{t.roleLabel}</span>
                    <select
                      className={`${inputCls} w-56 py-2`}
                      value={sheet.role}
                      aria-label={`${t.roleLabel} ${sheet.name}`}
                      data-testid={`import-role-${sheet.name}`}
                      onChange={(event) =>
                        updateRole(sheet.name, event.target.value as ImportRole | '')
                      }
                    >
                      <option value="">{t.roleNone}</option>
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {roleLabel(role)}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {sheet.role ? (
                  <>
                    <div className="grid grid-cols-1 gap-space-sm md:grid-cols-2">
                      {[
                        ...ROLE_FIELDS[sheet.role].required.map((field) => ({
                          field,
                          required: true,
                        })),
                        ...ROLE_FIELDS[sheet.role].optional.map((field) => ({
                          field,
                          required: false,
                        })),
                      ].map((item) => (
                        <label key={item.field} className="flex flex-col gap-1 text-label-md">
                          <span className="flex items-center gap-1 text-on-surface">
                            {fieldLabel(item.field)}
                            {item.required ? (
                              <Chip tone="danger">{t.requiredBadge}</Chip>
                            ) : null}
                          </span>
                          <select
                            className={`${inputCls} py-2`}
                            value={sheet.columns[item.field] ?? ''}
                            aria-label={`${fieldLabel(item.field)} — ${sheet.name}`}
                            data-testid={`import-column-${sheet.name}-${item.field}`}
                            onChange={(event) =>
                              updateColumn(sheet.name, item.field, event.target.value)
                            }
                          >
                            <option value="">{t.notMapped}</option>
                            {sheet.headers.map((header, index) => (
                              <option key={`${header}-${index}`} value={header}>
                                {header}
                              </option>
                            ))}
                          </select>
                        </label>
                      ))}
                    </div>
                    {sheet.sampleRows.length > 0 ? (
                      <details className="text-label-sm text-on-surface-variant">
                        <summary className="cursor-pointer">{t.sampleRows}</summary>
                        <div className="mt-space-xs overflow-auto">
                          <table className={tableCls}>
                            <thead>
                              <tr>
                                {sheet.headers.map((header, index) => (
                                  <th key={`${header}-${index}`} className={thCls}>
                                    {header}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {sheet.sampleRows.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                  {sheet.headers.map((_, cellIndex) => (
                                    <td key={cellIndex} className={tdCls}>
                                      {row[cellIndex] ?? ''}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    ) : null}
                  </>
                ) : (
                  <p className="m-0 text-label-sm text-on-surface-variant">{t.roleNone}</p>
                )}
              </section>
            ))}

            {mappingProblems.length > 0 ? (
              <div className="flex flex-col gap-1">
                {mappingProblems.map((problem) => (
                  <FieldError key={problem} message={problem} />
                ))}
              </div>
            ) : null}

            <div className="flex items-center justify-between gap-space-sm">
              <button type="button" className={btnSecondaryCls} onClick={resetToFile}>
                {t.back}
              </button>
              <button
                type="button"
                className={btnPrimaryCls}
                disabled={busy === 'validate' || mappingProblems.length > 0}
                onClick={() => void runValidate(mode)}
              >
                {busy === 'validate' ? t.validating : t.validate}
              </button>
            </div>
          </div>
        ) : null}

        {step === 'preview' && preview && summary ? (
          <div className="flex flex-col gap-space-md">
            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.summaryTitle}</h3>
              <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-4">
                <Stat label={t.statTotal} value={summary.students_total} />
                <Stat label={t.statValid} value={summary.students_valid} tone="bg-[#F0FDF4]" />
                <Stat label={t.statInvalid} value={summary.students_invalid} tone="bg-[#FEF2F2]" />
                <Stat label={t.statCreate} value={summary.will_create} />
                <Stat label={t.statUpdate} value={summary.will_update} />
                <Stat label={t.statSkip} value={summary.will_skip} />
                <Stat label={t.statPassed} value={summary.passed_valid} />
                <Stat label={t.statEnrollments} value={summary.enrollments_valid} />
                <Stat label={t.statDuplicates} value={summary.duplicate_rows} />
                <Stat label={t.statErrors} value={summary.error_count} tone="bg-[#FEF2F2]" />
                <Stat label={t.statWarnings} value={summary.warning_count} tone="bg-[#FFFBEB]" />
              </div>

              <fieldset className="m-0 flex flex-col gap-space-xs border-0 p-0">
                <legend className="mb-1 text-label-md font-semibold text-on-surface">
                  {t.modeTitle}
                </legend>
                <label className="flex items-start gap-space-xs text-body-sm">
                  <input
                    type="radio"
                    name="student-import-mode"
                    checked={mode === MODE_CREATE}
                    onChange={() => changeMode(MODE_CREATE)}
                  />
                  <span>
                    <span className="font-semibold text-on-surface">{t.modeCreate}</span>
                    <span className="block text-on-surface-variant">{t.modeCreateHint}</span>
                  </span>
                </label>
                <label className="flex items-start gap-space-xs text-body-sm">
                  <input
                    type="radio"
                    name="student-import-mode"
                    checked={mode === MODE_UPSERT}
                    onChange={() => changeMode(MODE_UPSERT)}
                  />
                  <span>
                    <span className="font-semibold text-on-surface">{t.modeUpsert}</span>
                    <span className="block text-on-surface-variant">{t.modeUpsertHint}</span>
                  </span>
                </label>
              </fieldset>
            </section>

            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <div className="flex flex-wrap items-center justify-between gap-space-sm">
                <h3 className="m-0 text-title-md font-bold text-on-surface">{t.errorsTitle}</h3>
                <button
                  type="button"
                  className={btnSecondaryCls}
                  onClick={() => downloadIssuesCsv(preview.errors)}
                  disabled={preview.errors.length === 0}
                >
                  {t.downloadErrors}
                </button>
              </div>
              <IssueTable issues={preview.errors} testId="import-errors" />
              {preview.details_truncated ? (
                <p className="m-0 text-label-sm text-on-surface-variant">{t.truncated}</p>
              ) : null}
            </section>

            {preview.warnings.length > 0 ? (
              <details className={`${cardCls} p-space-md`}>
                <summary className="cursor-pointer text-title-md font-bold text-on-surface">
                  {t.warningsTitle} ({toPersianDigits(preview.warnings.length)})
                </summary>
                <div className="mt-space-sm">
                  <IssueTable issues={preview.warnings} testId="import-warnings" />
                </div>
              </details>
            ) : null}

            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.studentsTitle}</h3>
              <div className="max-h-72 overflow-auto rounded-xl border border-outline-variant">
                <table className={tableCls} data-testid="import-students">
                  <thead>
                    <tr>
                      <th className={thCls}>{t.colRow}</th>
                      <th className={thCls}>{t.colName}</th>
                      <th className={thCls}>{t.colStudentId}</th>
                      <th className={thCls}>{t.colDepartment}</th>
                      <th className={thCls}>{t.colOutcome}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.students.map((row) => (
                      <tr key={`${row.row}-${row.student_id}`}>
                        <td className={`${tdCls} tnum`}>{toPersianDigits(row.row)}</td>
                        <td className={tdCls}>{row.full_name || '—'}</td>
                        <td className={`${tdCls} tnum`}>{row.student_id || '—'}</td>
                        <td className={tdCls}>{row.department || '—'}</td>
                        <td className={tdCls}>
                          <Chip tone={outcomeTone(row.outcome)}>
                            {outcomeLabel(row.outcome)}
                          </Chip>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {preview.students.some((row) => row.changes.length > 0) ? (
              <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
                <h3 className="m-0 text-title-md font-bold text-on-surface">{t.changesTitle}</h3>
                <ul className="m-0 flex list-none flex-col gap-space-xs p-0 text-body-sm">
                  {preview.students
                    .filter((row) => row.changes.length > 0)
                    .map((row) => (
                      <li key={`changes-${row.row}-${row.student_id}`}>
                        <span className="font-semibold text-on-surface">
                          {row.full_name} ({row.student_id})
                        </span>
                        <ul className="m-0 mt-1 list-none p-0 text-on-surface-variant">
                          {row.changes.map((change) => (
                            <li key={`${row.student_id}-${change.field}`}>
                              {t.changeLine
                                .replace('{label}', change.label)
                                .replace('{from}', String(change.from ?? t.emptyValue))
                                .replace('{to}', String(change.to ?? t.emptyValue))}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                </ul>
              </section>
            ) : null}

            <label className="flex items-start gap-space-xs text-body-sm text-on-surface">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
                data-testid="import-confirm-check"
              />
              <span>{t.confirmCheck}</span>
            </label>

            <div className="flex items-center justify-between gap-space-sm">
              <button type="button" className={btnSecondaryCls} onClick={() => setStep('map')}>
                {t.back}
              </button>
              <button
                type="button"
                className={btnPrimaryCls}
                disabled={!confirmed || busy === 'confirm'}
                onClick={() => void runConfirm()}
              >
                {busy === 'confirm' ? t.confirming : t.confirm}
              </button>
            </div>
          </div>
        ) : null}

        {step === 'result' && result ? (
          <div className="flex flex-col gap-space-md">
            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">{t.resultTitle}</h3>
              <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-4">
                <Stat label={t.resultCreated} value={result.summary.created} tone="bg-[#F0FDF4]" />
                <Stat label={t.resultUpdated} value={result.summary.updated} />
                <Stat label={t.resultSkipped} value={result.summary.skipped} />
                <Stat label={t.resultFailed} value={result.summary.failed} tone="bg-[#FEF2F2]" />
                <Stat label={t.resultPassed} value={result.summary.passed_imported} />
                <Stat label={t.resultEnrollments} value={result.summary.enrollments_imported} />
              </div>
              {result.errors.length > 0 ? (
                <button
                  type="button"
                  className={btnSecondaryCls}
                  onClick={() => downloadIssuesCsv(result.errors)}
                >
                  {t.downloadErrors}
                </button>
              ) : null}
            </section>

            <section className={`${cardCls} flex flex-col gap-space-sm p-space-md`}>
              <h3 className="m-0 text-title-md font-bold text-on-surface">
                {t.credentialsTitle}
              </h3>
              {result.created_credentials.length === 0 ? (
                <p className="m-0 text-body-sm text-on-surface-variant">{t.credentialsEmpty}</p>
              ) : (
                <>
                  <p className="m-0 rounded-xl border border-[#FCD34D] bg-[#FFFBEB] px-space-md py-space-sm text-body-sm text-[#92400E]">
                    {t.credentialsWarning}
                  </p>
                  <div className="max-h-64 overflow-auto rounded-xl border border-outline-variant">
                    <table className={tableCls} data-testid="import-credentials">
                      <thead>
                        <tr>
                          <th className={thCls}>{t.colStudentId}</th>
                          <th className={thCls}>{t.credentialsTitle}</th>
                          <th className={thCls}> </th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.created_credentials.map((row) => (
                          <tr key={row.email}>
                            <td className={`${tdCls} tnum`}>{row.email}</td>
                            <td className={`${tdCls} tnum font-mono`}>{row.password}</td>
                            <td className={tdCls}>
                              <button
                                type="button"
                                className={`${btnSecondaryCls} px-space-sm py-1 text-label-sm`}
                                onClick={() => void copyValue(row.password)}
                              >
                                {copied === row.password ? t.copied : t.copy}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div>
                    <button
                      type="button"
                      className={btnSecondaryCls}
                      onClick={() => downloadCredentialsCsv(result.created_credentials)}
                    >
                      {t.downloadCredentials}
                    </button>
                  </div>
                </>
              )}
            </section>

            <div className="flex justify-end">
              <button type="button" className={btnPrimaryCls} onClick={onClose}>
                {t.done}
              </button>
            </div>
          </div>
        ) : null}

        {step !== 'result' ? (
          <div className="flex justify-end border-t border-outline-variant pt-space-sm">
            <button type="button" className={btnSecondaryCls} onClick={onClose}>
              {common.cancel}
            </button>
          </div>
        ) : null}
      </div>
    </Modal>
  )
}
