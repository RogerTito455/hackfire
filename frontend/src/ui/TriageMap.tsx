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
import type { SpreadPolygon } from '../domain/spread'
import type { Neighbor } from '../domain/triage'
import type { ZoneImpact } from '../domain/zones'
import {
  HOTSPOT_AGE_COLORS,
  HOTSPOT_RADIUS_BY_FRP,
  SPREAD_HOUR_COLORS,
  STATUS_COLOR,
  STATUS_LABEL,
  ZONE_URGENCY_COLORS,
} from './theme'

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
const SPREAD = 'spread'
const ZONES = 'zones'

type GeoJSONData = Parameters<GeoJSONSource['setData']>[0]

// Geometries arrive from the backend as opaque GeoJSON, so the collections below are cast at this boundary.
function spreadToFeatureCollection(spread: readonly SpreadPolygon[]): GeoJSONData {
  return {
    type: 'FeatureCollection',
    features: spread.map(({ hour, geometry }) => ({ type: 'Feature', geometry, properties: { hour } })),
  } as unknown as GeoJSONData
}

function zonesToFeatureCollection(zones: readonly ZoneImpact[]): GeoJSONData {
  return {
    type: 'FeatureCollection',
    features: zones.map(({ zone, minutes }) => ({
      type: 'Feature',
      geometry: zone.geometry,
      properties: { kind: zone.kind, minutes },
    })),
  } as unknown as GeoJSONData
}

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

const spreadColor = [
  'interpolate',
  ['linear'],
  ['get', 'hour'],
  ...SPREAD_HOUR_COLORS.flat(),
] as ExpressionSpecification

const zoneColor = [
  'interpolate',
  ['linear'],
  ['get', 'minutes'],
  ...ZONE_URGENCY_COLORS.flat(),
] as ExpressionSpecification

// Facilities are a few pixels wide at this zoom: a thick outline keeps them visible.
const zoneLineWidth = [
  'match',
  ['get', 'kind'],
  ['estate', 'town'],
  2,
  'road',
  2.5,
  3.5,
] as ExpressionSpecification

interface TriageMapProps {
  neighbors: Neighbor[]
  hotspots: Hotspot[]
  /** Replay time in epoch milliseconds: hotspots observed after it are hidden. */
  time: number | null
  /** Predicted spread of the forecast in force, largest first. */
  spread: SpreadPolygon[]
  /** Zones the predicted fire reaches, with their minutes to impact. */
  zones: ZoneImpact[]
}

export function TriageMap({ neighbors, hotspots, time, spread, zones }: TriageMapProps) {
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
      // Predicted spread and zones at risk go under the hotspots, which stay on top.
      const empty = { type: 'FeatureCollection', features: [] } as GeoJSONData
      instance.addSource(SPREAD, { type: 'geojson', data: empty, attribution: 'Spread: HackFire model' })
      instance.addSource(ZONES, { type: 'geojson', data: empty, attribution: 'Places: © OpenStreetMap' })
      instance.addLayer({
        id: 'spread-fill',
        type: 'fill',
        source: SPREAD,
        paint: { 'fill-color': spreadColor, 'fill-opacity': 0.2 },
      })
      instance.addLayer({
        id: 'spread-outline',
        type: 'line',
        source: SPREAD,
        paint: { 'line-color': spreadColor, 'line-width': 1.2, 'line-opacity': 0.9 },
      })
      instance.addLayer({
        id: 'zones-fill',
        type: 'fill',
        source: ZONES,
        paint: { 'fill-color': zoneColor, 'fill-opacity': 0.55 },
      })
      instance.addLayer({
        id: 'zones-outline',
        type: 'line',
        source: ZONES,
        paint: { 'line-color': zoneColor, 'line-width': zoneLineWidth },
      })
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
    if (!styleReady || !map.current) return
    map.current.getSource<GeoJSONSource>(SPREAD)?.setData(spreadToFeatureCollection(spread))
  }, [styleReady, spread])

  useEffect(() => {
    if (!styleReady || !map.current) return
    map.current.getSource<GeoJSONSource>(ZONES)?.setData(zonesToFeatureCollection(zones))
  }, [styleReady, zones])

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
