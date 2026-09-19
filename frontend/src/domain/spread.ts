// Predicted spread for the replay. Pure types and functions: no React, no fetch, no styling.

/** A GeoJSON geometry, kept opaque: the domain only passes it on to the map. */
export interface GeoJsonGeometry {
  type: string
  coordinates: unknown
}

/** GeoJSON as served by GET /api/spread: one feature per forecast issued and hour ahead. */
export interface SpreadCollection {
  type: 'FeatureCollection'
  features: {
    geometry: GeoJsonGeometry
    properties: {
      issued_at: string
      /** Hours after `issued_at`; 0 is the fire as seen when the forecast was issued. */
      hour: number
      heading_deg: number | null
      speed_kmh: number
    }
  }[]
}

export interface SpreadPolygon {
  hour: number
  geometry: GeoJsonGeometry
}

/** The polygons of the forecast issued at `issuedAt`, largest first so the smaller ones draw on top. */
export function spreadPolygons(collection: SpreadCollection, issuedAt: number | null): SpreadPolygon[] {
  if (issuedAt === null) return []
  return collection.features
    .filter((feature) => Date.parse(feature.properties.issued_at) === issuedAt)
    .map((feature) => ({ hour: feature.properties.hour, geometry: feature.geometry }))
    .sort((a, b) => b.hour - a.hour)
}
