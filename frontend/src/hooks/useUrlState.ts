/** URL-driven list state (ADR-013 / Phase 06).

The URL is the source of truth for list-page filters, debounce and
pagination: values survive a refresh, a shared link and back/forward
navigation. Each list page binds its controls to this hook instead of to local
useState. The `key` matches the documented endpoint query parameter so the
contract is visible in the browser bar.

Two details matter for correctness:

* A URL param is a string, so a numeric initial value is coerced back to a
  number — otherwise `page - 1` would rely on string coercion.
* The hook stays in sync when the URL changes *outside* the setter (browser
  back/forward or a link carrying `?search=…`); a plain `useState` initial
  value would freeze the first URL the page ever saw.

Commits use `replace` so typing a search term does not fill the history with
one entry per keystroke.
*/
import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"

export interface UrlStateOptions {
  /** Debounce (ms) before the value is committed to the URL. */
  debounce?: number
}

export function useUrlState<T extends string | number | undefined>(
  key: string,
  initial: T,
  options: UrlStateOptions = {},
): [T, (next: T) => void] {
  const { debounce = 150 } = options
  const [searchParams, setSearchParams] = useSearchParams()

  const rawFromUrl = searchParams.get(key)

  const coerce = (raw: string | null): T => {
    if (raw === null) {
      return initial
    }
    if (typeof initial === "number") {
      const parsed = Number(raw)
      return (Number.isFinite(parsed) ? parsed : initial) as T
    }
    return raw as T
  }

  const fromUrl = coerce(rawFromUrl)
  const [value, setValue] = useState<T>(fromUrl)

  // External URL change (back/forward, shared link) → adopt the URL value.
  useEffect(() => {
    setValue(coerce(rawFromUrl))
    // `coerce` is derived from `initial`, which is a primitive in every call.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawFromUrl, key, initial])

  // Local change → commit to the URL after the debounce, unless the URL
  // already holds this value (which is what the effect above just wrote).
  useEffect(() => {
    if (value === fromUrl) {
      return
    }
    const timer = window.setTimeout(() => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (value === initial || value === undefined || value === "") {
            next.delete(key)
          } else {
            next.set(key, String(value))
          }
          return next
        },
        { replace: true },
      )
    }, debounce)
    return () => window.clearTimeout(timer)
  }, [value, fromUrl, initial, key, debounce, setSearchParams])

  return [value, setValue] as const
}
