// Backend client. The only file that knows URLs and HTTP.

import type { HotspotCollection } from '../domain/hotspots'
import type { LeadTime } from '../domain/leadTime'
import type { LiveFireCollection } from '../domain/liveFires'
import type { SpreadCollection } from '../domain/spread'
import type { CrewAlert, FireArea, Neighbor, Rescue, Route, TravelMode } from '../domain/triage'
import type { ImpactTable, ZoneCollection } from '../domain/zones'

// Deployed, the backend serves this dashboard, so the API is on the same origin. VITE_API_URL
// points a local dashboard at another backend.
const DEFAULT_API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''
const API_URL = (import.meta.env.VITE_API_URL ?? DEFAULT_API_URL).replace(/\/+$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init)
  if (!response.ok) throw new Error(`${path} returned ${response.status}`)
  return response.json() as Promise<T>
}

export const fetchNeighbors = () => request<Neighbor[]>('/api/neighbors')
export const fetchRescues = () => request<Rescue[]>('/api/rescues')
export const resetDemo = () => request<{ status: string }>('/api/reset', { method: 'POST' })
export const fetchHotspots = () => request<HotspotCollection>('/api/hotspots')
export const fetchLiveFires = () => request<LiveFireCollection>('/api/live/fires')
export const fetchRoute = (neighborId: string, mode: TravelMode) =>
  request<Route>(`/api/routes/${encodeURIComponent(neighborId)}?mode=${mode}`)
export const fetchFireArea = (crew: boolean) => request<FireArea>(`/api/fire-area${crew ? '?crew=true' : ''}`)
export const fetchRescueRoute = (neighborId: string) =>
  request<Route>(`/api/rescue-routes/${encodeURIComponent(neighborId)}`)
export const fetchAlerts = () => request<CrewAlert[]>('/api/alerts')
export const fetchSpread = () => request<SpreadCollection>('/api/spread')
export const fetchZones = () => request<ZoneCollection>('/api/zones')
export const fetchImpact = () => request<ImpactTable>('/api/impact')
export const fetchLeadTime = () => request<LeadTime>('/api/lead-time')
/** Tell the backend which replay moment the slider is on, so `get_fire_status` answers for it. */
export const setReplayTime = (isoTime: string) =>
  request<{ at: string }>('/api/replay/time', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ at: isoTime }),
  })
