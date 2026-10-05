/**
 * In-memory access token store (docs/05 section 3).
 *
 * The access token is deliberately kept in a module variable rather than
 * localStorage/sessionStorage: JS-readable storage would let any XSS payload
 * exfiltrate it, while a module variable dies with the tab. The refresh token
 * never enters JS at all — it is an HttpOnly cookie the server manages.
 */

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}
