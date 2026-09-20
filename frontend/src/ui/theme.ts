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
  [0, 4],
  [100, 6],
  [500, 9],
  [2000, 13],
]

// The base map is muted so that only our colours carry meaning: grey land, the fire in warm
// colours, the way out in blue. At night the tiles are inverted to a dark grey.
export const BASEMAP_PAINT = {
  light: { 'raster-saturation': -0.8, 'raster-contrast': -0.1, 'raster-brightness-min': 0.1, 'raster-brightness-max': 1 },
  dark: { 'raster-saturation': -1, 'raster-contrast': 0, 'raster-brightness-min': 0.78, 'raster-brightness-max': 0.1 },
} as const

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

/** How long ago, in units that read the same in both languages: "40 min", "6 h", "12 d". */
export function formatAgo(milliseconds: number): string {
  const minutes = Math.max(0, Math.round(milliseconds / 60_000))
  if (minutes < 60) return `${minutes} min`
  const hours = Math.round(minutes / 60)
  return hours < 48 ? `${hours} h` : `${Math.round(hours / 24)} d`
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

// Deepfire's spread models by their own names (proper nouns, not translated).
const SPREAD_MODEL_LABEL: Record<string, string> = { elmfire: 'ELMFIRE', forefire: 'ForeFire' }

export function spreadModelLabel(model: string): string {
  return SPREAD_MODEL_LABEL[model] ?? model.toUpperCase()
}

export const ROUTE_KIND_ICON = { car: 'car', walking: 'walk', rescue: 'fire-truck' } as const

// The way out is civil-protection blue (DESIGN.md); the fire keeps the warm colours.
export const ROUTE_COLOR = '#2447d6'
/** Roads closed to residents: fire red, dashed, like a cordon. */
export const ROAD_CLOSED_COLOR = '#e0302a'
export const FIRE_AREA_COLOR = '#e5301f'

export function formatDistance(metres: number, intl = 'en-GB'): string {
  if (metres < 1000) return `${Math.round(metres / 10) * 10} m`
  return `${new Intl.NumberFormat(intl, { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(metres / 1000)} km`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60))
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}

/** Hour and minute in Spain's time zone with its abbreviation ("15:30 CEST"), like the replay's times. */
export function formatSpanishClock(epochMs: number, intl = 'en-GB'): string {
  return new Intl.DateTimeFormat(intl, {
    timeZone: REPLAY_TIME_ZONE,
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(epochMs)
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
/** A closed road: the neutral ink of signage, so it reads as neither fire nor a way out. */
export const CLOSURE_COLOR = '#3c4043'
/** The DGT's official forest-fire incidents in live mode: a warning triangle in navy ink with a fire
 * dot, so they never read as one of Deepfire's round fire markers. */
export const DGT_MARKER = { ink: '#0f1b3d', fill: '#ffffff', fire: '#ff7a1a' } as const
/** A road the DGT itself has shut: the navy of its warning triangle, so official data never reads as
 * our red prediction cordon. Drawn dashed over a white casing, the same cordon idiom. */
export const DGT_CLOSURE_COLOR = DGT_MARKER.ink

export const ORDER_STATE_COLOR = { proposed: '#e0a100', approved: '#2e9e5b' } as const

// Service status (ServiceStatus.tsx): the status colours, so a dot reads like a resident's state.
// Configured-but-not-checked shares the green of "up" and is drawn hollow.
export const PROVIDER_STATE_COLOR: Record<import('../domain/operations').ProviderState, string> = {
  up: '#0e9f6e',
  configured: '#0e9f6e',
  degraded: '#e9a100',
  down: '#e0302a',
  not_configured: '#64708f',
}

// Activity log (ActivityLog.tsx): an icon per kind of event; a status report takes its status's icon.
export const AUDIT_ICON: Record<string, import('./Icon').IconName> = {
  order: 'flag',
  call: 'phone',
  campaign: 'phone',
  alert: 'bell',
  closure: 'road-closed',
  video: 'live',
  autopilot: 'replay',
  demo: 'reset',
}

