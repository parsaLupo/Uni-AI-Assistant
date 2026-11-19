/**
 * Bulk student import API (docs/api/admin.md, "Bulk student import").
 *
 * The backend is stateless: the same file is re-sent for inspect, validate and
 * confirm, and `confirm` must carry the `file_hash` the preview returned. That
 * is why every step takes the `File` rather than an upload id.
 */

import { buildApiUrl, requestJson, toApiError } from './client'
import { getAccessToken } from '../features/auth/session'
import type { Paginated } from '../types/api'

export type ImportRole = 'students' | 'passed_courses' | 'current_enrollments'
export type ImportMode = 'create_only' | 'upsert'
export type ImportOutcome =
  | 'create'
  | 'update'
  | 'skip'
  | 'error'
  | 'created'
  | 'updated'
  | 'skipped'
  | 'failed'

export interface ImportSheetInspection {
  name: string
  row_count: number
  headers: string[]
  suggested_role: ImportRole | null
  suggested_mapping: Record<string, string>
  sample_rows: string[][]
}

export interface ImportInspection {
  file_hash: string
  sheets: ImportSheetInspection[]
}

/** One logical sheet selection: which physical sheet feeds which role. */
export interface ImportSheetMapping {
  role: ImportRole
  sheet: string
  columns: Record<string, string>
}

export interface ImportMapping {
  sheets: ImportSheetMapping[]
}

export interface ImportIssue {
  sheet: string
  row: number
  field: string
  code: string
  message: string
}

export interface ImportChange {
  field: string
  label: string
  from: string | number | null
  to: string | number | null
}

export interface ImportStudentRow {
  row: number
  student_id: string
  email: string
  full_name: string
  department: string
  degree: string
  entry_year: string
  current_term: number | null
  gpa: string | null
  outcome: ImportOutcome
  changes: ImportChange[]
  errors: ImportIssue[]
  warnings: ImportIssue[]
}

export interface ImportHistoryRow {
  row: number
  kind: 'passed' | 'enrollment'
  student_id: string
  course_code: string
  term: string
  group_code?: string
  grade?: string | null
  errors: ImportIssue[]
  warnings: ImportIssue[]
}

export interface ImportSummary {
  students_total: number
  students_valid: number
  students_invalid: number
  students_existing: number
  will_create: number
  will_update: number
  will_skip: number
  passed_total: number
  passed_valid: number
  passed_invalid: number
  enrollments_total: number
  enrollments_valid: number
  enrollments_invalid: number
  duplicate_rows: number
  error_count: number
  warning_count: number
}

export interface ImportPreview {
  file_hash: string
  mode: ImportMode
  summary: ImportSummary
  students: ImportStudentRow[]
  passed_courses: ImportHistoryRow[]
  enrollments: ImportHistoryRow[]
  errors: ImportIssue[]
  warnings: ImportIssue[]
  detail_limit: number
  details_truncated: boolean
}

export interface ImportCreatedCredential {
  email: string
  password: string
}

export interface ImportResultRow {
  row: number
  student_id: string
  email: string
  full_name: string
  outcome: ImportOutcome
  passed_imported?: number
  enrollments_imported?: number
  warnings?: string[]
  errors?: ImportIssue[]
}

export interface ImportExecutionSummary {
  students_processed: number
  created: number
  updated: number
  skipped: number
  failed: number
  passed_imported: number
  enrollments_imported: number
  errors: number
  warnings: number
}

export interface ImportResult {
  file_hash: string
  mode: ImportMode
  summary: ImportExecutionSummary
  results: ImportResultRow[]
  errors: ImportIssue[]
  /** Only returned once, only for accounts created by this run. */
  created_credentials: ImportCreatedCredential[]
  audit_id: number
}

export interface ImportReportRow {
  id: number
  created_at: string
  actor: string | null
  file_hash: string
  mode: string
  summary: Record<string, number>
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function importForm(file: File, extra: Record<string, string>): FormData {
  const body = new FormData()
  body.append('file', file)
  for (const [key, value] of Object.entries(extra)) {
    body.append(key, value)
  }
  return body
}

export async function inspectStudentImport(file: File): Promise<ImportInspection> {
  return requestJson<ImportInspection>('/admin/students/import/inspect', {
    method: 'POST',
    body: importForm(file, {}),
    headers: authHeaders(),
  })
}

export async function validateStudentImport(
  file: File,
  mapping: ImportMapping,
  mode: ImportMode,
): Promise<ImportPreview> {
  const body = importForm(file, {
    mapping: JSON.stringify(mapping),
    mode,
  })
  return requestJson<ImportPreview>('/admin/students/import/validate', {
    method: 'POST',
    body,
    headers: authHeaders(),
  })
}

export async function confirmStudentImport(
  file: File,
  mapping: ImportMapping,
  mode: ImportMode,
  expectedHash: string,
): Promise<ImportResult> {
  const body = importForm(file, {
    mapping: JSON.stringify(mapping),
    mode,
    expected_hash: expectedHash,
    confirm: 'true',
  })
  return requestJson<ImportResult>('/admin/students/import/confirm', {
    method: 'POST',
    body,
    headers: authHeaders(),
  })
}

export async function listStudentImportReports(
  page = 1,
): Promise<Paginated<ImportReportRow>> {
  return requestJson<Paginated<ImportReportRow>>(
    '/admin/students/import/reports',
    { headers: authHeaders() },
    { page, page_size: 5 },
  )
}

/**
 * Download the official workbook. `requestJson` cannot be used (binary body),
 * so this mirrors its error handling with `toApiError` to keep the Persian
 * envelope message.
 */
export async function downloadStudentImportTemplate(): Promise<void> {
  const response = await fetch(
    buildApiUrl('/admin/students/import/template'),
    { credentials: 'include', headers: authHeaders() },
  )
  if (!response.ok) {
    throw await toApiError(response)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'student-import-template.xlsx'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

/** Client-side CSV of the validation/execution issues (UTF-8 BOM for Excel). */
export function downloadIssuesCsv(issues: ImportIssue[], fileName = 'import-errors.csv'): void {
  const escape = (value: string | number) => {
    const text = String(value ?? '')
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const header = ['sheet', 'row', 'field', 'code', 'message']
  const lines = [
    header.join(','),
    ...issues.map((issue) =>
      [issue.sheet, issue.row, issue.field, issue.code, issue.message].map(escape).join(','),
    ),
  ]
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
