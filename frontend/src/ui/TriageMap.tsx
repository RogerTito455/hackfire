import { useEffect, useRef, useState } from 'react'
import {
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  Popup,
  setWorkerUrl,
  type ExpressionSpecification,
  type GeoJSONSource,
  type StyleSpecification,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { MINUTE, type Hotspot } from '../domain/hotspots'
import type { Neighbor } from '../domain/triage'
import { HOTSPOT_AGE_COLORS, HOTSPOT_RADIUS_BY_FRP, STATUS_COLOR, STATUS_LABEL } from './theme'

// MapLibre v6 inside a bundler cannot find its worker on its own.
setWorkerUrl(workerUrl)

// Demo box around Burgohondo, El Tiemblo and La Atalaya (see PLAN.md section 4).
const DEMO_BOUNDS: [[number, number], [number, number]] = [
  [-4.85, 40.3],
  [-4.4, 40.5],
]

const OSM_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}

const HOTSPOTS = 'hotspots'

type GeoJSONData = Parameters<GeoJSONSource['setData']>[0]

// Feature times are minutes since the first hotspot: small numbers keep map expressions exact.
function toFeatureCollection(hotspots: readonly Hotspot[], origin: number): GeoJSONData {
  return {
    type: 'FeatureCollection',
    features: hotspots.map((hotspot) => ({
      type: 'Feature',
      id: hotspot.id,
      geometry: { type: 'Point', coordinates: [hotspot.lon, hotspot.lat] },
      properties: { t: (hotspot.observedAt - origin) / MINUTE, frp: hotspot.frp ?? 0 },
    })),
  }
}

function ageColor(nowMinutes: number): ExpressionSpecification {
  const stops = HOTSPOT_AGE_COLORS.flatMap(([hours, color]) => [hours * 60, color])
  return ['interpolate', ['linear'], ['-', nowMinutes, ['get', 't']], ...stops] as ExpressionSpecification
}

const radiusByFrp = [
  'interpolate',
  ['linear'],
  ['get', 'frp'],
  ...HOTSPOT_RADIUS_BY_FRP.flat(),
] as ExpressionSpecification

interface TriageMapProps {
  neighbors: Neighbor[]
  hotspots: Hotspot[]
  /** Replay time in epoch milliseconds: hotspots observed after it are hidden. */
  time: number | null
}

export function TriageMap({ neighbors, hotspots, time }: TriageMapProps) {
  const container = useRef<HTMLDivElement | null>(null)
  const map = useRef<MapLibreMap | null>(null)
  const markers = useRef<Map<string, Marker>>(new Map())
  const [styleReady, setStyleReady] = useState(false)

  useEffect(() => {
    if (!container.current || map.current) return
    const instance = new MapLibreMap({
      container: container.current,
      style: OSM_STYLE,
      bounds: DEMO_BOUNDS,
      fitBoundsOptions: { padding: 24 },
    })
    instance.addControl(new NavigationControl(), 'top-left')
    instance.on('load', () => {
      instance.addSource(HOTSPOTS, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        attribution: 'Hotspots: Deepfire',
      })
      instance.addLayer({
        id: HOTSPOTS,
        type: 'circle',
        source: HOTSPOTS,
        filter: ['<=', ['get', 't'], -1],
        paint: {
          'circle-radius': radiusByFrp,
          'circle-color': ageColor(0),
          'circle-opacity': 0.85,
          'circle-stroke-width': 0.5,
          'circle-stroke-color': '#3a0d06',
        },
      })
      setStyleReady(true)
    })
    map.current = instance
    // TODO(map): predicted spread cone, reading the same replay time.
    return () => {
      instance.remove()
      map.current = null
      setStyleReady(false)
    }
  }, [])

  const origin = hotspots.length > 0 ? hotspots[0].observedAt : 0

  useEffect(() => {
    if (!styleReady || !map.current) return
    const source = map.current.getSource<GeoJSONSource>(HOTSPOTS)
    source?.setData(toFeatureCollection(hotspots, origin))
  }, [styleReady, hotspots, origin])

  useEffect(() => {
    if (!styleReady || !map.current) return
    const now = time === null ? -1 : (time - origin) / MINUTE
    map.current.setFilter(HOTSPOTS, ['<=', ['get', 't'], now])
    map.current.setPaintProperty(HOTSPOTS, 'circle-color', ageColor(now))
  }, [styleReady, time, origin])

  useEffect(() => {
    if (!map.current) return
    for (const neighbor of neighbors) {
      markers.current.get(neighbor.id)?.remove()
      const marker = new Marker({ color: STATUS_COLOR[neighbor.status] })
        .setLngLat([neighbor.lon, neighbor.lat])
        .setPopup(new Popup({ offset: 24 }).setText(`${neighbor.name} · ${STATUS_LABEL[neighbor.status]}`))
        .addTo(map.current)
      markers.current.set(neighbor.id, marker)
    }
  }, [neighbors])

  return <div ref={container} className="map" />
}
