// Visual vocabulary: colours, icons and number formats. Change the look here; logic does not
// import colours. Words live in src/locales/*.json (see locales.ts and DESIGN.md).

import type { TriageStatus } from '../domain/triage'

export const STATUS_COLOR: Record<TriageStatus, string> = {
  pending: '#64708f',
  evacuating: '#0e9f6e',
  no_answer: '#e9a100',
  needs_rescue: '#e0302a',
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

const timeFormats = new Map<string, Intl.DateTimeFormat>()

/** Spanish local time (the fire's), written the way `intl` writes dates: "23 Jul, 18:00 CEST". */
export function formatSpanishTime(epochMs: number, intl = 'en-GB'): string {
  let format = timeFormats.get(intl)
  if (!format) {
    format = new Intl.DateTimeFormat(intl, {
      timeZone: REPLAY_TIME_ZONE,
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    })
    timeFormats.set(intl, format)
  }
  return format.format(epochMs)
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

/** "45 min", "4 h" or "4 h 30 min", from minutes. (formatDuration below takes seconds.) */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`
}

/** `now` (the locale's word for it) or a duration: how the panel says when the fire arrives. */
export function formatMinutesToImpact(minutes: number, now: string): string {
  return minutes <= 0 ? now : formatMinutes(minutes)
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

export const MAP_MODE_ICON = { replay: 'replay', live: 'live' } as const

export const ROUTE_KIND_ICON = { car: 'car', walking: 'walk', rescue: 'fire-truck' } as const

// The way out is civil-protection blue (DESIGN.md); the fire keeps the warm colours.
export const ROUTE_COLOR = '#2447d6'
export const FIRE_AREA_COLOR = '#e5301f'

export function formatDistance(metres: number, intl = 'en-GB'): string {
  if (metres < 1000) return `${Math.round(metres / 10) * 10} m`
  return `${new Intl.NumberFormat(intl, { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(metres / 1000)} km`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60))
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}

/** Wall-clock time for things happening now, such as crew alerts. */
export function formatClock(iso: string, intl = 'en-GB'): string {
  return new Intl.DateTimeFormat(intl, { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(Date.parse(iso))
}

// Icon for each triage status, next to its label and inside its map marker (see ui/icons/README.md).
export const STATUS_ICON: Record<TriageStatus, import('./Icon').IconName> = {
  pending: 'hourglass',
  evacuating: 'exit',
  no_answer: 'phone-missed',
  needs_rescue: 'lifebuoy',
}

// Map markers (ui/markers.ts): the white outline that keeps them readable on any basemap,
// and the dark grey ink of the white place markers (safe point, crew base).
export const MARKER_OUTLINE_COLOR = '#fff'
export const PLACE_MARKER_INK = '#3c4043'

export const ORDER_STATE_COLOR = { proposed: '#e0a100', approved: '#2e9e5b' } as const
