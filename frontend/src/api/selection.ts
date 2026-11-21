/**
 * Phase 11 — course-selection eligibility checks (docs/api/course-selection.md).
 *
 * `POST /students/me/course-selection/` is the deterministic rules engine's
 * surface: the verdict, every machine-readable rejection reason and the what-if
 * credit totals come from the backend engine, and the response already carries
 * a written Persian explanation (`explanation`). The UI only renders what the
 * engine produced — it never re-derives eligibility itself (AGENTS.md §8).
 *
 * The request field is `course_query`: the student may type a course code or a
 * Persian course name, and the backend resolves it against the real catalog
 * before running the engine. A query that matches more than one course never
 * produces a verdict; the response is an `ambiguous` candidate list the student
 * must choose from (the UI then re-submits the chosen course code).
 */

import { authedJson } from '../features/auth/api'

export interface SelectionReason {
  code: string
  message: string
  params: Record<string, unknown>
}

export interface CreditTotals {
  limit: number
  planned: number
  candidate: number
  extra: number
  total_with_candidate: number
  over_limit: boolean
}

export interface SelectionExplanation {
  text: string
  /** `composed` = deterministic engine text, `llm` = verdict-verified paraphrase. */
  source: 'composed' | 'llm'
  engine_eligible: boolean
}

export interface SelectionDecision {
  course: { code: string; title: string; credits: number }
  eligible: boolean
  reasons: SelectionReason[]
  term_name: string
  passed_course_codes: string[]
  missing_prerequisite_codes: string[]
  planned_course_codes: string[]
  extra_course_codes: string[]
  credit_totals: CreditTotals
  engine_version: string
  explanation: SelectionExplanation
}

/** One catalog row shown when a typed name matches several courses. */
export interface CourseCandidate {
  code: string
  title: string
  credits: number
  department: string
  course_type: string
}

export interface ResolvedSelection extends SelectionDecision {
  status: 'resolved'
}

/**
 * Several catalog rows are plausible. There is deliberately no `eligible` /
 * `reasons` here: the engine never ran, so the student must pick a course.
 */
export interface AmbiguousSelection {
  status: 'ambiguous'
  query: string
  candidates: CourseCandidate[]
  /** Total matches, which may exceed the capped candidate list. */
  total: number
}

export type SelectionResult = ResolvedSelection | AmbiguousSelection

export function checkCourseSelection(
  courseQuery: string,
  extraCourseCodes: string[] = [],
): Promise<SelectionResult> {
  return authedJson<SelectionResult>('/students/me/course-selection/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      course_query: courseQuery,
      extra_course_codes: extraCourseCodes,
    }),
  })
}
