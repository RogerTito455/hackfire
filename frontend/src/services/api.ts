// Backend client. The only file that knows URLs and HTTP.

import type { HotspotCollection } from '../domain/hotspots'
import type { LiveFireCollection } from '../domain/liveFires'
import type { FireArea, Neighbor, Rescue, Route, TravelMode } from '../domain/triage'

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
export const fetchFireArea = () => request<FireArea>('/api/fire-area')
