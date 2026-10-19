/**
 * Persistent application shell (docs/20 "Layout"): sticky top bar, RTL side
 * navigation with an active state, responsive drawer for small screens, the
 * mockup footer, and a user chip with logout.
 *
 * The mockups provide page *content* only — this shell follows the layout
 * rules of docs/20 using the same DESIGN.md tokens, so it matches the pages
 * without inventing a second design language.
 */

import { useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../features/auth'
import { auth as authText, nav as navText, shell } from '../i18n/fa'
import { roleLabels } from '../i18n/labels'

interface NavItem {
  to: string
  label: string
  icon: string
  end?: boolean
}

const STUDENT_ITEMS: NavItem[] = [
  { to: '/dashboard', label: navText.dashboard, icon: 'dashboard', end: true },
  { to: '/assistant', label: navText.assistant, icon: 'smart_toy' },
  { to: '/courses', label: navText.courses, icon: 'menu_book' },
  { to: '/professors', label: navText.professors, icon: 'school' },
  { to: '/calendar', label: navText.calendar, icon: 'event' },
  { to: '/exams', label: navText.exams, icon: 'assignment' },
  { to: '/announcements', label: navText.announcements, icon: 'campaign' },
  { to: '/profile', label: navText.profile, icon: 'account_circle' },
]

const ADMIN_ITEMS: NavItem[] = [{ to: '/admin', label: navText.adminOverview, icon: 'settings' }]

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERADMIN'

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    [
      'flex items-center gap-space-sm rounded-lg px-space-md py-2 text-body-sm transition-colors',
      isActive
        ? 'bg-surface-container-high text-primary font-bold shadow-xs'
        : 'text-on-surface-variant hover:bg-surface-container-low hover:text-primary',
    ].join(' ')

  const render = (item: NavItem) => (
    <NavLink key={item.to} to={item.to} end={item.end} className={linkCls} onClick={onNavigate}>
      <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
      <span>{item.label}</span>
    </NavLink>
  )

  return (
    <nav aria-label={navText.menu} className="flex flex-col gap-1">
      {STUDENT_ITEMS.map(render)}
      {isAdmin ? (
        <>
          <div className="mt-space-sm border-t border-outline-variant pt-space-sm">
            <span className="px-space-md text-label-sm font-bold text-outline">{navText.admin}</span>
          </div>
          {ADMIN_ITEMS.map(render)}
        </>
      ) : null}
    </nav>
  )
}

function UserChip() {
  const { user, logout } = useAuth()
  const name = user ? `${user.first_name} ${user.last_name}`.trim() || user.email : ''
  return (
    <div className="flex items-center gap-space-sm">
      <div className="hidden flex-col items-end leading-tight sm:flex">
        <span className="text-label-md font-bold text-on-surface">{name}</span>
        <span className="text-label-sm text-on-surface-variant">
          {user ? roleLabels[user.role] : ''}
        </span>
      </div>
      <div
        aria-hidden="true"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-container text-on-primary"
      >
        <span className="material-symbols-outlined text-[20px]">person</span>
      </div>
      <button
        type="button"
        onClick={() => void logout()}
        title={authText.logout}
        aria-label={authText.logout}
        className="flex h-9 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-error-container/60 hover:text-on-error-container"
      >
        <span className="material-symbols-outlined text-[20px]">logout</span>
      </button>
    </div>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()
  const closeDrawer = () => setDrawerOpen(false)

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-40 border-b border-outline-variant bg-surface-container-lowest/90 backdrop-blur">
        <div className="flex h-16 items-center justify-between gap-space-md px-gutter-desktop">
          <div className="flex items-center gap-space-sm">
            <button
              type="button"
              className="flex h-10 w-10 items-center justify-center rounded-lg text-primary transition-colors hover:bg-surface-container-low lg:hidden"
              onClick={() => setDrawerOpen((open) => !open)}
              aria-label={drawerOpen ? navText.closeMenu : navText.menu}
              aria-expanded={drawerOpen}
            >
              <span className="material-symbols-outlined text-[24px]">
                {drawerOpen ? 'close' : 'menu'}
              </span>
            </button>
            <NavLink
              to="/dashboard"
              className="flex items-center gap-space-sm"
              onClick={closeDrawer}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-on-primary">
                <span className="material-symbols-outlined text-[22px]">school</span>
              </span>
              <span className="text-headline-sm font-bold text-primary">{navText.brand}</span>
            </NavLink>
          </div>
          <UserChip />
        </div>
      </header>

      <div className="flex flex-1">
        {/* Desktop rail (RTL: the first flex child sits on the right). */}
        <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] w-64 shrink-0 overflow-y-auto border-l border-outline-variant bg-surface-container-lowest p-space-md lg:block">
          <NavList />
        </aside>

        {/* Mobile drawer */}
        {drawerOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
            <button
              type="button"
              aria-label={navText.closeMenu}
              className="absolute inset-0 bg-inverse-surface/40"
              onClick={closeDrawer}
            />
            <aside className="absolute inset-y-0 right-0 w-72 overflow-y-auto bg-surface-container-lowest p-space-md shadow-xl">
              <NavList onNavigate={closeDrawer} />
            </aside>
          </div>
        ) : null}

        <main key={location.pathname} className="min-w-0 flex-1 pb-space-xl">
          {children}
        </main>
      </div>

      <footer className="w-full border-t border-outline-variant bg-surface-container-low py-space-md">
        <div className="flex flex-col items-center justify-between gap-space-sm px-gutter-desktop text-label-sm text-on-surface-variant sm:flex-row">
          <div className="flex items-center gap-space-xs">
            <span className="h-2 w-2 rounded-full bg-secondary" />
            <span>{shell.footerStatus}</span>
          </div>
          <div className="flex items-center gap-space-md">
            <span className="tnum">{shell.footerVersion}</span>
            <span aria-hidden="true">•</span>
            <span>{shell.footerDocs}</span>
            <span aria-hidden="true">•</span>
            <span>{shell.footerSupport}</span>
          </div>
        </div>
      </footer>
    </div>
  )
}