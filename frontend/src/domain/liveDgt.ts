// Official road data from the DGT (Spain's traffic authority), as the backend reads it from the DGT's
// National Access Point (DATEX II): forest-fire incidents and road or carriageway closures. Official
// data, shown next to HackFire's own suggestions and never mixed with them. Pure types and functions.

import type { GeoJsonGeometry } from './spread'

/** One DATEX II situation record, as served by the backend. */
export interface DgtRecordResponse {
  id: string
  road: string | null
  cause: string | null
  cause_detail: string | null
  management: string | null
  forest_fire: boolean
  closure: boolean
  since: string | null
  from: { lat: number; lon: number; km: number | null; municipality: string | null; province: string | null }
  to: { lat: number; lon: number } | null
  comments: string[]
}

/** GET /api/live/dgt. */
export interface DgtOverviewResponse {
  source: string
  published_at: string | null
  fetched_at: string
  stale: boolean
  forest_fires: DgtRecordResponse[]
  closures: DgtRecordResponse[]
}

/** The `dgt` block of GET /api/live/operations/{fireId}: the records near that fire. */
export interface DgtNearResponse {
  available: boolean
  stale: boolean
  fetched_at?: string
  near_m?: number
  records: DgtRecordResponse[]
}

/** What kind of record, for its label: a forest fire, or how the road is managed. */
export type DgtKind = 'forestFire' | 'roadClosed' | 'carriagewayClosures' | 'laneClosures' | 'other'

/** Why a closure is in force, for its label; anything the dashboard does not name is `other`. */
export type DgtCause = 'roadMaintenance' | 'accident' | 'vehicleObstruction' | 'obstruction' | 'environmentalObstruction' | 'infrastructureDamageObstruction' | 'poorEnvironment' | 'publicEvent' | 'other'

const KNOWN_MANAGEMENT: readonly DgtKind[] = ['roadClosed', 'carriagewayClosures', 'laneClosures']
const KNOWN_CAUSES: readonly DgtCause[] = [
  'roadMaintenance',
  'accident',
  'vehicleObstruction',
  'obstruction',
  'environmentalObstruction',
  'infrastructureDamageObstruction',
  'poorEnvironment',
  'publicEvent',
]

export interface DgtRecord {
  id: string
  road: string | null
  kind: DgtKind
  /** The DGT shuts the road or a whole carriageway here, so the map draws it as an official cordon. */
  closure: boolean
  /** How the road is managed, when a forest fire's record also closes it. */
  management: DgtKind
  cause: DgtCause
  /** Since when, epoch ms; null when the DGT gives no start. */
  since: number | null
  lon: number
  lat: number
  km: number | null
  municipality: string | null
  province: string | null
  /** The far end of the stretch the record covers; null when the DGT gives only a point. */
  to: { lon: number; lat: number } | null
}

function management(value: string | null): DgtKind {
  return KNOWN_MANAGEMENT.find((known) => known === value) ?? 'other'
}

export function parseDgtRecord(record: DgtRecordResponse): DgtRecord {
  const since = record.since === null ? NaN : Date.parse(record.since)
  return {
    id: record.id,
    road: record.road,
    closure: record.closure,
    kind: record.forest_fire ? 'forestFire' : management(record.management),
    management: management(record.management),
    cause: KNOWN_CAUSES.find((known) => known === record.cause) ?? 'other',
    since: Number.isNaN(since) ? null : since,
    lon: record.from.lon,
    lat: record.from.lat,
    km: record.from.km,
    municipality: record.from.municipality,
    province: record.from.province,
    to: record.to === null ? null : { lon: record.to.lon, lat: record.to.lat },
  }
}

/** The records that shut a road or a carriageway: what the map draws as an official cordon. Pure. */
export function dgtClosures(records: readonly DgtRecord[]): DgtRecord[] {
  return records.filter((record) => record.closure)
}

/** Where a record is: the stretch the DGT gives, or its single point. Pure. */
export function dgtGeometry(record: DgtRecord): GeoJsonGeometry {
  if (record.to === null || (record.to.lon === record.lon && record.to.lat === record.lat)) {
    return { type: 'Point', coordinates: [record.lon, record.lat] }
  }
  return {
    type: 'LineString',
    coordinates: [
      [record.lon, record.lat],
      [record.to.lon, record.to.lat],
    ],
  }
}

export interface DgtOverview {
  forestFires: DgtRecord[]
  closures: DgtRecord[]
  fetchedAt: number
  stale: boolean
}

export function parseDgtOverview(response: DgtOverviewResponse): DgtOverview {
  return {
    forestFires: response.forest_fires.map(parseDgtRecord),
    closures: response.closures.map(parseDgtRecord),
    fetchedAt: Date.parse(response.fetched_at),
    stale: response.stale,
  }
}

export interface DgtNear {
  /** False when the DGT feed did not answer and nothing was cached. */
  available: boolean
  stale: boolean
  fetchedAt: number | null
  nearM: number | null
  records: DgtRecord[]
}

export function parseDgtNear(response: DgtNearResponse | undefined): DgtNear {
  if (!response) return { available: false, stale: false, fetchedAt: null, nearM: null, records: [] }
  const fetchedAt = response.fetched_at === undefined ? NaN : Date.parse(response.fetched_at)
  return {
    available: response.available,
    stale: response.stale,
    fetchedAt: Number.isNaN(fetchedAt) ? null : fetchedAt,
    nearM: response.near_m ?? null,
    records: response.records.map(parseDgtRecord),
  }
}
