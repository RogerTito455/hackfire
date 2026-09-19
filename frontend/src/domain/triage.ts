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

// Mirrors Route and TravelMode in backend/app/models.py (the tool contract).
export type TravelMode = 'car' | 'walking'

export interface Route {
  mode: TravelMode
  distance_m: number | null
  duration_s: number | null
  spoken_directions: string
  /** GeoJSON LineString; null when no route avoids the fire. */
  geometry: { type: 'LineString'; coordinates: [number, number][] } | null
  stub: boolean
}

/** GET /api/fire-area: what routes avoid, everything burned up to the scenario time. */
export interface FireArea {
  type: 'Feature'
  geometry: { type: 'Polygon' | 'MultiPolygon'; coordinates: unknown }
  properties: { until: string }
}

/** What the map shows for a selected resident: their way out, or the crew's way in. */
export type RouteKind = TravelMode | 'rescue'

/** Mirrors CrewAlert in backend/app/models.py. */
export interface CrewAlert {
  rescue_id: string
  neighbor_id: string
  message: string
  link: string
  created_at: string
  /** False: shown on the dashboard only. */
  sent_by_sms: boolean
}
