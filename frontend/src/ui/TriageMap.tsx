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
import { HOUR, MINUTE, type Hotspot } from '../domain/hotspots'
import { burningHours, type LiveFires } from '../domain/liveFires'
import type { SpreadCollection, ZoneRiskList, ZoneShapes } from '../domain/spread'
import type { FireArea, Neighbor, Route, RouteKind } from '../domain/triage'
import type { MapMode } from '../hooks/useMapMode'
import { placeMarkerSvg, statusMarkerSvg } from './markers'
import {
  FIRE_AREA_COLOR,
  formatImpact,
  formatSpanishTime,
  HOTSPOT_AGE_COLORS,
  HOTSPOT_RADIUS_BY_FRP,
  LIVE_RADIUS_BY_HOURS,
  LIVE_RECENCY_COLORS,
  ROUTE_COLOR,
  SPREAD_COLOR,
  SPREAD_OPACITY_BY_HOUR,
  STATUS_COLOR,
  STATUS_ICON,
  STATUS_LABEL,
  ZONE_KIND_LABEL,
  ZONE_RISK_COLORS,
} from './theme'

// MapLibre v6 inside a bundler cannot find its worker on its own.
setWorkerUrl(workerUrl)

// Demo box around Burgohondo, El Tiemblo and La Atalaya (see PLAN.md section 4).
const DEMO_BOUNDS: [[number, number], [number, number]] = [
  [-4.85, 40.3],
  [-4.4, 40.5],
]

