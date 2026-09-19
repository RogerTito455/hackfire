// Roads the coordinator marked as cut (backend app/closures.py). Every route after one goes around it.

export interface RoadClosure {
  id: string
  lat: number
  lon: number
  radius_m: number
  note: string | null
  created_at: string
  /** Residents already leaving by a route through here when it was closed: call them again. */
  affected: string[]
}

/** Changes whenever the set of closures changes, so routes asked before are asked again. */
export const closuresKey = (closures: RoadClosure[]): string => closures.map((closure) => closure.id).join(',')

/** The closed stretch as a GeoJSON polygon: a circle of the closure's radius, on the ground. */
export function closureArea(closure: RoadClosure, steps = 32): { type: 'Polygon'; coordinates: number[][][] } {
  const metresPerDegreeLat = 110_570
  const metresPerDegreeLon = 111_320 * Math.cos((closure.lat * Math.PI) / 180)
  const ring = Array.from({ length: steps + 1 }, (_, i) => {
    const angle = (2 * Math.PI * i) / steps
    return [
      closure.lon + (closure.radius_m * Math.cos(angle)) / metresPerDegreeLon,
      closure.lat + (closure.radius_m * Math.sin(angle)) / metresPerDegreeLat,
    ]
  })
  return { type: 'Polygon', coordinates: [ring] }
}
