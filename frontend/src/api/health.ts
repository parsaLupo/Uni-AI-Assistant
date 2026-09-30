import { requestJson } from './client'
import type { HealthResponse } from '../types/api'

/** GET /api/v1/health/ — used to verify backend + database availability. */
export function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/health')
}
