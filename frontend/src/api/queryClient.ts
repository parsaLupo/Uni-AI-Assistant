import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './client'

/**
 * The single QueryClient policy (ADR-013).
 *
 * - Never retry a deliberate server answer (4xx) — a 403 stays a 403;
 *   transient failures (5xx/network) get exactly one retry.
 * - `staleTime` keeps list screens from re-fetching on every mount while
 *   still picking up backend changes within 30s.
 * - Error → Persian text mapping happens at the component edge via
 *   `persianErrorText(error.code)`; the client keeps codes stable.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) {
          return false
        }
        return failureCount < 1
      },
      retryDelay: 500,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})