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
import { closureArea, type RoadClosure } from '../domain/closures'
import type { SpreadPolygon } from '../domain/spread'
import type { FireArea, Neighbor, Route, RouteKind } from '../domain/triage'
import { ROAD_CLOSED_WITHIN_MIN, type ZoneImpact } from '../domain/zones'
import type { MapMode } from '../hooks/useMapMode'
import { useI18n } from './i18n'
import { placeMarkerSvg, STATUS_MARKER_HEIGHT, statusMarkerSvg } from './markers'
import {
  BASEMAP_PAINT,
  CLOSURE_COLOR,
  FIRE_AREA_COLOR,
  formatSpanishTime,
  HOTSPOT_AGE_COLORS,
  HOTSPOT_RADIUS_BY_FRP,
  LIVE_RADIUS_BY_HOURS,
  LIVE_RECENCY_COLORS,
  ROAD_CLOSED_COLOR,
  ROUTE_COLOR,
  SPREAD_HOUR_COLORS,
  STATUS_COLOR,
  STATUS_ICON,
  ZONE_URGENCY_COLORS,
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

const DARK = '(prefers-color-scheme: dark)'

function basemapPaint() {
  return window.matchMedia?.(DARK).matches ? BASEMAP_PAINT.dark : BASEMAP_PAINT.light
}

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
  layers: [{ id: 'osm', type: 'raster', source: 'osm', paint: basemapPaint() }],
}

const HOTSPOTS = 'hotspots'
const LIVE_FIRES = 'live-fires'
const FIRE_AREA = 'fire-area'
const ROUTE = 'route'
const CLOSURES = 'closures'
const SPREAD = 'spread'
const ZONES = 'zones'
const EMPTY: GeoJSONData = { type: 'FeatureCollection', features: [] }

type GeoJSONData = Parameters<GeoJSONSource['setData']>[0]
type GeoJSONGeometry = Extract<GeoJSONData, { type: 'Feature' }>['geometry']

// Spread and zone geometries arrive from the backend as opaque GeoJSON, so the collections below are
// cast at this boundary.
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

/** Hotspot radius by fire power, scaled with the zoom so a zoomed-out fire is not one orange blob. */
const radiusByFrp = (scale: number) =>
  [
    'interpolate',
    ['linear'],
    ['get', 'frp'],
    ...HOTSPOT_RADIUS_BY_FRP.flatMap(([frp, radius]) => [frp, radius * scale]),
  ] as ExpressionSpecification

