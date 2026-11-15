/**
 * /selection — Phase 11 Course Selection Assistant UI.
 *
 * The page is a thin client over `POST /students/me/course-selection/`
 * (docs/api/course-selection.md): it sends the course code (plus optional
 * what-if extras), then renders the engine's verdict, the machine-readable
 * reasons, the what-if credit totals and the backend-provided Persian
 * explanation — no eligibility logic lives in React (AGENTS.md §3, §8).
 */

import { useState, type FormEvent } from 'react'
import { checkCourseSelection, type SelectionDecision } from '../../api/selection'
import {
  Chip,
  EmptyState,
  ErrorState,
  PageHeader,
  btnPrimaryCls,
  inputCls,
  cardCls,
} from '../../components/ui'
import { toPersianDigits } from '../../i18n/digits'
import { selectionPage } from '../../i18n/fa'

export function CourseSelectionPage() {
  const [courseCode, setCourseCode] = useState('')
  const [extrasInput, setExtrasInput] = useState('')
  const [decision, setDecision] = useState<SelectionDecision | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const run = async () => {
    const code = courseCode.trim()
    if (!code || loading) return
    // Split on Arabic/Latin commas and newlines; empty tokens are dropped.
    const extras = extrasInput
      .split(/[,؛،\n]/)
      .map((token) => token.trim())
      .filter(Boolean)
    setLoading(true)
    setError(null)
    try {
      setDecision(await checkCourseSelection(code, extras))
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    void run()
  }

  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader title={selectionPage.title} subtitle={selectionPage.subtitle} />

      <form onSubmit={submit} className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
        <div className="flex flex-col gap-2">
          <label htmlFor="selection-course-code" className="text-label-lg font-bold text-on-surface">
            {selectionPage.courseCodeLabel}
          </label>
          <input
            id="selection-course-code"
            value={courseCode}
            onChange={(event) => setCourseCode(event.target.value)}
            placeholder={selectionPage.courseCodePlaceholder}
            autoComplete="off"
            className={`${inputCls} w-full max-w-sm`}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="selection-extras" className="text-label-lg font-bold text-on-surface">
            {selectionPage.extrasLabel}
          </label>
          <input
            id="selection-extras"
            value={extrasInput}
            onChange={(event) => setExtrasInput(event.target.value)}
            placeholder={selectionPage.extrasPlaceholder}
            autoComplete="off"
            className={`${inputCls} w-full max-w-md`}
          />
          <p className="m-0 text-label-sm text-outline">{selectionPage.extrasHint}</p>
        </div>
        <div>
          <button type="submit" disabled={loading || !courseCode.trim()} className={btnPrimaryCls}>
            {loading ? selectionPage.checking : selectionPage.check}
          </button>
        </div>
      </form>

      {error ? <ErrorState error={error} onRetry={() => void run()} /> : null}

      {!error && !decision && !loading ? (
        <EmptyState message={selectionPage.emptyHint} />
      ) : null}

      {decision ? <DecisionCard decision={decision} /> : null}
    </div>
  )
}

function DecisionCard({ decision }: { decision: SelectionDecision }) {
  const totals = decision.credit_totals
  return (
    <section aria-label={selectionPage.resultAria} className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
      <div className="flex flex-wrap items-center gap-space-sm">
        <Chip tone={decision.eligible ? 'success' : 'danger'}>
          {decision.eligible ? selectionPage.eligibleBadge : selectionPage.ineligibleBadge}
        </Chip>
        <span className="text-body-md text-on-surface">
          «{decision.course.title}» ({decision.course.code})
        </span>
        <Chip tone="neutral">
          {toPersianDigits(decision.course.credits)} {selectionPage.creditUnit}
        </Chip>
        <span className="text-label-sm text-outline">
          {decision.term_name ? `${selectionPage.termLabel}: ${decision.term_name}` : ''}
        </span>
      </div>

      <div>
        <h2 className="m-0 mb-1 text-title-md font-bold text-on-surface">{selectionPage.explanationTitle}</h2>
        <p className="m-0 whitespace-pre-line text-body-md text-on-surface-variant">
          {decision.explanation.text}
        </p>
      </div>

      {decision.reasons.length > 0 ? (
        <div>
          <h2 className="m-0 mb-1 text-title-md font-bold text-on-surface">{selectionPage.reasonsTitle}</h2>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {decision.reasons.map((reason) => (
              <li key={`${reason.code}-${reason.message}`} className="flex items-start gap-space-sm">
                <Chip tone="warning">{reason.code}</Chip>
                <span className="text-body-sm text-on-surface-variant">{reason.message}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div>
        <h2 className="m-0 mb-1 text-title-md font-bold text-on-surface">{selectionPage.totalsTitle}</h2>
        {totals.over_limit ? <Chip tone="danger">{selectionPage.overLimit}</Chip> : null}
        <table className="mt-1 w-full max-w-md text-right text-body-sm">
          <tbody>
            <TotalRow label={selectionPage.totalsPlanned} value={totals.planned} />
            <TotalRow label={selectionPage.totalsCandidate} value={totals.candidate} />
            <TotalRow label={selectionPage.totalsExtra} value={totals.extra} />
            <TotalRow label={selectionPage.totalsTotal} value={totals.total_with_candidate} />
            <TotalRow label={selectionPage.totalsLimit} value={totals.limit} />
          </tbody>
        </table>
      </div>

      <p className="m-0 text-label-sm text-outline">
        {selectionPage.engineLabel}: {decision.engine_version}
      </p>
    </section>
  )
}

function TotalRow({ label, value }: { label: string; value: number }) {
  return (
    <tr>
      <td className="py-1 text-on-surface-variant">{label}</td>
      <td className="py-1 tnum font-bold text-on-surface">{toPersianDigits(value)}</td>
    </tr>
  )
}
