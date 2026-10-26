/**
 * /professors — faculty catalog from GET /professors/.
 *
 * Filters mirror the documented query parameters (docs/api/professors.md):
 * `?search=` (Persian-normalised server-side), `?department=` and `?term=`.
 * Paging and every filter live in the URL (useUrlState), so a filtered view
 * survives a reload and can be shared.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  FilterRow,
  FilterSelect,
  PageHeader,
  PaginationBar,
  SearchInput,
  SkeletonCards,
  btnSecondaryCls,
  cardCls,
} from '../../components/ui'
import { useUrlState } from '../../hooks/useUrlState'
import { common, professorsPage } from '../../i18n/fa'
import { toPersianDigits } from '../../i18n/digits'
import type { ListQuery } from '../../types/academic'

const PAGE_SIZE = 12

export function ProfessorsPage() {
  const [page, setPage] = useUrlState<number>('page', 1)
  const [search, setSearch] = useUrlState<string>('search', '', { debounce: 300 })
  const [term, setTerm] = useUrlState<string>('term', '')

  const terms = useQuery({
    queryKey: queryKeys.terms(),
    queryFn: () => academicApi.terms({ page_size: 50 }),
  })

  const query: ListQuery = {
    page,
    page_size: PAGE_SIZE,
    search: search.trim() || undefined,
    term: term || undefined,
  }
  const professors = useQuery({
    queryKey: queryKeys.professors(query),
    queryFn: () => academicApi.professors(query),
    placeholderData: (previous) => previous,
  })

  const hasFilters = Boolean(search.trim() || term)
  const changeFilter = (setter: (value: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }
  const clearFilters = () => {
    setSearch('')
    setTerm('')
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={professorsPage.title}
        subtitle={professorsPage.subtitle}
        actions={
          <SearchInput
            value={search}
            onChange={changeFilter(setSearch)}
            placeholder={professorsPage.searchPlaceholder}
            label={common.search}
          />
        }
      />

      <FilterRow>
        <FilterSelect
          icon="event"
          label={professorsPage.term}
          value={term}
          onChange={changeFilter(setTerm)}
          className="w-52"
        >
          <option value="">{professorsPage.termAll}</option>
          {(terms.data?.results ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {row.name}
              {row.is_current ? ` (${common.filterCurrent})` : ''}
            </option>
          ))}
        </FilterSelect>
        {hasFilters ? (
          <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
            {common.clearFilters}
          </button>
        ) : null}

        {professors.data ? (
          <span className="ms-auto text-label-sm text-on-surface-variant tnum">
            {common.resultsCount}: {toPersianDigits(professors.data.count)}
          </span>
        ) : null}
      </FilterRow>

      {professors.isPending ? (
        <SkeletonCards />
      ) : professors.isError ? (
        <ErrorState error={professors.error} onRetry={() => void professors.refetch()} />
      ) : professors.data.results.length === 0 ? (
        <EmptyState
          message={professorsPage.empty}
          hint={professorsPage.emptyHint}
          action={
            hasFilters ? (
              <button type="button" className={btnSecondaryCls} onClick={clearFilters}>
                {common.clearFilters}
              </button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-3">
            {professors.data.results.map((professor) => (
              <Link
                key={professor.id}
                to={`/professors/${professor.id}`}
                className={`${cardCls} group flex flex-col gap-space-sm p-space-lg transition-all hover:shadow-md`}
              >
                <div className="flex items-center gap-space-sm">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary">
                    <span className="material-symbols-outlined text-[24px]">school</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-headline-sm font-bold text-on-surface group-hover:text-primary">
                      {professor.academic_title} {professor.first_name} {professor.last_name}
                    </span>
                    <span className="text-label-sm text-on-surface-variant">
                      {professor.department.name}
                    </span>
                  </div>
                </div>
                <div className="mt-auto flex flex-wrap items-center gap-space-xs border-t border-outline-variant pt-space-sm">
                  {professor.office ? (
                    <Chip>
                      <span className="material-symbols-outlined text-[14px]">location_on</span>
                      {professor.office}
                    </Chip>
                  ) : null}
                  <Chip tone="primary">
                    <span dir="ltr">{professor.email}</span>
                  </Chip>
                </div>
              </Link>
            ))}
          </div>
          <PaginationBar
            count={professors.data.count}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </>
      )}
    </div>
  )
}
