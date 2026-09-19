// Predicted spread for the fires burning now: the ELMFIRE runs Deepfire makes on its own on active
// fires (terrain, fuel and weather). Pure types and functions.

import type { GeoJsonGeometry, SpreadPolygon } from './spread'

/** As served by GET /api/live/spread: the latest completed run per active fire. */
export interface LiveSpreadResponse {
  fires: {
    /** The active cluster's id, as in GET /api/live/fires. */
    fire_id: string
    simulation_id: string
    name: string
    location: string | null
    created_at: string
    /** `elmfire` or `forefire`. */
    model: string
    duration_hours: number | null
    ensemble_members: number
    burned_area_m2: number | null
    /** One cumulative polygon per hour after the run, largest first. */
    hours: { hour: number; geometry: GeoJsonGeometry; burn_probability?: number }[]
  }[]
  fetched_at: string
  /** True when Deepfire failed and this is the last good answer. */
  stale: boolean
}

export interface SimulatedFire {
  fireId: string
  name: string
  /** When Deepfire ran the simulation, epoch ms. */
  runAt: number
  model: string
  durationHours: number | null
  /** Largest first, so the smaller ones draw on top. */
  hours: SpreadPolygon[]
}

export interface LiveSpread {
  fires: SimulatedFire[]
  fetchedAt: number
  stale: boolean
}

export function parseLiveSpread(response: LiveSpreadResponse): LiveSpread {
  return {
    fires: response.fires.map((fire) => ({
      fireId: fire.fire_id,
      name: fire.name,
      runAt: Date.parse(fire.created_at),
      model: fire.model,
      durationHours: fire.duration_hours,
      hours: fire.hours.map(({ hour, geometry }) => ({ hour, geometry })).sort((a, b) => b.hour - a.hour),
    })),
    fetchedAt: Date.parse(response.fetched_at),
    stale: response.stale,
  }
}

/** The run shown for an active fire, if Deepfire simulated it. */
export function simulationFor(spread: LiveSpread | null, fireId: string): SimulatedFire | undefined {
  return spread?.fires.find((fire) => fire.fireId === fireId)
}

/** Every fire's hourly polygons, each fire's largest first. */
export function liveSpreadPolygons(spread: LiveSpread | null): (SpreadPolygon & { fireId: string })[] {
  return (spread?.fires ?? []).flatMap((fire) => fire.hours.map((polygon) => ({ ...polygon, fireId: fire.fireId })))
}

/** The models behind the runs shown, each once. */
export function spreadModels(spread: LiveSpread | null): string[] {
  return [...new Set((spread?.fires ?? []).map((fire) => fire.model))]
}
