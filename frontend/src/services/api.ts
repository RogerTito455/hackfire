// Backend client. The only file that knows URLs and HTTP.

import type { HotspotCollection } from '../domain/hotspots'
import type { SpreadCollection } from '../domain/spread'
import type { Neighbor, Rescue } from '../domain/triage'
import type { ImpactTable, ZoneCollection } from '../domain/zones'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init)
  if (!response.ok) throw new Error(`${path} returned ${response.status}`)
  return response.json() as Promise<T>
}

export const fetchNeighbors = () => request<Neighbor[]>('/api/neighbors')
export const fetchRescues = () => request<Rescue[]>('/api/rescues')
export const resetDemo = () => request<{ status: string }>('/api/reset', { method: 'POST' })
export const fetchHotspots = () => request<HotspotCollection>('/api/hotspots')
export const fetchSpread = () => request<SpreadCollection>('/api/spread')
export const fetchZones = () => request<ZoneCollection>('/api/zones')
export const fetchImpact = () => request<ImpactTable>('/api/impact')
/** Tell the backend which replay moment the slider is on, so `get_fire_status` answers for it. */
export const setReplayTime = (isoTime: string) =>
  request<{ at: string }>('/api/replay/time', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ at: isoTime }),
  })
