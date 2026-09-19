// The map, drawn from data/map.json (real hotspots, forecast, zones, roads and cached routes) with a
// virtual camera in kilometres, so scenes can fly between the whole valley and one street.

import map from './data/map.json'
import { C, SANS, clamp01, type Status } from './theme'
import { Icon, STATUS_ICON } from './Icon'

type LonLat = number[]

const LON0 = -4.615
const LAT0 = 40.4
const KX = 111.32 * Math.cos((LAT0 * Math.PI) / 180)
const KY = 110.57

export const toKm = (lon: number, lat: number): [number, number] => [(lon - LON0) * KX, (LAT0 - lat) * KY]

/** Where the camera looks (km from the map origin) and how close (pixels per km). */
export type Camera = { x: number; y: number; z: number }

export const camAt = (lon: number, lat: number, z: number): Camera => {
  const [x, y] = toKm(lon, lat)
  return { x, y, z }
}

export const lerpCam = (a: Camera, b: Camera, k: number): Camera => ({
  x: a.x + (b.x - a.x) * k,
  y: a.y + (b.y - a.y) * k,
  z: a.z * Math.pow(b.z / a.z, k),
})

export const VIEWS = {
  valley: camAt(-4.615, 40.402, 46),
  east: camAt(-4.54, 40.392, 78),
  atalaya: camAt(-4.458, 40.386, 210),
  rescue: camAt(-4.452, 40.39, 128),
}

export const DATA = map

// The same age ramp as the dashboard's hotspots (theme.ts HOTSPOT_AGE_COLORS): fresh is yellow.
const AGE: [number, string][] = [
  [0, C.fire[0]],
  [60, C.fire[1]],
  [360, C.fire[2]],
  [1440, C.fire[3]],
]
const ageColor = (minutes: number) => {
  let color = AGE[0][1]
  for (const [from, c] of AGE) if (minutes >= from) color = c
  return color
}

export type MapProps = {
  cam: Camera
  /** Replay minutes after 22 July 00:00 UTC: hotspots up to here are drawn. */
  time: number
  f: number
  width?: number
  height?: number
  /** Shift the picture right, to leave room for a panel on the left. */
  offsetX?: number
  /** Hours of the 15:30 forecast drawn, 0–7, fractional while it grows. */
  forecast?: number
  /** 0–1: La Atalaya shown as a zone at risk. */
  risk?: number
  /** 0–1: the lead time's 3 km ring. */
  ring?: number
  labels?: number
  residents?: Record<string, Status>
  flash?: { id: string; at: number }
  wayOut?: number
  wayIn?: number
  crewBase?: number
  /** 0–1: the stretches of road the fire has reached, closed to residents (a dashed red cordon). */
  closedRoads?: number
  /** 0–1: the road the coordinator closed by hand, with its no-entry sign. */
  closure?: number
}

