/**
 * Phase 00 baseline shell — intentionally not a feature screen.
 *
 * Phase 00 non-goals forbid UI implementation; this placeholder only proves the
 * React + TypeScript build pipeline works and that the document renders in RTL
 * Persian, as required by AGENTS.md ("Language & Localization") and
 * docs/20-ui-navigation.md. Strings come from src/i18n/fa.ts rather than being
 * written inline (docs/02-system-architecture.md). Real screens from
 * docs/20-ui-navigation.md arrive in later phases.
 */
import { appShell } from './i18n/fa'

export function App() {
  return (
    <main className="app-shell">
      <h1 className="app-shell__title">{appShell.title}</h1>
      <p className="app-shell__note">{appShell.baselineNote}</p>
    </main>
  )
}
