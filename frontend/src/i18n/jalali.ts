/**
 * Gregorian → Jalali conversion and Persian date formatting.
 *
 * docs/20 + Phase 05 require Jalali presentation where dates are shown
 * («۱۴ مهر ۱۴۰۳» per DESIGN.md). The API always returns UTC ISO-8601; conversion
 * happens here, in local time, so a term/exam date never shifts a day because
 * of the browser timezone.
 *
 * Algorithm: the standard Persian (jalaali) arithmetic calendar — the same
 * arithmetic used by the well-known jalaali-js table. Implemented locally
 * because AGENTS.md rule 10 blocks a dependency for ~90 lines of arithmetic.
 */

import { toPersianDigits } from './digits'

const BREAKS = [
  -61, 9, 38, 199, 426, 685, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192,
  2262, 2324, 2394, 2456, 3178,
] as const

export const JALALI_MONTHS = [
  'فروردین',
  'اردیبهشت',
  'خرداد',
  'تیر',
  'مرداد',
  'شهریور',
  'مهر',
  'آبان',
  'آذر',
  'دی',
  'بهمن',
  'اسفند',
] as const

/** JS `Date#getDay()` order (0 = Sunday) mapped to the Persian week (0 = شنبه). */
export const WEEKDAYS_FA = [
  'یکشنبه',
  'دوشنبه',
  'سه‌شنبه',
  'چهارشنبه',
  'پنج‌شنبه',
  'جمعه',
  'شنبه',
] as const

function div(a: number, b: number): number {
  return Math.trunc(a / b)
}

function mod(a: number, b: number): number {
  return a - Math.trunc(a / b) * b
}

interface JalCal {
  leap: number
  gy: number
  march: number
}

function jalCal(jy: number): JalCal {
  const bl = BREAKS.length
  const gy = jy + 621
  let leapJ = -14
  let jp: number = BREAKS[0]
  let jump = 0
  let jm: number
  let n: number

  if (jy < jp || jy >= BREAKS[bl - 1]) {
    throw new RangeError(`سال جلالی نامعتبر است: ${jy}`)
  }
  for (let i = 1; i < bl; i += 1) {
    jm = BREAKS[i]
    jump = jm - jp
    if (jy < jm) break
    leapJ = leapJ + div(jump, 33) * 8 + div(mod(jump, 33), 4)
    jp = jm
  }
  n = jy - jp
  leapJ = leapJ + div(n, 33) * 8 + div(mod(n, 33) + 3, 4)
  if (mod(jump, 33) === 4 && jump - n === 4) leapJ += 1

  const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150
  const march = 20 + leapJ - leapG

  let leap = mod(mod(n + 1, 33) - 1, 4)
  if (leap === -1) leap = 4

  return { leap, gy, march }
}

function g2d(gy: number, gm: number, gd: number): number {
  let d =
    div((gy + div(gm - 8, 6) + 100100) * 1461, 4) +
    div(153 * mod(gm + 9, 12) + 2, 5) +
    gd -
    34840408
  d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752
  return d
}

function d2g(jdn: number): { gy: number; gm: number; gd: number } {
  let j = 4 * jdn + 139361631
  j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
  const i = div(mod(j, 1461), 4) * 5 + 308
  const gd = div(mod(i, 153), 5) + 1
  const gm = mod(div(i, 153), 12) + 1
  const gy = div(j, 1461) - 100100 + div(8 - gm, 6)
  return { gy, gm, gd }
}

export interface JalaliDate {
  year: number
  month: number // 1..12
  day: number
}

/** Convert a Gregorian calendar date (local parts) to its Jalali equivalent. */
export function toJalaali(gy: number, gm: number, gd: number): JalaliDate {
  const jdn = g2d(gy, gm, gd)
  const r = jalCalOfResult(jdn)
  return r
}

function jalCalOfResult(jdn: number): JalaliDate {
  const { gy } = d2g(jdn)
  let jy = gy - 621
  const r = jalCal(jy)
  const jdn1f = g2d(r.gy, 3, r.march)
  let k = jdn - jdn1f

  if (k >= 0) {
    if (k <= 185) {
      return { year: jy, month: 1 + div(k, 31), day: mod(k, 31) + 1 }
    }
    k -= 186
  } else {
    jy -= 1
    k += 179
    if (r.leap === 1) k += 1
  }
  return { year: jy, month: 7 + div(k, 30), day: mod(k, 30) + 1 }
}

/** Parse a UTC ISO-8601 API timestamp into the Jalali date of the *local* day. */
export function isoToJalaali(iso: string): JalaliDate {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    throw new RangeError(`تاریخ نامعتبر: ${iso}`)
  }
  return toJalaali(date.getFullYear(), date.getMonth() + 1, date.getDate())
}

export function weekdayFa(date: Date): string {
  return WEEKDAYS_FA[date.getDay()]
}

/** Persian digits, formal structure: «۱۴ مهر ۱۴۰۳». */
export function formatJalaliDate(value: string | JalaliDate): string {
  const j = typeof value === 'string' ? isoToJalaali(value) : value
  return toPersianDigits(`${j.day} ${JALALI_MONTHS[j.month - 1]} ${j.year}`)
}

/** Short month label for countdown chips: «۲۰ دی». */
export function formatJalaliShort(value: string | JalaliDate): string {
  const j = typeof value === 'string' ? isoToJalaali(value) : value
  return toPersianDigits(`${j.day} ${JALALI_MONTHS[j.month - 1]}`)
}

/** Whole days from today (local) until the given ISO instant; negative = past. */
export function daysUntil(iso: string): number {
  const target = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const that = new Date(target.getFullYear(), target.getMonth(), target.getDate())
  return Math.round((that.getTime() - today.getTime()) / 86_400_000)
}

/**
 * «۱۴:۳۰» — Persian-digits clock time. Accepts a `Date` (shown in the viewer's
 * local time, matching `formatJalaliDate`'s local-day rule) or a raw API string:
 * plain times (schedule `start_time` = "14:00:00") and full ISO timestamps
 * alike, taking the first HH:MM pair in the string.
 */
export function formatTimeFa(value: string | Date): string {
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return '—'
    const hh = String(value.getHours()).padStart(2, '0')
    const mm = String(value.getMinutes()).padStart(2, '0')
    return toPersianDigits(`${hh}:${mm}`)
  }
  const match = value.match(/(\d{1,2}):(\d{2})/)
  if (!match) return toPersianDigits(value)
  return toPersianDigits(`${match[1]}:${match[2]}`)
}
