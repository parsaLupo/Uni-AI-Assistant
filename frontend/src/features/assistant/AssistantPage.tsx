/**
 * /assistant (+ /conversations/:id) — Smart AssistantDESIGN.md shell.
 *
 * The design's chat surface needs the Phase 10 conversation API
 * (POST /conversations/:id/messages/, docs/api/chat.md), which does not exist
 * yet, so the composer is rendered but disabled with the honest Persian notice
 * (assistantPage.notReady*) rather than a fake reply. History shows the empty
 * state for the same reason. Phase 10 swaps the notice for live messages —
 * layout, RTL and styling stay as-is.
 */

import { PageHeader, EmptyState, cardCls } from '../../components/ui'
import { assistantPage } from '../../i18n/fa'

export function AssistantPage() {
  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader
        title={assistantPage.title}
        subtitle={assistantPage.subtitle}
        actions={
          <button type="button" disabled className="rounded bg-primary-container px-space-md py-2 text-label-lg font-semibold text-on-primary opacity-75">
            {assistantPage.newChat}
          </button>
        }
      />

      <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-[1fr_18rem]">
        {/* Main conversation column */}
        <section className={`${cardCls} flex flex-col gap-space-md p-space-lg`} aria-label={assistantPage.title}>
          <div className="flex flex-col items-center gap-space-sm rounded-xl bg-surface-container-low px-space-lg py-space-xl text-center">
            <span aria-hidden="true" className="material-symbols-outlined text-[40px] text-primary">
              smart_toy
            </span>
            <h2 className="m-0 text-headline-md font-bold text-on-surface">{assistantPage.welcomeTitle}</h2>
            <p className="m-0 max-w-lg text-body-sm text-on-surface-variant">{assistantPage.welcomeBody}</p>
          </div>

          <div role="status" aria-live="polite" className="flex flex-col gap-1 rounded-xl border border-[#FDE68A] bg-[#FFFBEB] px-space-md py-space-sm">
            <span className="text-label-lg font-bold text-[#B45309]">{assistantPage.notReadyTitle}</span>
            <span className="text-body-sm text-[#92400E]">{assistantPage.notReadyBody}</span>
          </div>

          <form className="flex items-end gap-space-sm" onSubmit={(event) => event.preventDefault()}>
            <label htmlFor="assistant-composer" className="sr-only">
              {assistantPage.composerPlaceholder}
            </label>
            <textarea
              id="assistant-composer"
              dir="auto"
              rows={2}
              disabled
              placeholder={assistantPage.composerPlaceholder}
              className={`${cardCls} min-h-[3rem] w-full resize-y px-space-md py-space-sm text-body-sm opacity-75`}
            />
            <button type="submit" disabled className="rounded bg-primary-container px-space-lg py-3 text-label-lg font-semibold text-on-primary opacity-75">
              {assistantPage.send}
            </button>
          </form>
        </section>

        {/* History column (Phase 10 fills it from /conversations/) */}
        <aside className={`${cardCls} flex flex-col gap-space-sm p-space-md`} aria-label={assistantPage.history}>
          <h3 className="m-0 text-label-lg font-bold text-on-surface">{assistantPage.history}</h3>
          <EmptyState message={assistantPage.noHistory} />
        </aside>
      </div>
    </div>
  )
}
