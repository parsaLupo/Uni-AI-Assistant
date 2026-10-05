/**
 * Application routes (ADR-015: react-router-dom v7).
 *
 * Phase 03 ships the public auth routes plus one guarded placeholder to prove
 * the redirect flow; the route *groups* of docs/20-ui-navigation.md (student,
 * admin) and the real layout shell arrive in Phase 05/06. Protected routes are
 * a convenience only — DRF remains the security boundary (ADR-015).
 */
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, LoginPage, RegisterPage, RequireAuth, useAuth } from './features/auth'
import { auth, appShell } from './i18n/fa'

/**
 * Temporary authenticated landing page. Phase 06 replaces its content with the
 * dashboard; keeping it here lets Phase 03 prove the guard end to end.
 */
function DashboardPlaceholder() {
  const { user, logout } = useAuth()

  return (
    <main className="app-shell">
      <h1 className="app-shell__title">{appShell.title}</h1>
      <p className="app-shell__note">
        {auth.welcome}
        {user?.first_name ? ` ${user.first_name}` : ''} — {user?.email}
      </p>
      <p className="app-shell__note">{auth.dashboardNote}</p>
      <button type="button" className="auth-form__submit" onClick={() => void logout()}>
        {auth.logout}
      </button>
    </main>
  )
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <DashboardPlaceholder />
            </RequireAuth>
          }
        />
        {/* Anything else lands on the guarded home; the guard then decides
            between the dashboard and /login. */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}
