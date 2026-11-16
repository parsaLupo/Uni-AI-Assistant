/**
 * Instant-preserving conversions between the API's UTC ISO-8601 timestamps
 * and the values HTML `datetime-local` inputs expect (local wall time).
 *
 * The backend (USE_TZ=True, TIME_ZONE=UTC) emits e.g. `2026-11-15T09:33:00Z`.
 * Slicing that string for a `datetime-local` input shows the UTC wall time as
 * if it were local — every edit round-trip then shifts the instant by the
 * viewer's UTC offset (−03:30 in Tehran), which walks the stored time (and,
 * near midnight, the calendar date) with each save. These helpers convert
 * through the actual `Date` value so the instant survives the round trip:
 *
 *   pick 12:00 local  →  toISOString → 08:30Z stored
 *   edit shows 12:00 local (converted back)  →  re-save → 08:30Z (unchanged)
 *
 * Date-only fields (terms, documents) are plain `YYYY-MM-DD` end to end and
 * must never pass through these — no timezone conversion for calendar dates.
 */

/** UTC ISO-8601 instant → `YYYY-MM-DDTHH:mm` in the viewer's local time. */
export function utcIsoToLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** `datetime-local` value (local wall time) → UTC ISO instant, or null when empty. */
export function localInputToUtcIso(value: string | null | undefined): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}
