// Satellite hotspots for the replay. Pure types and functions: no React, no fetch, no styling.

export interface Hotspot {
  id: string
  lon: number
  lat: number
  /** Epoch milliseconds. */
  observedAt: number
  /** Fire radiative power in MW; null when the satellite does not report it. */
  frp: number | null
  confidence: string | null
  source: string | null
}

/** GeoJSON as served by GET /api/hotspots. */
export interface HotspotCollection {
  type: 'FeatureCollection'
  features: {
    id: string
    geometry: { type: 'Point'; coordinates: [number, number] }
    properties: {
      observed_at: string
      fire_radiative_power: number | null
      confidence: string | null
      source: string | null
    }
  }[]
}

export interface TimeRange {
  start: number
  end: number
}

export const MINUTE = 60_000
export const HOUR = 60 * MINUTE

/** Flatten the GeoJSON into hotspots sorted by observation time. */
export function parseHotspots(collection: HotspotCollection): Hotspot[] {
  return collection.features
    .map((feature) => ({
      id: feature.id,
      lon: feature.geometry.coordinates[0],
      lat: feature.geometry.coordinates[1],
      observedAt: Date.parse(feature.properties.observed_at),
      frp: feature.properties.fire_radiative_power,
      confidence: feature.properties.confidence,
      source: feature.properties.source,
    }))
    .sort((a, b) => a.observedAt - b.observedAt)
}

/** First and last observation, or null when there are no hotspots. */
export function timeRange(hotspots: readonly Hotspot[]): TimeRange | null {
  if (hotspots.length === 0) return null
  return { start: hotspots[0].observedAt, end: hotspots[hotspots.length - 1].observedAt }
}

/** How many hotspots had been observed at `time`. `hotspots` must be sorted by observedAt. */
export function countObservedBy(hotspots: readonly Hotspot[], time: number): number {
  let low = 0
  let high = hotspots.length
  while (low < high) {
    const mid = (low + high) >>> 1
    if (hotspots[mid].observedAt <= time) low = mid + 1
    else high = mid
  }
  return low
}

/** Clamp a time into the range. */
export function clampTime(range: TimeRange, time: number): number {
  return Math.min(range.end, Math.max(range.start, time))
}
