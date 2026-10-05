/**
 * Route guards for docs/20-ui-navigation.md.
 *
 * A guard is a *convenience, not a security boundary* (ADR-015): every API
 * call still carries a Bearer token and is authorized server-side by DRF.
 */

import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { appShell } from '../../i18n/fa'
import { useAuth } from './AuthProvider'

/** Blocks anonymous visitors until they sign in, remembering where they were going. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <main className="app-shell">
        <p className="app-shell__note" role="status">
          {appShell.loading}
        </p>
      </main>
    )
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

/** Keeps signed-in visitors off /login and /register. */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <main className="app-shell">
        <p className="app-shell__note" role="status">
          {appShell.loading}
        </p>
      </main>
    )
  }

  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from && from !== '/login' ? from : '/dashboard'} replace />
  }

  return <>{children}</>
}
