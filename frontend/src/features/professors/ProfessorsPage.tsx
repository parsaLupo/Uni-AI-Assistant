/** /professors — catalog cards from GET /professors/ (search: normalized Persian). */

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { queryKeys } from '../../api/keys'
import { academicApi } from '../../api/resources'
import {
  Chip,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  PaginationBar,
  cardCls,
  inputCls,
} from '../../components/ui'
import { common, professorsPage } from '../../i18n/fa'
import type { ListQuery } from '../../types/academic'

const PAGE_SIZE = 12

export function ProfessorsPage() {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const query: ListQuery = { page, page_size: PAGE_SIZE, search: debounced || undefined }
  const professors = useQuery({
    queryKey: queryKeys.professors(query),
    queryFn: () => academicApi.professors(query),
    placeholderData: (previous) => previous,
  })

  return (
    <div className="flex flex-col gap-space-md px-gutter-desktop pt-space-lg">
      <PageHeader
        title={professorsPage.title}
        subtitle={professorsPage.subtitle}
        actions={
          <div className="relative w-full max-w-sm">
            <span className="material-symbols-outlined pointer-events-none absolute inset-y-0 right-3 my-auto text-[20px] text-outline">
              search
            </span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={professorsPage.searchPlaceholder}
              aria-label={common.search}
              className={`${inputCls} pr-10`}
            />
          </div>
        }
      />

      {professors.isPending ? (
        <LoadingState />
      ) : professors.isError ? (
        <ErrorState error={professors.error} onRetry={() => void professors.refetch()} />
      ) : professors.data.results.length === 0 ? (
        <EmptyState message={professorsPage.empty} />
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
                  <Chip tone="primary">{professor.email}</Chip>
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