/**
 * /selection — Phase 11 Course Selection Assistant UI.
 *
 * The page is a thin client over `POST /students/me/course-selection/`
 * (docs/api/course-selection.md): it sends the typed course code *or* Persian
 * course name (plus optional what-if extras), then renders the engine's
 * verdict, the machine-readable reasons, the what-if credit totals and the
 * backend-provided Persian explanation — no eligibility logic lives in React
 * (AGENTS.md §3, §8).
 *
 * Name resolution is backend-only and deterministic. When a name matches more
 * than one catalog row the API returns `status: "ambiguous"` with the candidate
 * list; this page shows that list and never evaluates a candidate until the
 * student explicitly picks one (then the chosen *course code* is submitted, so
 * the very same `CourseSelectionEngine` runs).
 */

import { useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../../api/client'
import {
  checkCourseSelection,
  type AmbiguousSelection,
  type CourseCandidate,
  type SelectionDecision,
  type SelectionResult,
} from '../../api/selection'
import {
  Chip,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  btnPrimaryCls,
  btnSecondaryCls,
  inputCls,
  cardCls,
} from '../../components/ui'
import { toPersianDigits } from '../../i18n/digits'
import { selectionPage } from '../../i18n/fa'

/** Split what-if codes on Arabic/Latin commas and newlines; drop empties. */
function parseExtras(input: string): string[] {
  return input
    .split(/[,؛،\n]/)
    .map((token) => token.trim())
    .filter(Boolean)
}

export function CourseSelectionPage() {
  const [courseQuery, setCourseQuery] = useState('')
  const [extrasInput, setExtrasInput] = useState('')
  const [result, setResult] = useState<SelectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  /** Candidate whose own evaluation is in flight (spinner on that row only). */
  const [pendingCode, setPendingCode] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)
  // A ref, not just `loading`: two clicks in the same tick both see the stale
  // `loading === false` of the current render, so the synchronous guard is what
  // actually prevents the second request.
  const inFlight = useRef(false)

  const notFound = error instanceof ApiError && error.code === 'NOT_FOUND'

  /**
   * Resolve + evaluate one query. `candidateCode` is set only when the student
   * clicked a row in the ambiguity list; the ambiguity list stays visible until
   * the engine answers so the page never flashes back to the empty state.
   */
  const run = async (query: string, candidateCode?: string) => {
    const trimmed = query.trim()
    // Guard both the form and rapid double clicks: one request at a time.
    if (!trimmed || inFlight.current) return
    inFlight.current = true
    setLoading(true)
    setPendingCode(candidateCode ?? null)
    setError(null)
    if (!candidateCode) {
      setResult(null)
    }
    try {
      setResult(await checkCourseSelection(trimmed, parseExtras(extrasInput)))
    } catch (err) {
      setResult(null)
      setError(err)
    } finally {
      inFlight.current = false
      setLoading(false)
      setPendingCode(null)
    }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    void run(courseQuery)
  }

  return (
    <div className="flex flex-col gap-space-lg">
      <PageHeader title={selectionPage.title} subtitle={selectionPage.subtitle} />

      <form onSubmit={submit} className={`${cardCls} flex flex-col gap-space-md p-space-lg`}>
        <div className="flex flex-col gap-2">
          <label htmlFor="selection-course-query" className="text-label-lg font-bold text-on-surface">
            {selectionPage.courseQueryLabel}
          </label>
          <input
            id="selection-course-query"
            value={courseQuery}
            onChange={(event) => setCourseQuery(event.target.value)}
            placeholder={selectionPage.courseQueryPlaceholder}
            autoComplete="off"
            className={`${inputCls} w-full max-w-sm`}
          />
          <p className="m-0 text-label-sm text-outline">{selectionPage.courseQueryHint}</p>
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
          <button
            type="submit"
            disabled={loading || !courseQuery.trim()}
            className={btnPrimaryCls}
          >
            {loading && pendingCode === null ? selectionPage.checking : selectionPage.check}
          </button>
        </div>
      </form>

      {notFound ? (
        <EmptyState
          message={selectionPage.notFoundTitle}
          hint={selectionPage.notFoundMessage}
        />
      ) : null}

      {error && !notFound ? <ErrorState error={error} onRetry={() => void run(courseQuery)} /> : null}

      {!error && !result && !loading ? <EmptyState message={selectionPage.emptyHint} /> : null}

      {loading && pendingCode === null && !result ? (
        <LoadingState label={selectionPage.checking} />
      ) : null}

      {result?.status === 'ambiguous' ? (
        <AmbiguityCard
          result={result}
          loading={loading}
          pendingCode={pendingCode}
          onSelect={(code) => void run(code, code)}
        />
      ) : null}

      {result?.status === 'resolved' ? <DecisionCard decision={result} /> : null}
    </div>
  )
}

function AmbiguityCard({
  result,
  loading,
  pendingCode,
  onSelect,
}: {
  result: AmbiguousSelection
  loading: boolean
  pendingCode: string | null
  onSelect: (code: string) => void
}) {
  return (
    <section
      aria-label={selectionPage.ambiguousAria}
      className={`${cardCls} flex flex-col gap-space-md p-space-lg`}
    >
      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-title-md font-bold text-on-surface">{selectionPage.ambiguousTitle}</h2>
        <p className="m-0 text-body-sm text-on-surface-variant">{selectionPage.ambiguousHint}</p>
        {result.total > result.candidates.length ? (
          <p className="m-0 text-label-sm text-outline">{selectionPage.ambiguousMore}</p>
        ) : null}
      </div>

      <ul className="m-0 flex list-none flex-col gap-space-sm p-0">
        {result.candidates.map((candidate) => (
          <li key={candidate.code}>
            <CandidateButton
              candidate={candidate}
              busy={pendingCode === candidate.code}
              disabled={loading}
              onSelect={onSelect}
            />
          </li>
        ))}
      </ul>
    </section>
  )
}

function CandidateButton({
  candidate,
  busy,
  disabled,
  onSelect,
}: {
  candidate: CourseCandidate
  busy: boolean
  disabled: boolean
  onSelect: (code: string) => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onSelect(candidate.code)}
      className={`${btnSecondaryCls} w-full flex-col items-stretch gap-1 text-start disabled:opacity-60`}
    >
      <span className="flex flex-wrap items-center justify-between gap-space-sm">
        <span className="font-bold">{candidate.title}</span>
        <Chip tone="primary">{candidate.code}</Chip>
      </span>
      <span className="flex flex-wrap items-center justify-between gap-space-sm text-label-sm font-normal text-on-surface-variant">
        <span className="flex flex-wrap items-center gap-space-sm">
          {candidate.department ? <span>{candidate.department}</span> : null}
          <span>
            {toPersianDigits(candidate.credits)} {selectionPage.creditUnit}
          </span>
          {candidate.course_type ? <span>{candidate.course_type}</span> : null}
        </span>
        <span className="inline-flex items-center gap-1 text-primary">
          {busy ? (
            <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary/40 border-t-primary motion-reduce:animate-none" />
          ) : null}
          {selectionPage.selectCandidate}
          <span aria-hidden="true" className="material-symbols-outlined text-[18px]">
            chevron_left
          </span>
        </span>
      </span>
    </button>
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
