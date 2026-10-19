import { describe, expect, it } from 'vitest'
import { formatTimeFa, toAsciiDigits, toPersianDigits } from '../i18n/digits'
import {
  daysUntil,
  formatJalaliDate,
  formatJalaliShort,
  isoToJalaali,
  toJalaali,
} from '../i18n/jalali'

describe('toPersianDigits / toAsciiDigits', () => {
  it('maps ASCII digits to Persian and back', () => {
    expect(toPersianDigits('40123456')).toBe('۴۰۱۲۳۴۵۶')
    expect(toAsciiDigits('۴۰۱۲۳۴۵۶')).toBe('40123456')
    expect(toAsciiDigits('٤٠١')).toBe('401')
  })

  it('leaves non-digit text untouched and accepts numbers', () => {
    expect(toPersianDigits('کد 12 - 34')).toBe('کد ۱۲ - ۳۴')
    expect(toPersianDigits(17.84)).toBe('۱۷٫۸۴'.replace('٫', '.')) // dots stay ASCII
    expect(toPersianDigits(72)).toBe('۷۲')
  })

  it('zero-pads a clock time', () => {
    expect(formatTimeFa(new Date(2024, 0, 1, 9, 5))).toBe('۰۹:۰۵')
    expect(formatTimeFa(new Date(2024, 0, 1, 23, 0))).toBe('۲۳:۰۰')
  })
})

describe('toJalaali (known anchors)', () => {
  it('converts Nowruz 1403 (20 March 2024)', () => {
    expect(toJalaali(2024, 3, 20)).toEqual({ year: 1403, month: 1, day: 1 })
  })

  it('converts 5 October 2024 to 14 Mehr 1403', () => {
    expect(toJalaali(2024, 10, 5)).toEqual({ year: 1403, month: 7, day: 14 })
  })

  it('converts Nowruz 1404 (21 March 2025)', () => {
    expect(toJalaali(2025, 3, 21)).toEqual({ year: 1404, month: 1, day: 1 })
  })

  it('handles the leap of Esfand (29 vs 30) via a late-February date', () => {
    // 19 March 2025 is 29 Esfand 1403 (1403 is a leap year → Esfand has 30 days).
    expect(toJalaali(2025, 3, 19)).toEqual({ year: 1403, month: 12, day: 29 })
    expect(toJalaali(2025, 3, 20)).toEqual({ year: 1403, month: 12, day: 30 })
  })
})

describe('formatting', () => {
  it('renders the formal Persian structure «۱۴ مهر ۱۴۰۳»', () => {
    expect(formatJalaliDate({ year: 1403, month: 7, day: 14 })).toBe('۱۴ مهر ۱۴۰۳')
    expect(formatJalaliShort({ year: 1403, month: 12, day: 20 })).toBe('۲۰ اسفند')
  })

  it('parses an ISO timestamp to the Jalali day', () => {
    const j = isoToJalaali('2024-10-05T12:00:00Z')
    expect(j).toEqual({ year: 1403, month: 7, day: 14 })
  })

  it('rejects garbage input', () => {
    expect(() => isoToJalaali('not-a-date')).toThrow(RangeError)
    // Out of the calendar's supported range (Jalali years -61…3177, i.e.
    // Gregorian 560…3798); year 1000 CE is valid (→ 379 SH), so it must not throw.
    expect(() => toJalaali(500, 1, 1)).toThrow(RangeError)
    expect(() => toJalaali(4000, 1, 1)).toThrow(RangeError)
  })

  it('counts whole local days until a target', () => {
    const in3 = new Date(Date.now() + 3 * 86_400_000)
    expect(daysUntil(in3.toISOString())).toBe(3)
    const past = new Date(Date.now() - 2 * 86_400_000)
    expect(daysUntil(past.toISOString())).toBe(-2)
  })
})
