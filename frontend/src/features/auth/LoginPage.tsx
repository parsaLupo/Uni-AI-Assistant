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
import { RedirectIfAuthenticated } from './ProtectedRoute'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login(email, password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' ? from : '/dashboard', { replace: true })
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
      <main className="app-shell auth-form">
        <h1 className="app-shell__title">{auth.loginTitle}</h1>
        <form onSubmit={onSubmit} noValidate>
          <label className="auth-form__field">
            <span>{auth.email}</span>
            <input
              type="email"
              name="email"
              autoComplete="email"
              dir="ltr"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="auth-form__field">
            <span>{auth.password}</span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              dir="ltr"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && (
            <p className="auth-form__error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="auth-form__submit" disabled={submitting}>
            {auth.submitLogin}
          </button>
        </form>
        <p className="auth-form__switch">
          <Link to="/register">{auth.toRegister}</Link>
        </p>
      </main>
    </RedirectIfAuthenticated>
  )
}
