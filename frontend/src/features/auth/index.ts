export { AuthProvider, useAuth, type AuthStatus } from './AuthProvider'
export {
  GateLoading,
  homeForRole,
  landingFor,
  RequireAuth,
  RequireRole,
  RedirectIfAuthenticated,
  StudentOnly,
} from './ProtectedRoute'
export { LoginPage } from './LoginPage'
export { RegisterPage } from './RegisterPage'
export { changePassword } from './api'
export { getAccessToken, setAccessToken } from './session'
