// Builds the landing page's mini-demo data (src/ui/landing/miniDemo.json) from the committed files
// in data/: a sample of the real satellite hotspots of 23 July 2026 (first sighting per grid cell),
// the predicted spread issued when La Atalaya was first flagged, the zones, the safe point and two
// cached routes. Coordinates are projected to the SVG's own units so the component does no maths.
// No network, deterministic. Run: pnpm --dir frontend data:mini-demo

import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const data = (name) => JSON.parse(readFileSync(join(root, 'data', name), 'utf8'))
const OUT = join(root, 'frontend', 'src', 'ui', 'landing', 'miniDemo.json')

// The frame: from the fire's western flank to San Martín de Valdeiglesias.
const BOX = { west: -4.72, east: -4.37, south: 40.315, north: 40.465 }
const WIDTH = 1000
const KX = Math.cos(((BOX.north + BOX.south) / 2) * (Math.PI / 180))
const HEIGHT = Math.round((WIDTH * (BOX.north - BOX.south)) / ((BOX.east - BOX.west) * KX))
const round = (n) => Math.round(n * 10) / 10
const project = ([lon, lat]) => [
  round(((lon - BOX.west) / (BOX.east - BOX.west)) * WIDTH),
  round(((BOX.north - lat) / (BOX.north - BOX.south)) * HEIGHT),
]
const inBox = ([lon, lat]) => lon >= BOX.west && lon <= BOX.east && lat >= BOX.south && lat <= BOX.north
const path = (coords) => coords.map((c) => project(c).join(',')).join(' ')

// Every nth vertex, keeping the last, so outlines and routes stay light.
const thin = (coords, step) => coords.filter((_, i) => i % step === 0 || i === coords.length - 1)

// Minutes are counted from 00:00 CEST on 23 July (22:00 UTC the day before).
const START = Date.parse('2026-07-22T22:00:00Z')
const END = Date.parse('2026-07-23T22:00:00Z')
const minutesOf = (iso) => Math.round((Date.parse(iso) - START) / 60000)

// Hotspots: the first sighting in each ~450 m cell, up to the end of 23 July. Earlier ones (from
// 22 July) start at a negative minute and are already old when the animation begins.
const CELL = 0.005
const cells = new Map()
for (const feature of data('hotspots_2026-07-22_24.geojson').features) {
  const coords = feature.geometry.coordinates
  const at = Date.parse(feature.properties.observed_at)
  if (at >= END || !inBox(coords)) continue
  const key = `${Math.floor(coords[0] / CELL)}:${Math.floor(coords[1] / CELL)}`
  const seen = cells.get(key)
  if (!seen || at < seen.at) cells.set(key, { at, coords, iso: feature.properties.observed_at })
}
const hotspots = [...cells.values()]
  .sort((a, b) => a.at - b.at)
  .map(({ coords, iso }) => [...project(coords), Math.max(-120, minutesOf(iso))])

// The predicted spread issued at the flag time, one polygon per hour ahead.
const FLAGGED = data('lead_time_la-atalaya.json').flagged_at
const cone = data('spread_2026-07-23.geojson')
  .features.filter((f) => f.properties.issued_at === FLAGGED && f.properties.hour > 0)
  .map((f) => ({ hour: f.properties.hour, points: path(thin(f.geometry.coordinates[0], 2)) }))

// Point in polygon (ray casting), to find the first hour of the cone that reaches a zone.
const inside = ([x, y], ring) => {
  let hit = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit
  }
  return hit
}
const conePolygons = data('spread_2026-07-23.geojson')
  .features.filter((f) => f.properties.issued_at === FLAGGED)
  .sort((a, b) => a.properties.hour - b.properties.hour)

const outlineOf = (geometry) =>
  geometry.type === 'MultiPolygon'
    ? geometry.coordinates.reduce((a, b) => (b[0].length > a.length ? b[0] : a), [])
    : geometry.coordinates[0]
const zones = data('zones.geojson')
  .features.filter((f) => ['la-atalaya', 'el-tiemblo'].includes(f.properties.id))
  .map((f) => {
    const ring = outlineOf(f.geometry)
    const centre = ring.reduce((s, c) => [s[0] + c[0] / ring.length, s[1] + c[1] / ring.length], [0, 0])
    const reached = conePolygons.find((p) => ring.some((c) => inside(c, p.geometry.coordinates[0])))
    return {
      id: f.properties.id,
      name: f.properties.name,
      centre: project(centre),
      outline: path(thin(ring, 3)),
      // Hours after the flag at which the cone first reaches the zone; null when it does not.
      impactHours: reached ? reached.properties.hour : null,
    }
  })

const places = data('places.json')
const safe = places.safe_points.find((p) => p.id === 'san-martin')
const base = places.crew_base
const routes = data('routes_cache.json')
const routeFrom = (prefix) => {
  const key = Object.keys(routes).find((k) => k.startsWith(prefix))
  if (!key) throw new Error(`No cached route starts with ${prefix}`)
  return path(thin(routes[key].geometry.coordinates, 3))
}

// Example residents: the sample registry's positions (data/neighbors.sample.json), never the real one.
const residents = data('neighbors.sample.json').map((n) => project([n.lon, n.lat]))

const out = {
  about:
    'Generated by frontend/scripts/mini-demo-data.mjs from data/. SVG units; minutes since 00:00 CEST on 23 July 2026.',
  width: WIDTH,
  height: HEIGHT,
  flaggedMinute: minutesOf(FLAGGED),
  hotspots,
  cone,
  zones,
  safePoint: { name: safe.name, at: project([safe.lon, safe.lat]) },
  crewBase: project([base.lon, base.lat]),
  evacuationRoute: routeFrom('car:-4.45880,40.38290->-4.39865,40.36250'),
  crewRoute: routeFrom('car:-4.49762,40.41543->-4.46030,40.38170'),
  residents,
}
writeFileSync(OUT, JSON.stringify(out) + '\n')
console.log(`${OUT}: ${hotspots.length} hotspots, ${(JSON.stringify(out).length / 1024).toFixed(1)} KB`)
