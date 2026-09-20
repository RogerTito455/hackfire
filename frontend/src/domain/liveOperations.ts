// Live operations for one real fire: the places its Deepfire ELMFIRE run reaches, when, the alert
// drafts and the roads to close to residents. A prediction for the coordinator, never a warning sent
// to anyone. Pure types and functions.

import { dgtClosures, dgtGeometry, parseDgtNear, type DgtNear, type DgtNearResponse } from './liveDgt'
import type { Bounds } from './scenario'
import type { GeoJsonGeometry } from './spread'
import type { SimulatedFire } from './liveSpread'
import type { ZoneKind } from './zones'

/** As served by GET /api/live/operations/{fireId}. */
export interface LiveOperationsResponse {
  fire_id: string
  simulation_id: string
  name: string
  location: string | null
  run_at: string
  model: string
  duration_hours: number | null
  buffer_m: number
  road_closed_within_minutes: number
  places: {
    id: string
    name: string | null
    kind: ZoneKind
    osm: string | null
    geometry: GeoJsonGeometry
    /** First hour of the run whose polygon touches the place; null when it never does. */
    hour: number | null
    minutes_from_run: number | null
    reaches_at: string | null
    /** Minutes left when the backend answered, 0 when due; null when the run never reaches it. */
    minutes: number | null
  }[]
  alerts: { zone_id: string; place: string; minutes: number; text: string; draft: true; sent: false }[]
  roads_to_close: string[]
  places_fetched_at: string
  /** Places from an earlier run of this fire, because OpenStreetMap did not answer for this one. */
  places_stale: boolean
  /** Deepfire did not answer: the last simulation the backend had. */
  spread_stale: boolean
  /** Official DGT forest-fire incidents and closures near the footprint (absent from older backends). */
  dgt?: DgtNearResponse
  computed_at: string
}

export interface LivePlace {
  id: string
  name: string | null
  kind: ZoneKind
  geometry: GeoJsonGeometry
  /** Minutes until the simulated fire reaches it, 0 when due; null when it is only near the footprint. */
  minutes: number | null
  /** When the simulation puts the fire there, epoch ms; null when never. */
  reachesAt: number | null
}

export interface AlertDraft {
  zoneId: string
  place: string
  minutes: number
  /** In the dashboard's language, written by the backend. Never sent. */
  text: string
}

export interface LiveOperations {
  fireId: string
  simulationId: string
  name: string
  /** When Deepfire ran the simulation, epoch ms. */
  runAt: number
  model: string
  durationHours: number | null
  bufferM: number
  roadClosedWithinMinutes: number
  places: LivePlace[]
  alerts: AlertDraft[]
  roadsToClose: string[]
  placesFetchedAt: number
  placesStale: boolean
  spreadStale: boolean
  /** Official DGT data near this fire, kept apart from HackFire's own suggestions. */
  dgt: DgtNear
}

export function parseLiveOperations(response: LiveOperationsResponse): LiveOperations {
  return {
    fireId: response.fire_id,
    simulationId: response.simulation_id,
    name: response.name,
    runAt: Date.parse(response.run_at),
    model: response.model,
    durationHours: response.duration_hours,
    bufferM: response.buffer_m,
    roadClosedWithinMinutes: response.road_closed_within_minutes,
    places: response.places.map((place) => ({
      id: place.id,
      name: place.name,
      kind: place.kind,
      geometry: place.geometry,
      minutes: place.minutes,
      reachesAt: place.reaches_at === null ? null : Date.parse(place.reaches_at),
    })),
    alerts: response.alerts.map((alert) => ({
      zoneId: alert.zone_id,
      place: alert.place,
      minutes: alert.minutes,
      text: alert.text,
    })),
    roadsToClose: response.roads_to_close,
    placesFetchedAt: Date.parse(response.places_fetched_at),
    placesStale: response.places_stale,
    spreadStale: response.spread_stale,
    dgt: parseDgtNear(response.dgt),
  }
}

/** Places other than roads that the simulation reaches, soonest first (the backend's order). */
export function placesReached(operations: LiveOperations): LivePlace[] {
  return operations.places.filter((place) => place.kind !== 'road' && place.minutes !== null)
}

/** Places near the footprint that the simulation does not reach within its hours. */
export function placesNearby(operations: LiveOperations): LivePlace[] {
  return operations.places.filter((place) => place.kind !== 'road' && place.minutes === null)
}

/** Roads closed to residents: the simulation reaches them within the hour. Crews still use them. */
export function roadsToClose(operations: LiveOperations): LivePlace[] {
  const closed = new Set(operations.roadsToClose)
  return operations.places.filter((place) => closed.has(place.id))
}

/** The closed road the coordinator tapped, so the map and the panel agree on which one it is.
 * `official` is a DGT record, `predicted` a road our simulation reaches within the hour. */
export interface ClosureFocus {
  kind: 'official' | 'predicted'
  id: string
  lon: number
  lat: number
}

function walk(coordinates: unknown, visit: (lon: number, lat: number) => void): void {
  if (!Array.isArray(coordinates)) return
  if (typeof coordinates[0] === 'number') {
    visit(coordinates[0] as number, coordinates[1] as number)
    return
  }
  for (const item of coordinates) walk(item, visit)
}

/** The middle of a geometry's box: where the map flies when a closure is tapped. Null when empty. */
export function geometryCenter(geometry: GeoJsonGeometry): [number, number] | null {
  let west = Infinity
  let south = Infinity
  let east = -Infinity
  let north = -Infinity
  walk(geometry.coordinates, (lon, lat) => {
    west = Math.min(west, lon)
    south = Math.min(south, lat)
    east = Math.max(east, lon)
    north = Math.max(north, lat)
  })
  return west === Infinity ? null : [(west + east) / 2, (south + north) / 2]
}

/** The box around the run's footprint, every place listed and every official closure drawn beside
 * them, for the map to fit; null when empty. A closure the map draws outside the box would never be
 * seen, so it belongs in it. */
export function operationsBounds(operations: LiveOperations, run?: SimulatedFire): Bounds | null {
  let west = Infinity
  let south = Infinity
  let east = -Infinity
  let north = -Infinity
  const visit = (lon: number, lat: number) => {
    west = Math.min(west, lon)
    south = Math.min(south, lat)
    east = Math.max(east, lon)
    north = Math.max(north, lat)
  }
  const geometries = [
    ...operations.places.map((place) => place.geometry),
    ...(run?.hours ?? []).map((hour) => hour.geometry),
    ...dgtClosures(operations.dgt.records).map(dgtGeometry),
  ]
  for (const geometry of geometries) walk(geometry.coordinates, visit)
  return west === Infinity
    ? null
    : [
        [west, south],
        [east, north],
      ]
}
