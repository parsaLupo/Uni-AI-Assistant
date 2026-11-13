import { describe, expect, it } from 'vitest'
import { examRowsFromPlanner, todaySessions } from '../features/dashboard/schedule'
import type { ClassSchedule, Exam, PlannerItem } from '../types/academic'

/**
 * Pure dashboard shaping helpers over `/students/planner/` rows:
 * today's classes (weekday filter + start-time order) and final exams
 * (announced first chronologically, unannounced last).
 */

let nextScheduleId = 1
let nextItemId = 1

function schedule(weekday: number, start: string, end: string): ClassSchedule {
  return {
    id: nextScheduleId++,
    weekday,
    weekday_display: '',
    start_time: start,
    end_time: end,
    classroom: 'کلاس ۱',
  }
}

function exam(startsAt: string, endsAt: string): Exam {
  return {
    id: nextItemId,
    starts_at: startsAt,
    ends_at: endsAt,
    classroom: '',
    status: 'SCHEDULED',
    last_updated_at: '',
    created_at: '',
    course_offering: {
      id: nextItemId,
      course_code: '1916219',
      course_title: '',
      section_code: '01',
      term: {
        id: 1,
        name: 'نیمسال اول 1405-1406',
        academic_year: '1405-1406',
        semester_type: 'FIRST',
        is_current: true,
        starts_at: '2026-09-01T00:00:00Z',
        ends_at: '2027-02-01T00:00:00Z',
      },
    },
  }
}

function plannerItem(
  schedules: ClassSchedule[],
  examRow?: Exam,
): PlannerItem {
  const id = nextItemId++
  return {
    id,
    status: 'ENROLLED',
    total_credits: 3,
    course_offering: {
      id: 1000 + id,
      section_code: '01',
      course: { code: '1916219', title: `درس ${id}`, credits: 3 },
      term: examRow
        ? examRow.course_offering.term
        : {
            id: 1,
            name: 'نیمسال اول 1405-1406',
            academic_year: '1405-1406',
            semester_type: 'FIRST',
            is_current: true,
            starts_at: '2026-09-01T00:00:00Z',
            ends_at: '2027-02-01T00:00:00Z',
          },
      professor: null,
      schedules,
      ...(examRow ? { exam: examRow } : {}),
    },
  } as unknown as PlannerItem
}

// 2026-11-08 is a Sunday (getDay() === 0) — the session rows below use the
// API's Date#getDay() numbering (0 = یکشنبه … 5 = شنبه, 6 = جمعه).
const SUNDAY = new Date(2026, 10, 8)

describe('todaySessions', () => {
  it('shows only sessions matching today’s weekday, sorted by start time', () => {
    const items = [
      plannerItem([schedule(5, '10:00', '12:00')]), // شنبه — not today
      plannerItem([schedule(0, '10:00', '12:00')]), // یکشنبه
      plannerItem([schedule(0, '08:00', '09:00')]), // یکشنبه, earlier
      plannerItem([schedule(2, '13:00', '14:00')]), // سه‌شنبه — not today
    ]
    const rows = todaySessions(items, SUNDAY)
    expect(rows).toHaveLength(2)
    expect(rows.map((r) => r.schedule.start_time)).toEqual(['08:00', '10:00'])
  })

  it('keeps every weekly session of one course (two meetings on one day)', () => {
    const item = plannerItem([
      schedule(0, '15:00', '17:00'),
      schedule(0, '08:00', '09:00'),
    ])
    const rows = todaySessions([item], SUNDAY)
    expect(rows).toHaveLength(2)
    expect(rows.map((r) => r.schedule.start_time)).toEqual(['08:00', '15:00'])
  })

  it('returns an empty list for an empty planner or a free day', () => {
    expect(todaySessions([], SUNDAY)).toEqual([])
    expect(todaySessions([plannerItem([schedule(5, '10:00', '12:00')])], SUNDAY)).toEqual([])
  })
})

describe('examRowsFromPlanner', () => {
  it('lists announced exams chronologically, then unannounced offerings', () => {
    const items = [
      plannerItem([], exam('2027-01-20T12:30:00Z', '2027-01-20T14:30:00Z')), // دیرتر
      plannerItem([], exam('2027-01-09T06:30:00Z', '2027-01-09T08:30:00Z')), // زودتر
      plannerItem([]), // بدون امتحان اعلام‌شده
    ]
    const rows = examRowsFromPlanner(items)
    expect(rows.map((r) => r.exam?.starts_at ?? null)).toEqual([
      '2027-01-09T06:30:00Z',
      '2027-01-20T12:30:00Z',
      null,
    ])
  })

  it('marks offerings without an imported exam as unannounced (no invented dates)', () => {
    const rows = examRowsFromPlanner([plannerItem([])])
    expect(rows).toHaveLength(1)
    expect(rows[0].exam).toBeNull()
  })

  it('returns an empty list for an empty planner', () => {
    expect(examRowsFromPlanner([])).toEqual([])
  })
})