const hotspotRadius = [
  'interpolate',
  ['linear'],
  ['zoom'],
  8,
  radiusByFrp(0.45),
  11,
  radiusByFrp(0.8),
  14,
  radiusByFrp(1.3),
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

// Predicted spread and the zones it reaches belong to the replay; live mode hides them.
const REPLAY_LAYERS = ['spread-fill', 'spread-outline', 'zones-fill', 'zones-outline', 'roads-closed-casing', 'roads-closed']

// Roads the fire reaches within the hour: closed to residents, open to crews (domain/zones.ts).
const ROAD_CLOSED_FILTER = [
  'all',
  ['==', ['get', 'kind'], 'road'],
  ['<=', ['get', 'minutes'], ROAD_CLOSED_WITHIN_MIN],
] as ExpressionSpecification

// Leave room for what covers the map: the top bar, and on a phone the bottom sheet.
function routePadding() {
  const phone = window.matchMedia('(max-width: 899px)').matches
  return phone
    ? { top: 90, right: 40, bottom: Math.round(window.innerHeight * 0.55), left: 40 }
    : { top: 80, right: 80, bottom: 80, left: 80 }
}

interface TriageMapProps {
  mode: MapMode
  neighbors: Neighbor[]
  hotspots: Hotspot[]
  /** Replay time in epoch milliseconds: hotspots observed after it are hidden. */
  time: number | null
  live: LiveFires | null
  selectedNeighborId: string | null
  route: Route | null
  /** Out by car or on foot (the flag marks the destination), or the crew's way in (from the fire station). */
  routeKind: RouteKind
  /** The area the route avoids; drawn only while a route is shown. */
  fireArea: FireArea | null
  onSelectNeighbor: (neighborId: string) => void
  /** Predicted spread of the forecast in force, largest first. */
  spread: SpreadPolygon[]
  /** Zones the predicted fire reaches, with their minutes to impact. */
  zones: ZoneImpact[]
  /** A resident's live video (#18), drawn next to their pin with the last caption under it. */
  liveVideo?: { lon: number; lat: number; element: HTMLElement; caption: string; waiting: boolean } | null
  /** Roads marked as cut, drawn as no-entry signs over the stretch they close. */
  closures?: RoadClosure[]
  /** While true, a tap on the map reports where, to close the road there. */
  closing?: boolean
  onMapClick?: (lon: number, lat: number) => void
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
  onSelectNeighbor,
  spread,
  zones,
  liveVideo = null,
  closures = [],
  closing = false,
  onMapClick,
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
  // The map is built once: its click handler reads whether a road is being closed through refs.
  const tapToClose = useRef<((lon: number, lat: number) => void) | null>(null)
  useEffect(() => {
    tapToClose.current = closing && onMapClick ? onMapClick : null
  }, [closing, onMapClick])
  // The map is built once; its click handlers read the current language through this ref.
  const { t, intl } = useI18n()
  const words = useRef({ t, intl })
  useEffect(() => {
    words.current = { t, intl }
  }, [t, intl])

  useEffect(() => {
    if (!container.current || map.current) return
    const instance = new MapLibreMap({
      // Credits collapse to an (i) button, so they never cover the sheet on a phone.
      attributionControl: { compact: true },
      container: container.current,
      style: OSM_STYLE,
      bounds: DEMO_BOUNDS,
      fitBoundsOptions: { padding: 24 },
    })
    instance.addControl(new NavigationControl(), 'top-left')
    instance.on('load', () => {
      // Compact credits start open; fold them into the (i) button until someone taps it.
      instance.getContainer().querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
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
      // Predicted spread and zones at risk go under the hotspots, which stay on top.
      instance.addSource(SPREAD, { type: 'geojson', data: EMPTY, attribution: 'Spread: HackFire model' })
      instance.addSource(ZONES, { type: 'geojson', data: EMPTY, attribution: 'Places: © OpenStreetMap' })
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
      instance.addLayer({
        id: 'roads-closed-casing',
        type: 'line',
        source: ZONES,
        filter: ROAD_CLOSED_FILTER,
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': '#fff', 'line-width': 7 },
      })
      instance.addLayer({
        id: 'roads-closed',
        type: 'line',
        source: ZONES,
        filter: ROAD_CLOSED_FILTER,
        paint: { 'line-color': ROAD_CLOSED_COLOR, 'line-width': 4, 'line-dasharray': [1.2, 0.8] },
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
          'circle-radius': hotspotRadius,
          'circle-color': ageColor(0),
          'circle-opacity': 0.85,
          'circle-stroke-width': 0.75,
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
        paint: { 'line-color': '#fff', 'line-width': 10 },
      })
      instance.addLayer({
        id: ROUTE,
        type: 'line',
        source: ROUTE,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ROUTE_COLOR, 'line-width': 6 },
      })
      // Closed roads: the stretch each one cuts, over the route so a cut on it shows.
      instance.addSource(CLOSURES, { type: 'geojson', data: EMPTY })
      instance.addLayer({
        id: `${CLOSURES}-fill`,
        type: 'fill',
        source: CLOSURES,
        paint: { 'fill-color': CLOSURE_COLOR, 'fill-opacity': 0.18 },
      })
      instance.addLayer({
        id: `${CLOSURES}-outline`,
        type: 'line',
        source: CLOSURES,
        paint: { 'line-color': CLOSURE_COLOR, 'line-width': 2 },
      })
      instance.on('click', (event) => tapToClose.current?.(event.lngLat.lng, event.lngLat.lat))
      instance.on('click', LIVE_FIRES, (event) => {
        const feature = event.features?.[0]
        if (!feature || feature.geometry.type !== 'Point') return
        const { hoursBurning, lastObserved } = feature.properties as { hoursBurning: number; lastObserved: number }
        new Popup({ offset: 12, closeButton: false, focusAfterOpen: false })
          .setLngLat(feature.geometry.coordinates as [number, number])
          .setText(
            words.current.t('map.liveFire', {
              hours: Math.round(hoursBurning),
              time: formatSpanishTime(lastObserved, words.current.intl),
            }),
          )
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

  useEffect(() => {
    if (!styleReady || !window.matchMedia) return
    const query = window.matchMedia(DARK)
    const apply = () => {
      const paint = basemapPaint()
      for (const property of Object.keys(paint) as (keyof typeof paint)[]) {
        map.current?.setPaintProperty('osm', property, paint[property])
      }
    }
    query.addEventListener('change', apply)
    return () => query.removeEventListener('change', apply)
  }, [styleReady])

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
    map.current.getSource<GeoJSONSource>(SPREAD)?.setData(spreadToFeatureCollection(spread))
  }, [styleReady, spread])

  useEffect(() => {
    if (!styleReady || !map.current) return
    map.current.getSource<GeoJSONSource>(ZONES)?.setData(zonesToFeatureCollection(zones))
  }, [styleReady, zones])

  useEffect(() => {
    if (!styleReady || !map.current) return
    map.current.setLayoutProperty(HOTSPOTS, 'visibility', mode === 'replay' ? 'visible' : 'none')
    for (const layer of REPLAY_LAYERS) {
      map.current.setLayoutProperty(layer, 'visibility', mode === 'replay' ? 'visible' : 'none')
    }
    map.current.setLayoutProperty(LIVE_FIRES, 'visibility', mode === 'live' ? 'visible' : 'none')
    map.current.fitBounds(mode === 'live' ? IBERIA_BOUNDS : DEMO_BOUNDS, { padding: 24, duration: 800 })
  }, [styleReady, mode])

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
        { padding: routePadding(), duration: 800, maxZoom: 14 },
      )
    }
  }, [styleReady, showRoute, route, routeKind, fireArea])

  // Closed roads: the area on the map, a no-entry marker on each, and a crosshair while closing one.
  const closureMarkers = useRef<Marker[]>([])
  useEffect(() => {
    if (!styleReady || !map.current) return
    const instance = map.current
    instance.getSource<GeoJSONSource>(CLOSURES)?.setData({
      type: 'FeatureCollection',
      features: closures.map((closure) => ({ type: 'Feature', geometry: closureArea(closure), properties: {} })),
    })
    for (const marker of closureMarkers.current) marker.remove()
    closureMarkers.current = closures.map((closure) => {
      const element = document.createElement('div')
      element.className = 'place-marker closure-marker'
      element.setAttribute('aria-label', t('closures.marker'))
      element.innerHTML = placeMarkerSvg('road-closed')
      return new Marker({ element }).setLngLat([closure.lon, closure.lat]).addTo(instance)
    })
  }, [styleReady, closures, t])

  useEffect(() => {
    if (map.current) map.current.getCanvas().style.cursor = closing ? 'crosshair' : ''
  }, [closing])

  // Markers are rebuilt only when what they show changes, so a click is never lost to a poll.
  const drawn = useRef<Map<string, string>>(new Map())

  useEffect(() => {
    if (!map.current) return
    for (const neighbor of neighbors) {
      const look = `${neighbor.status}|${neighbor.lon}|${neighbor.lat}|${neighbor.name}|${intl}`
      const label = t('map.resident', { name: neighbor.name, status: t(`status.${neighbor.status}`) })
      let marker = markers.current.get(neighbor.id)
      if (marker === undefined || drawn.current.get(neighbor.id) !== look) {
        marker?.remove()
        const element = document.createElement('div')
        element.className = 'status-marker'
        element.setAttribute('role', 'button')
        element.setAttribute('aria-label', label)
        element.innerHTML = statusMarkerSvg(STATUS_COLOR[neighbor.status], STATUS_ICON[neighbor.status])
        marker = new Marker({ element, anchor: 'bottom' })
          .setLngLat([neighbor.lon, neighbor.lat])
          .setPopup(new Popup({ offset: [0, -STATUS_MARKER_HEIGHT + 2], closeButton: false, focusAfterOpen: false }).setText(label))
          .addTo(map.current)
        marker.getElement().addEventListener('click', () => onSelect.current(neighbor.id))
        markers.current.set(neighbor.id, marker)
        drawn.current.set(neighbor.id, look)
      }
      marker.getElement().classList.toggle('selected', neighbor.id === selectedNeighborId)
    }
  }, [neighbors, selectedNeighborId, t, intl])

  // The resident's video, anchored next to their pin; the caption is updated in place.
  const videoMarker = useRef<Marker | null>(null)
  const videoCaption = useRef<HTMLParagraphElement | null>(null)
  const videoLon = liveVideo?.lon
  const videoLat = liveVideo?.lat
  const videoElement = liveVideo?.element
  useEffect(() => {
    if (!map.current || !videoElement || videoLon === undefined || videoLat === undefined) return
    const card = document.createElement('div')
    card.className = 'live-video'
    const caption = document.createElement('p')
    caption.className = 'live-video-caption'
    card.append(videoElement, caption)
    videoCaption.current = caption
    videoMarker.current = new Marker({ element: card, anchor: 'bottom-left', offset: [18, -30] })
      .setLngLat([videoLon, videoLat])
      .addTo(map.current)
    // Bring the resident into view with room for the card, which opens up and to the right of the pin.
    map.current.easeTo({ center: [videoLon, videoLat], offset: [-120, 90], duration: 800 })
    return () => {
      videoMarker.current?.remove()
      videoMarker.current = null
      videoCaption.current = null
    }
  }, [videoElement, videoLon, videoLat])

  const videoText = liveVideo ? (liveVideo.waiting ? t('video.waiting') : liveVideo.caption) : ''
  useEffect(() => {
    if (videoCaption.current) videoCaption.current.textContent = videoText
  }, [videoText])

  return <div ref={container} className="map" />
}
