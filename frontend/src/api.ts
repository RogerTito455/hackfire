export type TriageStatus = 'pending' | 'evacuating' | 'no_answer' | 'needs_rescue'

export interface Neighbor {
  id: string
  name: string
  address: string
  zone: string
  lat: number
  lon: number
  status: TriageStatus
  people: number | null
  mobility: string | null
  observation: string | null
  updated_at: string | null
}

export interface Rescue {
  rescue_id: string
  neighbor: Neighbor
  minutes_to_impact: number | null
  priority: number
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`)
  if (!response.ok) throw new Error(`${path} returned ${response.status}`)
  return response.json() as Promise<T>
}

export const fetchNeighbors = () => getJson<Neighbor[]>('/api/neighbors')
export const fetchRescues = () => getJson<Rescue[]>('/api/rescues')
