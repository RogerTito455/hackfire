// Visual vocabulary for triage states. Change the look here; logic does not import colours.

import type { TriageStatus } from '../domain/triage'

export const STATUS_LABEL: Record<TriageStatus, string> = {
  pending: 'Not called yet',
  evacuating: 'Evacuating',
  no_answer: 'No answer',
  needs_rescue: 'Needs rescue',
}

export const STATUS_COLOR: Record<TriageStatus, string> = {
  pending: '#8a8f98',
  evacuating: '#2e9e5b',
  no_answer: '#e0a100',
  needs_rescue: '#d93025',
}

// Hotspot colour by age at the replay time, in hours: fresh detections bright, old ones dark.
export const HOTSPOT_AGE_COLORS: readonly (readonly [hours: number, color: string])[] = [
  [0, '#ffe066'],
  [1, '#ff8c1a'],
  [6, '#d93025'],
  [24, '#5c1d14'],
]

// Hotspot radius in pixels by fire radiative power in MW.
export const HOTSPOT_RADIUS_BY_FRP: readonly (readonly [frp: number, radius: number])[] = [
  [0, 3],
  [100, 5],
  [500, 8],
  [2000, 12],
]

// The fire is in Spain, so the replay clock shows Spanish local time.
export const REPLAY_TIME_ZONE = 'Europe/Madrid'

const replayTimeFormat = new Intl.DateTimeFormat('en-GB', {
  timeZone: REPLAY_TIME_ZONE,
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZoneName: 'short',
})

export function formatSpanishTime(epochMs: number): string {
  return replayTimeFormat.format(epochMs)
}

// Live fires: colour by hours since the last detection, radius by hours burning.
export const LIVE_RECENCY_COLORS: readonly (readonly [hours: number, color: string])[] = [
  [0, '#ff5a1f'],
  [6, '#d93025'],
  [24, '#7a2a1d'],
]

export const LIVE_RADIUS_BY_HOURS: readonly (readonly [hours: number, radius: number])[] = [
  [0, 4],
  [6, 7],
  [24, 10],
  [72, 14],
]

export const MAP_MODE_LABEL = { replay: 'Replay · 22–24 Jul 2026', live: 'Live · burning now' } as const

export const TRAVEL_MODE_LABEL = { car: 'By car', walking: 'On foot' } as const

export const ROUTE_COLOR = '#1a73e8'
export const FIRE_AREA_COLOR = '#d93025'

export function formatDistance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres / 10) * 10} m` : `${(metres / 1000).toFixed(1)} km`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60))
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}