export function FireMap(p: MapProps) {
  const width = p.width ?? 1920
  const height = p.height ?? 1080
  const { cam } = p
  const P = (lon: number, lat: number): [number, number] => {
    const [x, y] = toKm(lon, lat)
    return [(x - cam.x) * cam.z + width / 2 + (p.offsetX ?? 0), (y - cam.y) * cam.z + height / 2]
  }
  const line = (coords: LonLat[]) => coords.map(([lon, lat], i) => `${i ? 'L' : 'M'}${P(lon, lat).map((n) => n.toFixed(1)).join(' ')}`).join('')
  const ring = (coords: LonLat[]) => `${line(coords)}Z`
  const labels = p.labels ?? 1
  const visible = ([x, y]: [number, number], pad = 40) => x > -pad && x < width + pad && y > -pad && y < height + pad

  // A faint kilometre grid: the map reads as an instrument, not a picture.
  const step = cam.z > 110 ? 1 : 5
  const x0 = cam.x - (width / 2 + (p.offsetX ?? 0)) / cam.z
  const y0 = cam.y - height / 2 / cam.z
  const grid: string[] = []
  for (let k = Math.floor(x0 / step) * step; k < x0 + width / cam.z; k += step) {
    const x = (k - cam.x) * cam.z + width / 2 + (p.offsetX ?? 0)
    grid.push(`M${x.toFixed(1)} 0V${height}`)
  }
  for (let k = Math.floor(y0 / step) * step; k < y0 + height / cam.z; k += step) {
    const y = (k - cam.y) * cam.z + height / 2
    grid.push(`M0 ${y.toFixed(1)}H${width}`)
  }

  const r = Math.max(3.2, Math.min(13, 0.075 * cam.z))
  const hot = map.hotspots.filter((h) => h[2] <= p.time)
  const atalaya = map.zones['la-atalaya']
  const tiemblo = map.zones['el-tiemblo']
  const risk = clamp01(p.risk ?? 0)
  const resident = (id: string) => map.residents.find((n) => n.id === id)

  return (
    <svg width={width} height={height} style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <defs>
        <filter id={`heat-${width}`} x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={Math.max(6, r * 2.2)} />
        </filter>
      </defs>
      <path d={grid.join('')} stroke="rgba(111,140,255,0.07)" strokeWidth={1} />

      {map.roads.map((road, i) => (
        <g key={i}>
          {road.lines.map((l, j) => (
            <path key={j} d={line(l)} fill="none" stroke="#1d2a55" strokeWidth={cam.z > 110 ? 3 : 2} strokeLinecap="round" strokeLinejoin="round" />
          ))}
        </g>
      ))}

      {tiemblo.rings.map((r2, i) => (
        <path key={i} d={ring(r2)} fill="rgba(111,140,255,0.04)" stroke={C.ink3} strokeWidth={1.5} strokeDasharray="6 6" />
      ))}

      {/* The forecast issued at 15:30: the predicted area, hour by hour, fresh red to far yellow. */}
      {p.forecast !== undefined &&
        [...map.forecast.hours].reverse().map((h) => {
          const k = clamp01((p.forecast ?? 0) - h.hour)
          if (k <= 0) return null
          const color = C.spread[h.hour] ?? C.spread[6]
          return h.rings.map((r2, i) => (
            <path key={`${h.hour}-${i}`} d={ring(r2)} fill={color} fillOpacity={(h.hour ? 0.035 : 0.12) * k} stroke={color} strokeOpacity={0.85 * k} strokeWidth={1.6} strokeDasharray={h.hour ? '10 7' : undefined} />
          ))
        })}

      {p.ring !== undefined &&
        map.leadTime.ring.map((r2, i) => (
          <path key={i} d={ring(r2)} fill="rgba(255,224,102,0.05)" fillOpacity={p.ring} stroke={C.fire[0]} strokeOpacity={0.8 * (p.ring ?? 0)} strokeWidth={2} strokeDasharray="4 8" />
        ))}

      {atalaya.rings.map((r2, i) => (
        <path key={i} d={ring(r2)} fill={C.zone} fillOpacity={0.08 + 0.3 * risk} stroke={risk > 0.02 ? C.zone : C.ink2} strokeWidth={2 + 1.5 * risk} />
      ))}

      {/* Heat: a soft glow under the burning front, so the fire reads as fire, not as dots. */}
      <g filter={`url(#heat-${width})`} opacity={0.55}>
        {hot.map(([lon, lat, t], i) => {
          const age = p.time - t
          if (age > 720) return null
          const at = P(lon, lat)
          return visible(at, 80) ? <circle key={i} cx={at[0]} cy={at[1]} r={r * 3.2} fill={ageColor(age)} /> : null
        })}
      </g>
      {hot.map(([lon, lat, t], i) => {
        const at = P(lon, lat)
        if (!visible(at)) return null
        const age = p.time - t
        const fresh = clamp01(1 - age / 40)
        const color = ageColor(age)
        return (
          <g key={i}>
            {fresh > 0 && <circle cx={at[0]} cy={at[1]} r={r * (1.6 + 2.4 * fresh)} fill={color} opacity={0.22 * fresh} />}
            <circle cx={at[0]} cy={at[1]} r={r} fill={color} opacity={0.92} />
          </g>
        )
      })}

      {(p.closedRoads ?? 0) > 0 &&
        map.closedStretches.map((l, i) => (
          <path key={i} d={line(l)} fill="none" stroke={C.status.needs_rescue} strokeWidth={cam.z > 110 ? 6 : 4} strokeLinecap="round" strokeDasharray="7 7" opacity={p.closedRoads} />
        ))}

      {p.wayOut !== undefined && <Route d={line(map.routes.wayOut.line)} k={p.wayOut} f={p.f} />}
      {p.wayIn !== undefined && <Route d={line(map.routes.wayIn.line)} k={p.wayIn} f={p.f} crew />}

      {/* Places: the safe points (blue, the way out) and the crews' base. */}
      {map.places.map((place) => {
        const at = P(place.lon, place.lat)
        if (!visible(at, 200)) return null
        if (place.kind === 'crew') {
          const k = clamp01(p.crewBase ?? 0)
          if (k <= 0) return null
          return (
            <g key={place.id} opacity={k} transform={`translate(${at[0]} ${at[1]})`}>
              <circle r={24} fill={C.routeDeep} stroke={C.route} strokeWidth={2} />
              <g transform="translate(-14 -14)">
                <MapIcon name="fire-truck" size={28} color="#fff" />
              </g>
              <text x={34} y={7} style={{ fontFamily: SANS, fontSize: 21, fontWeight: 600 }} fill={C.ink}>
                El Tiemblo fire station
              </text>
            </g>
          )
        }
        return (
          <g key={place.id} opacity={labels} transform={`translate(${at[0]} ${at[1]})`}>
            <circle r={6} fill={C.night} stroke={C.route} strokeWidth={2.5} />
            <text x={12} y={6} style={{ fontFamily: SANS, fontSize: cam.z > 100 ? 21 : 17, fontWeight: 500 }} fill={C.ink2}>
              {place.name}
            </text>
          </g>
        )
      })}

      {(() => {
        const [lon, lat] = centroid(atalaya.rings[0])
        const at = P(lon, lat)
        return (
          <text x={at[0]} y={at[1] - Math.max(30, 0.9 * cam.z)} textAnchor="middle" opacity={labels} style={{ fontFamily: SANS, fontSize: cam.z > 100 ? 30 : 22, fontWeight: 700 }} fill={risk > 0.5 ? '#e7c8ff' : C.ink}>
            La Atalaya
          </text>
        )
      })()}

      {(p.closure ?? 0) > 0 &&
        (() => {
          const at = P(map.closure.lon, map.closure.lat)
          const k = clamp01(p.closure ?? 0)
          return (
            <g transform={`translate(${at[0]} ${at[1]})`} opacity={k}>
              <circle r={Math.max(10, 0.15 * cam.z)} fill={C.ink} fillOpacity={0.12} stroke={C.ink} strokeWidth={2} />
              <circle r={17} fill="#fff" stroke="#3c4043" strokeWidth={2} />
              <g transform="translate(-11 -11)">
                <MapIcon name="road-closed" size={22} color="#3c4043" />
              </g>
              {width > 1000 && (
                <text x={26} y={7} style={{ fontFamily: SANS, fontSize: 21, fontWeight: 600 }} fill={C.ink}>
                  Closed by the coordinator
                </text>
              )}
            </g>
          )
        })()}

      {p.residents &&
        Object.entries(p.residents).map(([id, status]) => {
          const n = resident(id)
          if (!n) return null
          const at = P(n.lon, n.lat)
          const since = p.flash?.id === id ? p.f - p.flash.at : -1
          return (
            <g key={id} transform={`translate(${at[0]} ${at[1]})`}>
              {since >= 0 && since < 36 && (
                <>
                  <circle r={18 + since * 7} fill="none" stroke={C.status[status]} strokeWidth={4} opacity={1 - since / 36} />
                  <circle r={18 + since * 3.5} fill={C.status[status]} opacity={0.25 * (1 - since / 36)} />
                </>
              )}
              <circle r={19} fill={C.status[status]} stroke={C.night} strokeWidth={3} />
              <g transform="translate(-11 -11)">
                <MapIcon name={STATUS_ICON[status]} size={22} color="#fff" />
              </g>
            </g>
          )
        })}

    </svg>
  )
}

function Route({ d, k, f, crew = false }: { d: string; k: number; f: number; crew?: boolean }) {
  if (k <= 0) return null
  return (
    <g>
      <path d={d} fill="none" stroke={C.route} strokeOpacity={0.25} strokeWidth={16} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={`${k} 1`} />
      <path d={d} fill="none" stroke={crew ? '#9fb3ff' : C.route} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={`${k} 1`} />
      {crew && k >= 1 && <path d={d} fill="none" stroke="#fff" strokeWidth={2.5} strokeLinecap="round" strokeDasharray="10 18" strokeDashoffset={-f * 2.2} />}
    </g>
  )
}

function centroid(coords: LonLat[]): [number, number] {
  const n = coords.length
  return [coords.reduce((s, c) => s + c[0], 0) / n, coords.reduce((s, c) => s + c[1], 0) / n]
}

// The icons inside the map's SVG.
function MapIcon({ name, size, color }: { name: string; size: number; color: string }) {
  return <Icon name={name} size={size} color={color} stroke={2.2} />
}