// Live mode: the Iberian Peninsula and the Balearic Islands, as queried by the backend.
const IBERIA_BOUNDS: [[number, number], [number, number]] = [
  [-9.6, 35.8],
  [4.4, 44.0],
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
const LIVE_FIRES = 'live-fires'
const FIRE_AREA = 'fire-area'
const SPREAD = 'spread'
const ZONES = 'zones'
const ROUTE = 'route'
const EMPTY: GeoJSONData = { type: 'FeatureCollection', features: [] }

type GeoJSONData = Parameters<GeoJSONSource['setData']>[0]
type GeoJSONGeometry = Extract<GeoJSONData, { type: 'Feature' }>['geometry']

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

function liveFireCollection(live: LiveFires | null): GeoJSONData {
  return {
    type: 'FeatureCollection',
    features: (live?.fires ?? []).map((fire) => ({
      type: 'Feature',
      id: fire.id,
      geometry: { type: 'Point', coordinates: [fire.lon, fire.lat] },
      properties: {
        hoursSinceSeen: (live!.fetchedAt - fire.lastObserved) / HOUR,
        hoursBurning: burningHours(fire),
        lastObserved: fire.lastObserved,
      },
    })),
  }
}

const liveColor = [
  'interpolate',
  ['linear'],
  ['get', 'hoursSinceSeen'],
  ...LIVE_RECENCY_COLORS.flat(),
] as ExpressionSpecification

const liveRadius = [
  'interpolate',
  ['linear'],
  ['get', 'hoursBurning'],
  ...LIVE_RADIUS_BY_HOURS.flat(),
] as ExpressionSpecification

/** Only the zones the prediction reaches, with their minutes to impact. */
function zonesAtRiskCollection(shapes: ZoneShapes | null, risk: ZoneRiskList | null): GeoJSONData {
  const minutes = new Map((risk?.zones ?? []).map((zone) => [zone.id, zone.minutes_to_impact]))
  return {
    type: 'FeatureCollection',
    features: (shapes?.features ?? [])
      .filter((zone) => minutes.get(zone.id) != null)
      .map((zone) => ({
        type: 'Feature',
        geometry: zone.geometry as GeoJSONGeometry,
        properties: { ...zone.properties, minutes: minutes.get(zone.id) },
      })),
  }
}

const zoneColor = [
  'interpolate',
  ['linear'],
  ['get', 'minutes'],
  ...ZONE_RISK_COLORS.flat(),
] as ExpressionSpecification

const spreadOpacity = [
  'interpolate',
  ['linear'],
  ['get', 'hour'],
  ...SPREAD_OPACITY_BY_HOUR.flat(),
] as ExpressionSpecification

const radiusByFrp = [
  'interpolate',
  ['linear'],
  ['get', 'frp'],
  ...HOTSPOT_RADIUS_BY_FRP.flat(),
] as ExpressionSpecification

interface TriageMapProps {
  mode: MapMode
  neighbors: Neighbor[]
  hotspots: Hotspot[]
  /** Replay time in epoch milliseconds: hotspots observed after it are hidden. */
  time: number | null
  live: LiveFires | null
  selectedNeighborId: string | null
  route: Route | null
  routeKind: RouteKind
  /** The area the route avoids; drawn only while a route is shown. */
  fireArea: FireArea | null
  /** Predicted spread and places at risk at the replay time; null in live mode. */
  cone: SpreadCollection | null
  zones: ZoneShapes | null
  risk: ZoneRiskList | null
  onSelectNeighbor: (neighborId: string) => void
}

export function TriageMap({
  mode,
  neighbors,
  hotspots,
  time,
  live,
  selectedNeighborId,
  route,
  routeKind,
  fireArea,
  cone,
  zones,
  risk,
  onSelectNeighbor,
}: TriageMapProps) {
  const container = useRef<HTMLDivElement | null>(null)
  const map = useRef<MapLibreMap | null>(null)
  const markers = useRef<Map<string, Marker>>(new Map())
  const [styleReady, setStyleReady] = useState(false)
  const endpoint = useRef<Marker | null>(null)
  const onSelect = useRef(onSelectNeighbor)
  useEffect(() => {
    onSelect.current = onSelectNeighbor
  }, [onSelectNeighbor])

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
      // Under the hotspots: the burned area the routes avoid.
      instance.addSource(FIRE_AREA, { type: 'geojson', data: EMPTY })
      instance.addLayer({
        id: FIRE_AREA,
        type: 'fill',
        source: FIRE_AREA,
        paint: { 'fill-color': FIRE_AREA_COLOR, 'fill-opacity': 0.12 },
      })
      instance.addLayer({
        id: `${FIRE_AREA}-outline`,
        type: 'line',
        source: FIRE_AREA,
        paint: { 'line-color': FIRE_AREA_COLOR, 'line-width': 1.5, 'line-dasharray': [2, 2] },
      })
      // The predicted spread, one polygon per hour: overlapping fills make the nearest hours darkest.
      instance.addSource(SPREAD, { type: 'geojson', data: EMPTY })
      instance.addLayer({
        id: SPREAD,
        type: 'fill',
        source: SPREAD,
        paint: { 'fill-color': SPREAD_COLOR, 'fill-opacity': spreadOpacity },
      })
      // Places the prediction reaches, coloured by how soon.
      instance.addSource(ZONES, { type: 'geojson', data: EMPTY })
      instance.addLayer({
        id: ZONES,
        type: 'fill',
        source: ZONES,
        paint: { 'fill-color': zoneColor, 'fill-opacity': 0.35 },
      })
      instance.addLayer({
        id: `${ZONES}-outline`,
        type: 'line',
        source: ZONES,
        paint: { 'line-color': zoneColor, 'line-width': 2 },
      })
      instance.on('click', ZONES, (event) => {
        const feature = event.features?.[0]
        if (!feature) return
        const { name, kind, minutes } = feature.properties as { name: string; kind: keyof typeof ZONE_KIND_LABEL; minutes: number }
        new Popup({ offset: 8 })
          .setLngLat(event.lngLat)
          .setText(`${name} · ${ZONE_KIND_LABEL[kind]} · fire ${formatImpact(minutes)}`)
          .addTo(instance)
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
      instance.addSource(LIVE_FIRES, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        attribution: 'Active fires: Deepfire',
      })
      instance.addLayer({
        id: LIVE_FIRES,
        type: 'circle',
        source: LIVE_FIRES,
        layout: { visibility: 'none' },
        paint: {
          'circle-radius': liveRadius,
          'circle-color': liveColor,
          'circle-opacity': 0.85,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#fff',
        },
      })
      // Over everything: the selected resident's route out.
      instance.addSource(ROUTE, { type: 'geojson', data: EMPTY })
      instance.addLayer({
        id: `${ROUTE}-casing`,
        type: 'line',
        source: ROUTE,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#fff', 'line-width': 8 },
      })
      instance.addLayer({
        id: ROUTE,
        type: 'line',
        source: ROUTE,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ROUTE_COLOR, 'line-width': 5 },
      })
      instance.on('click', LIVE_FIRES, (event) => {
        const feature = event.features?.[0]
        if (!feature || feature.geometry.type !== 'Point') return
        const { hoursBurning, lastObserved } = feature.properties as { hoursBurning: number; lastObserved: number }
        new Popup({ offset: 12 })
          .setLngLat(feature.geometry.coordinates as [number, number])
          .setText(`Detected over ${Math.round(hoursBurning)} h · last seen ${formatSpanishTime(lastObserved)}`)
          .addTo(instance)
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
    if (!styleReady || !map.current) return
    map.current.getSource<GeoJSONSource>(LIVE_FIRES)?.setData(liveFireCollection(live))
  }, [styleReady, live])

  useEffect(() => {
    if (!styleReady || !map.current) return
    map.current.setLayoutProperty(HOTSPOTS, 'visibility', mode === 'replay' ? 'visible' : 'none')
    map.current.setLayoutProperty(LIVE_FIRES, 'visibility', mode === 'live' ? 'visible' : 'none')
    map.current.fitBounds(mode === 'live' ? IBERIA_BOUNDS : DEMO_BOUNDS, { padding: 24, duration: 800 })
  }, [styleReady, mode])

  useEffect(() => {
    if (!styleReady || !map.current) return
    map.current.getSource<GeoJSONSource>(SPREAD)?.setData(cone ?? EMPTY)
    map.current.getSource<GeoJSONSource>(ZONES)?.setData(zonesAtRiskCollection(zones, risk))
  }, [styleReady, cone, zones, risk])

  // The route and the area it avoids belong to the replay; live mode hides them.
  const showRoute = mode === 'replay' && route?.geometry != null

  useEffect(() => {
    if (!styleReady || !map.current) return
    const instance = map.current
    instance.getSource<GeoJSONSource>(ROUTE)?.setData(
      showRoute ? { type: 'Feature', geometry: route!.geometry!, properties: {} } : EMPTY,
    )
    instance.getSource<GeoJSONSource>(FIRE_AREA)?.setData(
      showRoute && fireArea ? { type: 'Feature', geometry: fireArea.geometry as GeoJSONGeometry, properties: {} } : EMPTY,
    )
    endpoint.current?.remove()
    endpoint.current = null
    if (showRoute) {
      const coordinates = route!.geometry!.coordinates
      const element = document.createElement('div')
      element.className = 'place-marker'
      element.innerHTML = placeMarkerSvg(routeKind === 'rescue' ? 'fire-truck' : 'flag')
      endpoint.current = new Marker({ element })
        .setLngLat(routeKind === 'rescue' ? coordinates[0] : coordinates[coordinates.length - 1])
        .addTo(instance)
      const lons = coordinates.map(([lon]) => lon)
      const lats = coordinates.map(([, lat]) => lat)
      instance.fitBounds(
        [
          [Math.min(...lons), Math.min(...lats)],
          [Math.max(...lons), Math.max(...lats)],
        ],
        { padding: { top: 80, right: 80, bottom: 150, left: 80 }, duration: 800, maxZoom: 14 },
      )
    }
  }, [styleReady, showRoute, route, routeKind, fireArea])

  // Markers are rebuilt only when what they show changes, so a click is never lost to a poll.
  const drawn = useRef<Map<string, string>>(new Map())

  useEffect(() => {
    if (!map.current) return
    for (const neighbor of neighbors) {
      const look = `${neighbor.status}|${neighbor.lon}|${neighbor.lat}|${neighbor.name}`
      let marker = markers.current.get(neighbor.id)
      if (marker === undefined || drawn.current.get(neighbor.id) !== look) {
        marker?.remove()
        const element = document.createElement('div')
        element.className = 'status-marker'
        element.setAttribute('role', 'button')
        element.setAttribute('aria-label', `${neighbor.name}: ${STATUS_LABEL[neighbor.status]}`)
        element.innerHTML = statusMarkerSvg(STATUS_COLOR[neighbor.status], STATUS_ICON[neighbor.status])
        marker = new Marker({ element, anchor: 'bottom' })
          .setLngLat([neighbor.lon, neighbor.lat])
          .setPopup(new Popup({ offset: [0, -38] }).setText(`${neighbor.name} · ${STATUS_LABEL[neighbor.status]}`))
          .addTo(map.current)
        marker.getElement().addEventListener('click', () => onSelect.current(neighbor.id))
        markers.current.set(neighbor.id, marker)
        drawn.current.set(neighbor.id, look)
      }
      marker.getElement().classList.toggle('selected', neighbor.id === selectedNeighborId)
    }
  }, [neighbors, selectedNeighborId])

  return <div ref={container} className="map" />
}
