/**
 * /register — public self-registration (FR-AUTH-001, ADR-014 decision 2).
 *
 * The payload never carries a role: the server forces STUDENT, so a forged
 * field cannot escalate privileges. Duplicate email surfaces as 409 CONFLICT
 * and weak passwords as 400 VALIDATION_ERROR — both rendered in Persian from
 * the stable code (docs/12 section 2).
 */

import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../../api/client'
import { auth, persianErrorText } from '../../i18n/fa'
import { useAuth } from './AuthProvider'
import { RedirectIfAuthenticated } from './ProtectedRoute'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await register({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
      })
      navigate('/dashboard', { replace: true })
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
        <h1 className="app-shell__title">{auth.registerTitle}</h1>
        <form onSubmit={onSubmit} noValidate>
          <label className="auth-form__field">
            <span>{auth.firstName}</span>
            <input
              type="text"
              name="first_name"
              autoComplete="given-name"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
            />
          </label>
          <label className="auth-form__field">
            <span>{auth.lastName}</span>
            <input
              type="text"
              name="last_name"
              autoComplete="family-name"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
            />
          </label>
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
              autoComplete="new-password"
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
            {auth.submitRegister}
          </button>
        </form>
        <p className="auth-form__switch">
          <Link to="/login">{auth.toLogin}</Link>
        </p>
      </main>
    </RedirectIfAuthenticated>
  )
}
