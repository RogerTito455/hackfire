import { useEffect, useRef } from 'react'
import { Map as MapLibreMap, Marker, NavigationControl, Popup, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Neighbor } from '../domain/triage'
import { STATUS_COLOR, STATUS_LABEL } from './theme'

// Demo box: roughly 15 km around El Tiemblo and La Atalaya (see PLAN.md section 4).
const DEMO_CENTER: [number, number] = [-4.51, 40.422]

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

interface TriageMapProps {
  neighbors: Neighbor[]
}

export function TriageMap({ neighbors }: TriageMapProps) {
  const container = useRef<HTMLDivElement | null>(null)
  const map = useRef<MapLibreMap | null>(null)
  const markers = useRef<Map<string, Marker>>(new Map())

  useEffect(() => {
    if (!container.current || map.current) return
    map.current = new MapLibreMap({
      container: container.current,
      style: OSM_STYLE,
      center: DEMO_CENTER,
      zoom: 12.5,
    })
    map.current.addControl(new NavigationControl(), 'top-left')
    // TODO(map): hotspot layer, predicted spread cone and time slider.
    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

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
