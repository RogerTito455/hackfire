// Domain types and pure functions. No React, no fetch, no styling.

export type TriageStatus = 'pending' | 'evacuating' | 'no_answer' | 'needs_rescue'

export const TRIAGE_STATUSES: readonly TriageStatus[] = [
  'pending',
  'evacuating',
  'no_answer',
  'needs_rescue',
]

export interface Neighbor {
  id: string
  name: string
  address: string
  zone: string
  lat: number
  lon: number
  status: TriageStatus
  people: number | null
  mobility: string | null
  observation: string | null
  updated_at: string | null
}

export interface Rescue {
  rescue_id: string
  neighbor: Neighbor
  minutes_to_impact: number | null
  priority: number
}

export type StatusCounts = Record<TriageStatus, number>

export function countByStatus(neighbors: readonly Neighbor[]): StatusCounts {
  const counts: StatusCounts = { pending: 0, evacuating: 0, no_answer: 0, needs_rescue: 0 }
  for (const neighbor of neighbors) counts[neighbor.status] += 1
  return counts
}
