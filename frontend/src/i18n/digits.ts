/**
 * Persian digit rendering (docs/11 localization: Persian numerals in the UI;
 * DESIGN.md: "Persian-digit tabular figures" in tables and stat cards).
 *
 * Display only — API contracts and query parameters keep ASCII digits
 * (AGENTS.md: English/Persian rules apply to identifiers and user-facing text).
 */

const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'] as const
const EN_DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] as const

/** Convert every ASCII digit in `value` to its Persian counterpart. */
export function toPersianDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (d) => FA_DIGITS[Number(d)])
}

/** Convert Persian/Arabic-Indic digits back to ASCII (for form inputs). */
export function toAsciiDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (d) => String(EN_DIGITS['۰۱۲۳۴۵۶۷۸۹'.indexOf(d)]))
    .replace(/[٠-٩]/g, (d) => String(EN_DIGITS['٠١٢٣٤٥٦٧٨٩'.indexOf(d)]))
}

/** Localised, zero-padded 24h clock: `9:05` → `۰۹:۰۵`. */
export function formatTimeFa(date: Date): string {
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return toPersianDigits(`${hh}:${mm}`)
}
