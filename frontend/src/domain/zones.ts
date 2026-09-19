// Places the fire can reach, and when. Pure types and functions: no React, no fetch, no styling.

import type { GeoJsonGeometry } from './spread'

export type ZoneKind = 'estate' | 'town' | 'care_home' | 'health_centre' | 'school' | 'road'

export interface Zone {
  id: string
  /** OpenStreetMap has no name for a few facilities. */
  name: string | null
  kind: ZoneKind
  geometry: GeoJsonGeometry
}

/** GeoJSON as served by GET /api/zones. */
export interface ZoneCollection {
  type: 'FeatureCollection'
  features: {
    id: string
    geometry: GeoJsonGeometry
    properties: { id: string; name: string | null; kind: ZoneKind; osm: string | null }
  }[]
}

/**
 * GET /api/impact: at every `step_minutes` from `start`, the forecast in force and each zone's
 * minutes to impact. The backend computes them, so the panel, the map and the voice agent's
 * `get_fire_status` always agree. Only zones that are ever at risk are listed.
 */
export interface ImpactTable {
  start: string
  step_minutes: number
  forecast: (string | null)[]
  zones: Record<string, (number | null)[]>
}

/**
 * A road the predicted fire reaches within this many minutes is closed to residents: their routes
 * avoid the fire plus its next hour of spread (backend AVOID_AHEAD_H), while crews' routes avoid
 * only what has burned, so crews still use it.
 */
export const ROAD_CLOSED_WITHIN_MIN = 60

/** The roads closed to residents at this moment of the forecast. */
export function closedRoads(zones: readonly ZoneImpact[]): ZoneImpact[] {
  return zones.filter(({ zone, minutes }) => zone.kind === 'road' && minutes <= ROAD_CLOSED_WITHIN_MIN)
}

export interface ZoneImpact {
  zone: Zone
  /** Minutes until the predicted fire reaches the zone; 0 when it is there already. */
  minutes: number
}

// Who is hurt most comes first among zones the fire reaches at the same time.
const KIND_PRIORITY: readonly ZoneKind[] = ['estate', 'town', 'care_home', 'health_centre', 'school', 'road']

export function parseZones(collection: ZoneCollection): Zone[] {
  return collection.features.map((feature) => ({
    id: feature.id,
    name: feature.properties.name,
    kind: feature.properties.kind,
    geometry: feature.geometry,
  }))
}

/** Which step of the impact table `time` falls in, or null when the table does not cover it. */
export function impactStep(table: ImpactTable | null, time: number | null): number | null {
  if (table === null || time === null) return null
  const step = Math.floor((time - Date.parse(table.start)) / (table.step_minutes * 60_000))
  return step >= 0 && step < table.forecast.length ? step : null
}

/** When the forecast in force at `step` was issued (epoch ms), or null if there is none. */
export function forecastIssuedAt(table: ImpactTable | null, step: number | null): number | null {
  const issued = table === null || step === null ? null : table.forecast[step]
  return issued === null ? null : Date.parse(issued)
}

/** Zones the predicted fire reaches at `step`, soonest first. */
export function zonesAtRisk(table: ImpactTable | null, zones: readonly Zone[], step: number | null): ZoneImpact[] {
  if (table === null || step === null) return []
  const impacts: ZoneImpact[] = []
  for (const zone of zones) {
    const minutes = table.zones[zone.id]?.[step]
    if (minutes !== null && minutes !== undefined) impacts.push({ zone, minutes })
  }
  return impacts.sort(
    (a, b) =>
      a.minutes - b.minutes ||
      KIND_PRIORITY.indexOf(a.zone.kind) - KIND_PRIORITY.indexOf(b.zone.kind) ||
      a.zone.id.localeCompare(b.zone.id),
  )
}
