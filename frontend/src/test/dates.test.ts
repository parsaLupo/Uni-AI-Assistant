/**
 * api/dates.ts — instant-preserving datetime-local conversions.
 *
 * Contract (docs I-11): the API emits UTC ISO-8601; the UI edits in the
 * viewer's local wall time. A `datetime-local` value sliced from a UTC
 * string (the old `iso.slice(0, 16)`) shows UTC as if local and shifts the
 * stored instant by the viewer's UTC offset on every edit round-trip.
 */

import { describe, expect, it } from 'vitest'
import { localInputToUtcIso, utcIsoToLocalInput } from '../api/dates'

/** Local `YYYY-MM-DDTHH:mm` rendering of an instant, computed independently. */
function expectedLocalInput(iso: string): string {
  const date = new Date(iso)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

describe('utcIsoToLocalInput', () => {
  it('renders the instant as the viewer-local wall time, not the UTC wall time', () => {
    // Backend example from the live API.
    const iso = '2026-11-15T09:33:00Z'
    expect(utcIsoToLocalInput(iso)).toBe(expectedLocalInput(iso))
  })

  it('handles offsets and fractional seconds in the source string', () => {
    const iso = '2026-10-01T08:00:00.123456+03:30'
    expect(utcIsoToLocalInput(iso)).toBe(expectedLocalInput(iso))
  })

  it('returns an empty string for empty and unparseable input — never a fallback date', () => {
    expect(utcIsoToLocalInput(null)).toBe('')
    expect(utcIsoToLocalInput(undefined)).toBe('')
    expect(utcIsoToLocalInput('')).toBe('')
    expect(utcIsoToLocalInput('not-a-date')).toBe('')
  })
})

describe('localInputToUtcIso', () => {
  it('round-trips: convert out, convert back, same instant', () => {
    for (const iso of [
      '2026-11-15T09:33:00Z',
      '2026-03-21T00:00:00Z',
      '2026-11-16T20:30:00Z', // midnight-crossing for positive offsets
      '2026-06-21T23:59:00Z',
    ]) {
      const input = utcIsoToLocalInput(iso)
      const back = localInputToUtcIso(input)
      // toISOString always emits milliseconds; compare the instants.
      expect(back === null ? Number.NaN : new Date(back).getTime()).toBe(new Date(iso).getTime())
    }
  })

  it('keeps date-only values untouched — they must never be timezone-converted', () => {
    // Terms/documents dates are plain YYYY-MM-DD in and out (no helper use).
    expect(utcIsoToLocalInput('2026-06-01')).toBe(expectedLocalInput('2026-06-01'))
  })

  it('returns null for empty and unparseable input', () => {
    expect(localInputToUtcIso('')).toBeNull()
    expect(localInputToUtcIso(null)).toBeNull()
    expect(localInputToUtcIso(undefined)).toBeNull()
    expect(localInputToUtcIso('not-a-date')).toBeNull()
  })
})
