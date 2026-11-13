/**
 * Application routes (ADR-015: react-router-dom v7).
 *
 * Route inventory follows docs/20-ui-navigation.md exactly: public auth,
 * the student group behind `RequireAuth`, and the admin group behind
 * `RequireRole`. The authenticated group renders inside the persistent
 * `AppShell` (docs/20 "Layout"). Guards are a convenience only — DRF remains
 * the security boundary (ADR-015).
 */
import { Link, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import {
  AuthProvider,
  LoginPage,
  RegisterPage,
  RequireAuth,
  RequireRole,
  StudentOnly,
} from './features/auth'
import {
  ADMIN_LINKS,
  AdminAnalyticsPage,
  AdminAnnouncementsPage,
  AdminCoursesPage,
  AdminDocumentsPage,
  AdminExamsPage,
  AdminOverviewPage,
  AdminProfessorsPage,
  AdminTermsPage,
  AdminUsersPage,
} from './features/admin'
import { AssistantPage } from './features/assistant'
import { AnnouncementsPage } from './features/announcements'
import { CalendarPage } from './features/calendar'
import { CourseDetailPage, CoursesPage } from './features/courses'
import { DashboardPage } from './features/dashboard'
import { ExamsPage } from './features/exams'
import { ProfessorDetailPage, ProfessorsPage } from './features/professors'
import { ProfilePage } from './features/profile'
import { CourseSelectionPage } from './features/selection'
import { NotificationsPage } from './features/notifications'
import { common, nav as navText } from './i18n/fa'

function ShellLayout() {
  return (
    <RequireAuth>
      <AppShell>
        <Outlet />
      </AppShell>
    </RequireAuth>
  )
}

/** Persian catch-all — docs/20 defines no other unknown-URL behaviour. */
function NotFoundRoute() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-space-md px-gutter py-space-xl text-center">
      <span className="material-symbols-outlined text-[48px] text-outline">explore_off</span>
      <h1 className="m-0 text-headline-lg font-bold text-on-surface">{common.notFoundTitle}</h1>
      <p className="m-0 text-body-md text-on-surface-variant">{common.notFoundBody}</p>
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-space-xs rounded bg-primary-container px-space-lg py-space-sm text-label-lg font-semibold text-on-primary transition-colors hover:bg-[#2563EB]"
      >
        {navText.dashboard}
      </Link>
    </div>
  )
}

/** Admin sub-routes come from `features/admin` so the overview's quick links
 *  and the router can never drift apart. */
export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route element={<ShellLayout />}>
          {/* Student home — admins are bounced to the admin overview, so a
              refresh or direct URL can never land them on this screen. */}
          <Route
            path="/dashboard"
            element={
              <StudentOnly>
                <DashboardPage />
              </StudentOnly>
            }
          />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/conversations/:id" element={<AssistantPage />} />
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="/courses/:id" element={<CourseDetailPage />} />
          <Route path="/professors" element={<ProfessorsPage />} />
          <Route path="/professors/:id" element={<ProfessorDetailPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/exams" element={<ExamsPage />} />
          <Route path="/announcements" element={<AnnouncementsPage />} />
          <Route path="/selection" element={<CourseSelectionPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          <Route
            path="/admin"
            element={
              <RequireRole roles={['ADMIN', 'SUPERADMIN']}>
                <AdminOverviewPage />
              </RequireRole>
            }
          />
          {ADMIN_LINKS.map(({ path }) => {
            // Phase 13: every management section is a real CRUD screen over
            // its documented admin endpoint (`api/admin.ts`).
            const pages: Record<string, React.ReactElement> = {
              users: <AdminUsersPage />,
              courses: <AdminCoursesPage />,
              professors: <AdminProfessorsPage />,
              terms: <AdminTermsPage />,
              exams: <AdminExamsPage />,
              documents: <AdminDocumentsPage />,
              announcements: <AdminAnnouncementsPage />,
              analytics: <AdminAnalyticsPage />,
            }
            return (
              <Route
                key={path}
                path={`/admin/${path}`}
                element={
                  <RequireRole roles={['ADMIN', 'SUPERADMIN']}>
                    {pages[path] ?? <AdminOverviewPage />}
                  </RequireRole>
                }
              />
            )
          })}

          {/* Anything else lands on the guarded home; the guard then decides
              between the dashboard and /login. */}
          <Route path="*" element={<NotFoundRoute />} />
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}
