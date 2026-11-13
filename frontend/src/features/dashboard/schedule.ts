/**
 * Dashboard data shaping (UI refinement): pure helpers over the student's own
 * `/students/planner/` rows so both dashboard sections read from the same
 * real source — the current-term enrollments (`PLANNED`/`ENROLLED`) with
 * their imported `ClassSchedule` rows and optional `Exam`.
 *
 * No mock data (docs/06 §8): an offering without an imported exam stays
 * visible as "not announced" instead of being dropped or given a date.
 */

import type { ClassSchedule, Exam, PlannerItem } from '../../types/academic'

export interface TodaySession {
  item: PlannerItem
  schedule: ClassSchedule
}

/**
 * Classes meeting on the given day, sorted by start time.
 *
 * `weekday` uses the API's numbering — identical to JS `Date#getDay()`
 * (0 = یکشنبه … 5 = شنبه, 6 = جمعه; docs/03 section 3). Every weekly session
 * of an enrolled offering is kept (a course can meet twice on one day), and
 * courses that do not meet today are never shown.
 */
export function todaySessions(items: PlannerItem[], now: Date): TodaySession[] {
  const weekday = now.getDay()
  const rows: TodaySession[] = []
  for (const item of items) {
    for (const schedule of item.course_offering.schedules ?? []) {
      if (schedule.weekday === weekday) {
        rows.push({ item, schedule })
      }
    }
  }
  return rows.sort((a, b) => a.schedule.start_time.localeCompare(b.schedule.start_time))
}

export interface ExamRowData {
  item: PlannerItem
  /** null = the offering has no imported exam → «تاریخ امتحان اعلام نشده». */
  exam: Exam | null
}

/**
 * Final-exam rows for the student's current-term enrollments.
 *
 * Announced exams come first in chronological order; offerings without an
 * announced date follow (so the "not announced" note stays visible).
 * Planner rows are unique per offering and one exam per offering is enforced
 * by the schema, so no duplicate entries can appear; passed courses live in
 * historical terms and never reach the current-term planner.
 */
export function examRowsFromPlanner(items: PlannerItem[]): ExamRowData[] {
  const announced: ExamRowData[] = []
  const unannounced: ExamRowData[] = []
  for (const item of items) {
    const exam = item.course_offering.exam ?? null
    if (exam) {
      announced.push({ item, exam })
    } else {
      unannounced.push({ item, exam: null })
    }
  }
  announced.sort((a, b) => a.exam!.starts_at.localeCompare(b.exam!.starts_at))
  return [...announced, ...unannounced]
}
