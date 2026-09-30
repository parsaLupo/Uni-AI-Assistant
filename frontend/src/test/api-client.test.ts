import { describe, expect, it } from 'vitest'
import { ApiError, apiBaseUrl, buildApiUrl, toApiError } from '../api/client'

describe('buildApiUrl', () => {
  it('mounts paths under the versioned API base with a trailing slash', () => {
    expect(buildApiUrl('/health')).toBe(`${apiBaseUrl()}/health/`)
  })

  it('accepts paths with or without a leading slash', () => {
    expect(buildApiUrl('courses')).toBe(buildApiUrl('/courses'))
  })

  it('adds pagination parameters documented in docs/04 section 4', () => {
    expect(buildApiUrl('/courses', { page: 2, page_size: 20, search: undefined })).toBe(
      `${apiBaseUrl()}/courses/?page=2&page_size=20`,
    )
  })
})

describe('toApiError', () => {
  it('reads the documented error envelope', async () => {
    const response = new Response(
      JSON.stringify({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'One or more fields are invalid.',
          details: { title: ['This field is required.'] },
        },
      }),
      {
        status: 400,
        headers: { 'content-type': 'application/json', 'X-Request-ID': 'trace-42' },
      },
    )

    const error = await toApiError(response)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('VALIDATION_ERROR')
    expect(error.status).toBe(400)
    expect(error.details).toEqual({ title: ['This field is required.'] })
    // Correlation id is kept so support can trace the failure (docs/12 section 4).
    expect(error.requestId).toBe('trace-42')
  })

  it('falls back to INTERNAL_ERROR when the body is not the contract shape', async () => {
    const response = new Response('<html><body>500 Bad Gateway</body></html>', { status: 502 })

    const error = await toApiError(response)

    expect(error.code).toBe('INTERNAL_ERROR')
    expect(error.status).toBe(502)
  })
})
