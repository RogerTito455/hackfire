import { useEffect, useRef, useState } from 'react'
import { Map as MapLibreMap, Marker, NavigationControl, Popup, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { fetchNeighbors, fetchRescues, type Neighbor, type Rescue, type TriageStatus } from './api'
import './App.css'

// Demo box: roughly 15 km around El Tiemblo and La Atalaya (see PLAN.md section 4).
const DEMO_CENTER: [number, number] = [-4.51, 40.422]
const POLL_MS = 2000

const STATUS_LABEL: Record<TriageStatus, string> = {
  pending: 'Not called yet',
  evacuating: 'Evacuating',
  no_answer: 'No answer',
  needs_rescue: 'Needs rescue',
}

const STATUS_COLOR: Record<TriageStatus, string> = {
  pending: '#8a8f98',
  evacuating: '#2e9e5b',
  no_answer: '#e0a100',
  needs_rescue: '#d93025',
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
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}

function App() {
  const mapContainer = useRef<HTMLDivElement | null>(null)
  const map = useRef<MapLibreMap | null>(null)
  const markers = useRef<Map<string, Marker>>(new Map())
  const [neighbors, setNeighbors] = useState<Neighbor[]>([])
  const [rescues, setRescues] = useState<Rescue[]>([])
  const [online, setOnline] = useState(true)

  useEffect(() => {
    if (!mapContainer.current || map.current) return
    map.current = new MapLibreMap({
      container: mapContainer.current,
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
    let cancelled = false
    const poll = async () => {
      try {
        const [nextNeighbors, nextRescues] = await Promise.all([fetchNeighbors(), fetchRescues()])
        if (cancelled) return
        setNeighbors(nextNeighbors)
        setRescues(nextRescues)
        setOnline(true)
      } catch {
        if (!cancelled) setOnline(false)
      }
    }
    poll()
    const timer = setInterval(poll, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    if (!map.current) return
    for (const neighbor of neighbors) {
      markers.current.get(neighbor.id)?.remove()
      const marker = new Marker({ color: STATUS_COLOR[neighbor.status] })
        .setLngLat([neighbor.lon, neighbor.lat])
        .setPopup(
          new Popup({ offset: 24 }).setText(
            `${neighbor.name} · ${STATUS_LABEL[neighbor.status]}`,
          ),
        )
        .addTo(map.current)
      markers.current.set(neighbor.id, marker)
    }
  }, [neighbors])

  const counts = neighbors.reduce<Record<TriageStatus, number>>(
    (acc, n) => ({ ...acc, [n.status]: acc[n.status] + 1 }),
    { pending: 0, evacuating: 0, no_answer: 0, needs_rescue: 0 },
  )

  return (
    <div className="layout">
      <aside className="panel">
        <header>
          <h1>HackFire</h1>
          <p className={online ? 'conn ok' : 'conn down'}>
            {online ? 'Backend connected' : 'Backend unreachable'}
          </p>
        </header>

        <section>
          <h2>Triage</h2>
          <ul className="counts">
            {(Object.keys(STATUS_LABEL) as TriageStatus[]).map((status) => (
              <li key={status}>
                <span className="dot" style={{ background: STATUS_COLOR[status] }} />
                {STATUS_LABEL[status]}
                <strong>{counts[status]}</strong>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h2>Rescue queue</h2>
          {rescues.length === 0 ? (
            <p className="empty">No rescues pending.</p>
          ) : (
            <ol className="rescues">
              {rescues.map((rescue) => (
                <li key={rescue.rescue_id}>
                  <strong>{rescue.neighbor.name}</strong>
                  <span>{rescue.neighbor.address}</span>
                  <span>
                    {rescue.neighbor.people ?? '?'} people · {rescue.neighbor.mobility ?? 'mobility unknown'}
                  </span>
                  {rescue.minutes_to_impact !== null && (
                    <span className="impact">~{rescue.minutes_to_impact} min to impact</span>
                  )}
                </li>
              ))}
            </ol>
          )}
        </section>
      </aside>
      <div ref={mapContainer} className="map" />
    </div>
  )
}

export default App
