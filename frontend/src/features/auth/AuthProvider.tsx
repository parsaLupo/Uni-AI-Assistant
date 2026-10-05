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
  login: (email: string, password: string) => Promise<void>
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
  // Guards React StrictMode's double-invoked effect in development.
  const booted = useRef(false)

  useEffect(() => {
    if (booted.current) {
      return
    }
    booted.current = true

    let cancelled = false
    void (async () => {
      try {
        const session = await authApi.refreshSession()
        const profile = await authApi.fetchMe()
        if (!cancelled) {
          setUser(profile)
          setStatus('authenticated')
        }
        void session
      } catch {
        // No cookie, expired session, replayed token or offline: all of these
        // simply mean "not signed in" for a page load. The server stays the
        // authority on every real request (ADR-015).
        setAccessToken(null)
        if (!cancelled) {
          setUser(null)
          setStatus('anonymous')
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const session = await authApi.login(email, password)
    // Prefer the full profile, but the session summary is enough to proceed.
    try {
      setUser(await authApi.fetchMe())
    } catch {
      setUser(userFromSession(session))
    }
    setStatus('authenticated')
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
