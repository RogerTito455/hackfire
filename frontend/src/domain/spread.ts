// Where the fire is heading (the predicted cone) and which places it reaches. Pure types and functions.

import { MINUTE } from './hotspots'

type Polygonal = { type: 'Polygon' | 'MultiPolygon'; coordinates: unknown }

/** GET /api/spread: one polygon per hour ahead, outermost first. Empty when there is no clear direction. */
export interface SpreadCollection {
  type: 'FeatureCollection'
  features: { type: 'Feature'; geometry: Polygonal; properties: { hour: number } }[]
  at: string
  motion: { bearing_deg: number; speed_km_h: number } | null
}

export type ZoneKind = 'settlement' | 'care_home' | 'school' | 'health'

export interface ZoneRisk {
  id: string
  name: string
  kind: ZoneKind
  /** 0: already reached. null: the prediction does not reach it. */
  minutes_to_impact: number | null
}

/** GET /api/zones/risk */
export interface ZoneRiskList {
  at: string
  zones: ZoneRisk[]
}

/** GET /api/zones: every zone's outline, keyed by the feature id. */
export interface ZoneShapes {
  type: 'FeatureCollection'
  features: { type: 'Feature'; id: string; geometry: Polygonal; properties: { name: string; kind: ZoneKind } }[]
}

/** The backend computes risk in 15-minute steps; asking at the same step reuses its answer. */
export const RISK_STEP = 15 * MINUTE

export function snapToStep(time: number): number {
  return Math.floor(time / RISK_STEP) * RISK_STEP
}

/** Places the fire has not reached yet but is predicted to, soonest first. */
export function upcomingZones(risk: ZoneRiskList | null): ZoneRisk[] {
  return (risk?.zones ?? [])
    .filter((zone) => zone.minutes_to_impact !== null && zone.minutes_to_impact > 0)
    .sort((a, b) => (a.minutes_to_impact ?? 0) - (b.minutes_to_impact ?? 0))
}

export function reachedCount(risk: ZoneRiskList | null): number {
  return (risk?.zones ?? []).filter((zone) => zone.minutes_to_impact === 0).length
}

const COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']

export function compass(bearingDeg: number): string {
  return COMPASS[Math.round(bearingDeg / 45) % 8]
}
