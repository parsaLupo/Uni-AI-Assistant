import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { toApiError } from '../api/client'
import { appShell, errorMessages, isPersianText, persianErrorText } from '../i18n/fa'

/** Codes fixed by docs/12-error-handling-observability.md section 1. */
const DOCUMENTED_CODES = [
  'VALIDATION_ERROR',
  'AUTHENTICATION_REQUIRED',
  'PERMISSION_DENIED',
  'NOT_FOUND',
  'CONFLICT',
  'RATE_LIMITED',
  'AI_PROVIDER_ERROR',
  'RETRIEVAL_ERROR',
  'DOCUMENT_PROCESSING_ERROR',
  'INTERNAL_ERROR',
]

describe('document shell', () => {
  it('declares the app as Persian and RTL at the document level', () => {
    // AGENTS.md requires an RTL application "from the beginning", which is a
    // property of the document, not of a component.
    const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8')

    expect(html).toContain('lang="fa"')
    expect(html).toContain('dir="rtl"')
  })
})

describe('persian strings', () => {
  it('keeps every shell string in Persian script', () => {
    for (const value of Object.values(appShell)) {
      expect(isPersianText(value)).toBe(true)
    }
  })

  it('maps every documented error code to a Persian message', () => {
    for (const code of DOCUMENTED_CODES) {
      expect(errorMessages[code], code).toBeDefined()
      expect(isPersianText(errorMessages[code] as string), code).toBe(true)
    }
  })
})

describe('persianErrorText', () => {
  it('prefers the stable code mapping over the server sentence', () => {
    expect(persianErrorText('NOT_FOUND', 'منبع موردنظر یافت نشد.')).toBe(errorMessages.NOT_FOUND)
  })

  it('accepts a Persian server message when no code is mapped', () => {
    expect(persianErrorText('SOMETHING_NEW', 'پیام فارسی سرور')).toBe('پیام فارسی سرور')
  })

  it('never returns an English sentence to the user', () => {
    expect(isPersianText(persianErrorText('SOMETHING_NEW', 'Gateway Timeout'))).toBe(true)
    expect(isPersianText(persianErrorText('SOMETHING_NEW'))).toBe(true)
  })
})

describe('toApiError', () => {
  it('produces a Persian message when the body is not the contract shape', async () => {
    const response = new Response('<html><body>504 Gateway Timeout</body></html>', { status: 504 })

    const error = await toApiError(response)

    expect(error.code).toBe('INTERNAL_ERROR')
    expect(isPersianText(error.message)).toBe(true)
  })
})