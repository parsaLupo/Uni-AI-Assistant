import type { ReactNode } from 'react'
import { auth, shell } from '../../i18n/fa'

/**
 * Shared shell for the public auth screens — ported from `UI/Login.html` +
 * `loginDESIGN.md` (ADR-016 tokens come from `@theme` in `src/theme.css`).
 *
 * Scope decisions (honest UI, docs/06 section 8):
 * - The decorative column keeps only claims true of *this* system (Argon2id,
 *   rate limiting, HttpOnly refresh — ADR-014). Mockup theatre with no backend
 *   (role tabs, SMS-OTP, SSO/CAS buttons, "forgot password", TLS badge) is
 *   omitted rather than faked, and the external stock image is replaced with a
 *   gradient panel so the screen works offline (OA-20, fonts aside).
 * - Positioning uses logical utilities (`start-*`, `ps-*`, `pe-*`) so the RTL
 *   requirement (AGENTS.md rule 12) holds structurally; the app's `dir="rtl"`
 *   never flips (ADR-010), so rendering matches the RTL-authored mockup.
 */
interface AuthLayoutProps {
  title: string
  subtitle: string
  children: ReactNode
}

function SecurityItem({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <li className="flex items-start gap-space-xs p-space-sm rounded-xl bg-surface-container-low/70">
      <span className="material-symbols-outlined text-secondary text-[20px] mt-0.5" aria-hidden="true">
        {icon}
      </span>
      <div className="flex flex-col">
        <span className="font-label-sm text-label-sm text-on-surface font-semibold">{title}</span>
        <span className="font-label-sm text-label-sm text-on-surface-variant">{body}</span>
      </div>
    </li>
  )
}

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-surface-container-low/40 px-gutter py-space-xl flex items-center justify-center">
      {/* Ambient academic geometric backdrop (decorative only). */}
      <div
        aria-hidden="true"
        className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-primary-fixed/20 blur-3xl pointer-events-none"
      />
      <div
        aria-hidden="true"
        className="absolute -bottom-24 -right-24 w-80 h-80 rounded-full bg-secondary-fixed/25 blur-3xl pointer-events-none"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[radial-gradient(#1e3a8a_1px,transparent_1px)] [background-size:24px_24px] opacity-[0.035] pointer-events-none"
      />

      <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-space-xl items-center relative z-10">
        {/* Decorative column — stacks under the form on mobile, like the mockup. */}
        <div className="lg:col-span-5 flex flex-col gap-space-lg order-2 lg:order-1">
          <div className="inline-flex items-center gap-space-xs px-space-md py-space-xs rounded-full bg-surface-container-high w-fit">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" aria-hidden="true" />
            <span className="font-label-sm text-label-sm text-primary font-bold">{auth.heroBadge}</span>
          </div>

          <div className="flex flex-col gap-space-sm">
            <h2 className="font-headline-lg text-headline-lg text-on-surface">{auth.heroTitle}</h2>
            <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">{auth.heroBody}</p>
          </div>

          {/* Visual panel standing in for the mockup's external stock photo. */}
          <div className="relative rounded-2xl overflow-hidden shadow-md bg-gradient-to-br from-primary-container to-secondary-container h-44 flex flex-col items-center justify-center gap-space-xs text-on-primary">
            <span className="material-symbols-outlined text-[44px]" aria-hidden="true">
              school
            </span>
            <span className="font-label-lg text-label-lg font-bold">{auth.heroVisualTitle}</span>
            <span className="font-label-sm text-label-sm opacity-90">{auth.heroVisualBody}</span>
          </div>

          <div className="bg-surface-container-lowest rounded-2xl p-space-lg shadow-sm flex flex-col gap-space-md">
            <span className="font-label-lg text-label-lg text-primary font-bold flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                policy
              </span>
              {auth.secTitle}
            </span>
            <ul className="grid grid-cols-1 sm:grid-cols-3 gap-space-sm m-0 p-0 list-none">
              <SecurityItem icon="lock_clock" title={auth.secHashTitle} body={auth.secHashBody} />
              <SecurityItem icon="speed" title={auth.secRateTitle} body={auth.secRateBody} />
              <SecurityItem icon="lock" title={auth.secSessionTitle} body={auth.secSessionBody} />
            </ul>
          </div>
        </div>

        {/* Auth card */}
        <div className="lg:col-span-7 order-1 lg:order-2 relative rounded-3xl bg-surface-container-lowest shadow-md p-space-xl flex flex-col gap-space-lg">
          <div className="flex flex-col gap-space-xs">
            <span className="inline-flex items-center gap-space-xs w-fit font-label-sm text-label-sm bg-surface-container text-primary font-bold px-space-sm py-space-xs rounded-full">
              <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                verified_user
              </span>
              {shell.roleStudent} · {shell.footerVersion}
            </span>
            <h1 className="font-headline-xl text-headline-xl text-on-surface m-0">{title}</h1>
            <p className="font-body-md text-body-md text-on-surface-variant m-0">{subtitle}</p>
          </div>

          {children}

          <p className="font-label-sm text-label-sm text-on-surface-variant text-center m-0">
            {shell.footerStatus}
          </p>
        </div>
      </div>
    </main>
  )
}