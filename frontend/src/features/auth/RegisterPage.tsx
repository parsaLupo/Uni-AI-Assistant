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
import { AuthLayout } from './AuthLayout'
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
  const [reveal, setReveal] = useState(false)

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
      <AuthLayout title={auth.registerTitle} subtitle={auth.registerSubtitle}>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-space-md">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <div className="flex flex-col gap-space-xs">
              <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="register-first-name">
                {auth.firstName}
              </label>
              <input
                id="register-first-name"
                type="text"
                name="first_name"
                autoComplete="given-name"
                className="w-full h-12 px-space-md bg-surface-container-low rounded-xl font-body-sm text-body-sm text-on-surface focus:bg-surface-container-lowest transition-all shadow-inner"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-space-xs">
              <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="register-last-name">
                {auth.lastName}
              </label>
              <input
                id="register-last-name"
                type="text"
                name="last_name"
                autoComplete="family-name"
                className="w-full h-12 px-space-md bg-surface-container-low rounded-xl font-body-sm text-body-sm text-on-surface focus:bg-surface-container-lowest transition-all shadow-inner"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="flex flex-col gap-space-xs">
            <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="register-email">
              {auth.email}
            </label>
            <div className="relative flex items-center">
              <span
                className="material-symbols-outlined absolute start-space-md text-outline text-[20px] pointer-events-none"
                aria-hidden="true"
              >
                alternate_email
              </span>
              <input
                id="register-email"
                type="email"
                name="email"
                autoComplete="email"
                dir="ltr"
                placeholder={auth.emailPlaceholder}
                className="w-full h-12 ps-11 pe-space-md bg-surface-container-low rounded-xl font-body-sm text-body-sm text-on-surface placeholder:text-outline focus:bg-surface-container-lowest transition-all text-right shadow-inner"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="flex flex-col gap-space-xs">
            <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="register-password">
              {auth.password}
            </label>
            <div className="relative flex items-center">
              <span
                className="material-symbols-outlined absolute start-space-md text-outline text-[20px] pointer-events-none"
                aria-hidden="true"
              >
                key
              </span>
              <input
                id="register-password"
                type={reveal ? 'text' : 'password'}
                name="password"
                autoComplete="new-password"
                dir="ltr"
                className="w-full h-12 ps-11 pe-12 bg-surface-container-low rounded-xl font-body-sm text-body-sm text-on-surface focus:bg-surface-container-lowest transition-all text-right shadow-inner"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                type="button"
                aria-label={auth.togglePassword}
                aria-pressed={reveal}
                onClick={() => setReveal((value) => !value)}
                className="absolute end-space-md text-outline hover:text-on-surface flex items-center justify-center p-1"
              >
                <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                  {reveal ? 'visibility_off' : 'visibility'}
                </span>
              </button>
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
                person_add
              </span>
              <span>{auth.submitRegister}</span>
            </button>
          </div>
        </form>

        <div className="relative flex items-center justify-center">
          <div className="w-full h-px bg-surface-variant" aria-hidden="true" />
        </div>

        <p className="m-0 text-center font-body-sm text-body-sm text-on-surface-variant">
          <Link to="/login" className="text-primary font-semibold hover:underline">
            {auth.toLogin}
          </Link>
        </p>
      </AuthLayout>
    </RedirectIfAuthenticated>
  )
}
