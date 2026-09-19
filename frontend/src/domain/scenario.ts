// The active scenario: which fire the dashboard replays, and where (backend/app/scenario.py).
// Pure types and functions: no React, no fetch, no styling.

/** As served by GET /api/scenario. */
export interface Scenario {
  id: string
  name: string
  /** min lon, min lat, max lon, max lat. */
  bbox: [number, number, number, number]
  /** IANA time zone the replay is told in. */
  time_zone: string
  replay_start: string
  replay_end: string
  /** The moment the calls happen at, and routes are planned for. */
  scenario_time: string
  lead_time_zone: string
}

/** South-west and north-east corners, as MapLibre takes them. */
export type Bounds = [[number, number], [number, number]]

export function scenarioBounds(scenario: Scenario): Bounds {
  const [west, south, east, north] = scenario.bbox
  return [
    [west, south],
    [east, north],
  ]
}
