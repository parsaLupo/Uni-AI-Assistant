/**
 * /login — Phase 03 authentication screen (docs/20-ui-navigation.md section 2).
 *
 * All strings come from i18n/fa.ts; failures are rendered from the stable
 * `error.code` via persianErrorText, never from raw English server text
 * (docs/12 section 2). The access token is stored in memory only by the API
 * layer — nothing is written to web storage here or anywhere in the SPA.
 */

import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/client'
import { auth, persianErrorText } from '../../i18n/fa'
import { useAuth } from './AuthProvider'
import { AuthLayout } from './AuthLayout'
import { landingFor, RedirectIfAuthenticated } from './ProtectedRoute'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [reveal, setReveal] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const user = await login(email, password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(landingFor(user, from), { replace: true })
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? persianErrorText(caught.code, caught.message)
          : persianErrorText('INTERNAL_ERROR'),
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <RedirectIfAuthenticated>
      <AuthLayout title={auth.loginTitle} subtitle={auth.loginSubtitle}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-space-md">
          <div className="flex flex-col gap-space-xs">
            <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="login-email">
              {auth.email}
            </label>
            <div className="relative flex items-center">
              <span
                className="material-symbols-outlined absolute inset-y-0 right-space-md flex items-center text-outline text-[20px] pointer-events-none"
                aria-hidden="true"
              >
                alternate_email
              </span>
              <input
                id="login-email"
                type="email"
                name="email"
                autoComplete="email"
                dir="ltr"
                placeholder={auth.emailPlaceholder}
                className="w-full h-12 pe-11 ps-space-md bg-surface-container-low rounded-xl font-body-sm text-body-sm text-on-surface placeholder:text-outline focus:bg-surface-container-lowest transition-all text-right shadow-inner"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="flex flex-col gap-space-xs">
            <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="login-password">
              {auth.password}
            </label>
            <div className="relative flex items-center">
              {/* One icon at a time in the same slot: the key while the field
                  is empty, the show/hide toggle once the user starts typing. */}
              {password ? (
                <button
                  type="button"
                  aria-label={auth.togglePassword}
                  aria-pressed={reveal}
                  onClick={() => setReveal((value) => !value)}
                  className="absolute right-space-md top-1/2 -translate-y-1/2 text-outline hover:text-on-surface flex items-center justify-center p-1"
                >
                  <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                    {reveal ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              ) : (
                <span
                  className="material-symbols-outlined absolute inset-y-0 right-space-md flex items-center text-outline text-[20px] pointer-events-none"
                  aria-hidden="true"
                >
                  key
                </span>
              )}
              <input
                id="login-password"
                type={reveal ? 'text' : 'password'}
                name="password"
                autoComplete="current-password"
                dir="ltr"
                className="w-full h-12 ps-11 pe-12 bg-surface-container-low rounded-xl font-body-sm text-body-sm text-on-surface focus:bg-surface-container-lowest transition-all text-right shadow-inner"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="m-0 rounded-xl bg-error-container px-space-md py-space-sm font-label-lg text-label-lg text-on-error-container">
              {error}
            </p>
          )}

          <div className="flex flex-col gap-space-xs pt-space-xs">
            <button
              type="submit"
              disabled={submitting}
              className="w-full h-12 rounded-xl bg-primary-container hover:bg-primary text-on-primary font-headline-sm text-headline-sm flex items-center justify-center gap-space-sm shadow-md transition-all active:scale-[0.99] disabled:opacity-75 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[22px]" aria-hidden="true">
                login
              </span>
              <span>{auth.submitLogin}</span>
            </button>
          </div>
        </form>

        <div className="relative flex items-center justify-center">
          <div className="w-full h-px bg-surface-variant" aria-hidden="true" />
        </div>

        <p className="m-0 text-center font-body-sm text-body-sm text-on-surface-variant">
          <Link to="/register" className="text-primary font-semibold hover:underline">
            {auth.toRegister}
          </Link>
        </p>
      </AuthLayout>
    </RedirectIfAuthenticated>
  )
}
