/**
 * Phase 11 — course-selection eligibility checks (docs/api/course-selection.md).
 *
 * `POST /students/me/course-selection/` is the deterministic rules engine's
 * surface: the verdict, every machine-readable rejection reason and the what-if
 * credit totals come from the backend engine, and the response already carries
 * a written Persian explanation (`explanation`). The UI only renders what the
 * engine produced — it never re-derives eligibility itself (AGENTS.md §8).
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

export async function checkCourseSelection(
  courseCode: string,
  extraCourseCodes: string[] = [],
): Promise<SelectionDecision> {
  return authedJson<SelectionDecision>('/students/me/course-selection/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      course_code: courseCode,
      extra_course_codes: extraCourseCodes,
    }),
  })
}
