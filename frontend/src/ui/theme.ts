// Visual vocabulary for triage states. Change the look here; logic does not import colours.

import type { TriageStatus } from '../domain/triage'
import type { ZoneKind } from '../domain/zones'

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

// Predicted spread by hours after the forecast: red is the fire now, yellow is furthest ahead.
export const SPREAD_HOUR_COLORS: readonly (readonly [hours: number, color: string])[] = [
  [0, '#e8261a'],
  [1, '#f2551a'],
  [2, '#f7811f'],
  [4, '#fbb02a'],
  [6, '#ffe066'],
]

// Zones at risk by minutes to impact: a darker purple is sooner. Purple keeps them apart from the spread.
export const ZONE_URGENCY_COLORS: readonly (readonly [minutes: number, color: string])[] = [
  [0, '#4a0d67'],
  [60, '#7b1fa2'],
  [180, '#ab47bc'],
  [360, '#d1a3dc'],
]

export const ZONE_KIND_LABEL: Record<ZoneKind, string> = {
  estate: 'Housing estate',
  town: 'Town',
  care_home: 'Care home',
  health_centre: 'Health centre',
  school: 'School',
  road: 'Road',
}

/** "45 min", "4 h" or "4 h 30 min", from minutes. (formatDuration below takes seconds.) */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`
}

/** "now" or a duration: how the panel says when the fire arrives. */
export function formatMinutesToImpact(minutes: number): string {
  return minutes <= 0 ? 'now' : formatMinutes(minutes)
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

export const ROUTE_KIND_LABEL = { car: 'By car', walking: 'On foot', rescue: 'Crew route' } as const

export const ROUTE_COLOR = '#1a73e8'
export const FIRE_AREA_COLOR = '#d93025'

export function formatDistance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres / 10) * 10} m` : `${(metres / 1000).toFixed(1)} km`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60))
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}

const clockFormat = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

/** Wall-clock time for things happening now, such as crew alerts. */
export function formatClock(iso: string): string {
  return clockFormat.format(Date.parse(iso))
}
