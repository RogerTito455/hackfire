// Fires burning right now, as Deepfire's active clusters. Pure types and functions.

export interface LiveFire {
  id: string
  lon: number
  lat: number
  /** Epoch milliseconds. */
  firstObserved: number
  lastObserved: number
}

/** As served by GET /api/live/fires. */
export interface LiveFireCollection {
  type: 'FeatureCollection'
  features: {
    geometry: { type: 'Point'; coordinates: [number, number] }
    properties: { id: string; first_observed: string; last_observed: string }
  }[]
  fetched_at: string
  /** True when Deepfire failed and this is the last good answer. */
  stale: boolean
}

export interface LiveFires {
  fires: LiveFire[]
  fetchedAt: number
  stale: boolean
}

export function parseLiveFires(collection: LiveFireCollection): LiveFires {
  return {
    fires: collection.features.map((feature) => ({
      id: feature.properties.id,
      lon: feature.geometry.coordinates[0],
      lat: feature.geometry.coordinates[1],
      firstObserved: Date.parse(feature.properties.first_observed),
      lastObserved: Date.parse(feature.properties.last_observed),
    })),
    fetchedAt: Date.parse(collection.fetched_at),
    stale: collection.stale,
  }
}

/** Hours between the first and the last detection: a rough size of the fire. */
export function burningHours(fire: LiveFire): number {
  return (fire.lastObserved - fire.firstObserved) / 3_600_000
}
