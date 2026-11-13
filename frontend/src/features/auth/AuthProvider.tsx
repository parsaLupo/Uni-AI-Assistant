/**
 * Authentication state for the SPA (docs/05 section 3).
 *
 * On boot the provider attempts a silent refresh (rotating HttpOnly cookie →
 * new access token) and then loads `/auth/me/`; failure at any step simply
 * means an anonymous visitor. Screens never see raw tokens — only the user
 * profile and the three actions.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type { AuthSession, AuthUser } from '../../types/api'
import * as authApi from './api'
import { setAccessToken } from './session'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  /** Resolves with the signed-in profile so callers can route by role. */
  login: (email: string, password: string) => Promise<AuthUser>
  register: (input: authApi.RegisterInput) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function userFromSession(session: AuthSession): AuthUser {
  return {
    id: session.user.id,
    email: session.user.email,
    role: session.user.role,
    first_name: session.user.first_name ?? '',
    last_name: session.user.last_name ?? '',
    is_active: true,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<AuthUser | null>(null)
  // Runs the silent refresh exactly once. The ref guards React StrictMode's
  // double-invoked effect: a second POST /auth/refresh with the same rotating
  // cookie would race the first rotation and trip reuse detection (ADR-014),
  // revoking the session family the boot is trying to restore.
  const booted = useRef(false)

  useEffect(() => {
    if (booted.current) {
      return
    }
    booted.current = true

    // No `cancelled` flag here deliberately: StrictMode runs effect 1, cleans
    // it up, then runs effect 2 (which the ref above skips) — so gating the
    // state update on "not cleaned up" deadlocks the gate at 'loading' forever
    // ("در حال بازیابی نشست…"). The boot promise must always settle the status.
    // AuthProvider is the app root and never unmounts in practice, and React
    // ignores setState after unmount, so there is nothing for the flag to guard.
    void (async () => {
      try {
        const session = await authApi.refreshSession()
        const profile = await authApi.fetchMe()
        setUser(profile)
        setStatus('authenticated')
        void session
      } catch {
        // No cookie, expired session, replayed token or offline: all of these
        // simply mean "not signed in" for a page load. The server stays the
        // authority on every real request (ADR-015).
        setAccessToken(null)
        setUser(null)
        setStatus('anonymous')
      }
    })()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const session = await authApi.login(email, password)
    // Prefer the full profile, but the session summary is enough to proceed.
    let profile: AuthUser
    try {
      profile = await authApi.fetchMe()
    } catch {
      profile = userFromSession(session)
    }
    setUser(profile)
    setStatus('authenticated')
    return profile
  }, [])

  const register = useCallback(async (input: authApi.RegisterInput) => {
    const session = await authApi.register(input)
    try {
      setUser(await authApi.fetchMe())
    } catch {
      setUser(userFromSession(session))
    }
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
    setStatus('anonymous')
  }, [])

  const value = useMemo(
    () => ({ status, user, login, register, logout }),
    [status, user, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return context
}
