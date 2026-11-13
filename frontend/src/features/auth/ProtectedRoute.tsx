/**
 * Route guards for docs/20-ui-navigation.md.
 *
 * A guard is a *convenience, not a security boundary* (ADR-015): every API
 * call still carries a Bearer token and is authorized server-side by DRF.
 */

import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { auth as authText } from '../../i18n/fa'
import type { AuthUser, UserRole } from '../../types/api'
import { useAuth } from './AuthProvider'

/** Role-aware landing route: admins open the admin overview, students the
 *  student dashboard (docs/20 home routing). */
export function homeForRole(user: Pick<AuthUser, 'role'> | null): string {
  return user && (user.role === 'ADMIN' || user.role === 'SUPERADMIN') ? '/admin' : '/dashboard'
}

/** Full-screen Persian loading state shown while the session is restored. */
export function GateLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-screen flex-col items-center justify-center gap-space-sm bg-background text-body-md text-on-surface-variant"
    >
      <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-outline-variant border-t-primary motion-reduce:animate-none" />
      <p className="m-0">{authText.sessionRestoring}</p>
    </div>
  )
}

/** Blocks anonymous visitors until they sign in, remembering where they were going. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <GateLoading />
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

/** Keeps signed-in visitors off /login and /register. */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <GateLoading />
  }

  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from && from !== '/login' ? from : homeForRole(user)} replace />
  }

  return <>{children}</>
}

/**
 * Client-side role gate for admin screens (docs/20 admin routes). Convenience
 * only — DRF `IsAdmin` remains the authority (docs/05 section 7), so a user who
 * bypasses this in the browser still gets 403 from the API.
 */
export function RequireRole({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <GateLoading />
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (user && !roles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

/**
 * Keeps administrator accounts off the student-only screens (UI refinement:
 * the student dashboard is never shown to admins). Admins are redirected to
 * the admin overview; students pass through untouched.
 */
export function StudentOnly({ children }: { children: ReactNode }) {
  const { status, user } = useAuth()

  if (status === 'loading') {
    return <GateLoading />
  }

  if (user && (user.role === 'ADMIN' || user.role === 'SUPERADMIN')) {
    return <Navigate to="/admin" replace />
  }

  return <>{children}</>
}
