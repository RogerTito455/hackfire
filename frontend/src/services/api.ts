// Backend client. The only file that knows URLs and HTTP.

import type { Autopilot } from '../domain/autopilot'
import type { HotspotCollection } from '../domain/hotspots'
import type { EvacuationOrder, OrderDecision, SafePoint } from '../domain/orders'
import type { LeadTime } from '../domain/leadTime'
import type { LiveFireCollection } from '../domain/liveFires'
import type { LiveSpreadResponse } from '../domain/liveSpread'
import type { LiveOperationsResponse } from '../domain/liveOperations'
import type { SpreadCollection } from '../domain/spread'
import type { TextClassification } from '../domain/textTriage'
import type { AgentFocus, CrewAlert, FireArea, Neighbor, Rescue, Route, TravelMode, TriageStatus } from '../domain/triage'
import type { ImpactTable, ZoneCollection } from '../domain/zones'
import type { CampaignCall, VoiceCapabilities, WebSession } from '../domain/voice'
import type { CrewRoom, RescueVideo, RescueVideoLink, VideoAccess, VideoCapabilities } from '../domain/video'
import type { CrewPlan } from '../domain/crewPlan'
import type { RoadClosure } from '../domain/closures'
import type { Scenario } from '../domain/scenario'

// Deployed, the backend serves this dashboard, so the API is on the same origin. VITE_API_URL
// points a local dashboard at another backend.
const DEFAULT_API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''
const API_URL = (import.meta.env.VITE_API_URL ?? DEFAULT_API_URL).replace(/\/+$/, '')

// The backend writes some sentences itself (route directions, orders, crew alerts): every request
// asks for them in the dashboard's language, which the i18n provider keeps in <html lang>.
function inDashboardLanguage(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers)
  headers.set('Accept-Language', document.documentElement.lang || 'en')
  return { ...init, headers }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, inDashboardLanguage(init))
  if (!response.ok) throw new Error(`${path} returned ${response.status}`)
  return response.json() as Promise<T>
}

export const fetchNeighbors = () => request<Neighbor[]>('/api/neighbors')
export const fetchRescues = () => request<Rescue[]>('/api/rescues')
export const resetDemo = () => request<{ status: string }>('/api/reset', { method: 'POST' })
export const fetchScenario = () => request<Scenario>('/api/scenario')
export const fetchHotspots = () => request<HotspotCollection>('/api/hotspots')
export const fetchLiveFires = () => request<LiveFireCollection>('/api/live/fires')
export const fetchLiveSpread = () => request<LiveSpreadResponse>('/api/live/spread')
/** Places at risk, alert drafts and roads to close for one live fire with a Deepfire run. */
export const fetchLiveOperations = (fireId: string) =>
  request<LiveOperationsResponse>(`/api/live/operations/${encodeURIComponent(fireId)}`)
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
/** The demo autopilot: on at the slider's moment, or off (the backend puts the state back). */
export const fetchAutopilot = () => request<Autopilot>('/api/autopilot')
export const setAutopilot = (enabled: boolean, isoTime?: string) =>
  request<Autopilot>('/api/autopilot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled, at: isoTime ?? null }),
  })
export const fetchOrders = () => request<EvacuationOrder[]>('/api/orders')
export const fetchSafePoints = () => request<SafePoint[]>('/api/safe-points')
export const approveOrder = (zone: string, decision: OrderDecision) =>
  request<EvacuationOrder>(`/api/orders/${encodeURIComponent(zone)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  })
export const fetchTextTriageAvailable = () => request<{ available: boolean }>('/api/triage/text')
export const triageFromText = (neighborId: string, text: string) =>
  request<{ neighbor: Neighbor; classification: TextClassification }>('/api/triage/text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ neighbor_id: neighborId, text }),
  })
export const reportStatus = (neighborId: string, status: TriageStatus) =>
  request<Neighbor>('/tools/report_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ neighbor_id: neighborId, status }),
  })
export const fetchFocus = () => request<AgentFocus | null>('/api/focus')
export const fetchVoiceCapabilities = () => request<VoiceCapabilities>('/api/voice')
export const startCampaign = (zone: string) =>
  request<CampaignCall[]>(`/api/campaigns/${encodeURIComponent(zone)}`, { method: 'POST' })
export const createWebSession = (neighborId: string) =>
  request<WebSession>(`/api/neighbors/${encodeURIComponent(neighborId)}/web-session`, { method: 'POST' })
export const createCoordinatorSession = () => request<WebSession>('/api/coordinator/web-session', { method: 'POST' })
/** A browser call with this resident ended: the backend flags them for a follow-up if nothing was recorded. */
export const reportCallEnded = (neighborId: string) =>
  request<{ status: string }>(`/api/neighbors/${encodeURIComponent(neighborId)}/call-ended`, { method: 'POST' })
export const fetchVideoCapabilities = () => request<VideoCapabilities>('/api/video')
export const requestRescueVideo = (neighborId: string) =>
  request<RescueVideoLink>(`/api/rescues/${encodeURIComponent(neighborId)}/video`, { method: 'POST' })
export const watchRescueVideo = (neighborId: string) =>
  request<RescueVideo>(`/api/rescues/${encodeURIComponent(neighborId)}/video`)

/** The resident's camera access, once per link: 'used' when it was opened before, 'unknown' when it never existed. */
export async function joinVideo(linkId: string): Promise<VideoAccess | 'used' | 'unknown'> {
  const response = await fetch(`${API_URL}/api/video/${encodeURIComponent(linkId)}`)
  if (response.status === 410) return 'used'
  if (response.status === 404) return 'unknown'
  if (!response.ok) throw new Error(`/api/video returned ${response.status}`)
  return response.json() as Promise<VideoAccess>
}
export const fetchCrewPlan = (crews: number) => request<CrewPlan>(`/api/crew-plan?crews=${crews}`)
export const openCrewRoom = () => request<CrewRoom>('/api/crew-room', { method: 'POST' })
export const joinCrewRoomAccess = (roomId: string) => request<VideoAccess>(`/api/crew-room/${encodeURIComponent(roomId)}`)

/** Roads marked as cut; every route asked after a closure goes around it. */
export const fetchClosures = () => request<RoadClosure[]>('/api/closures')
export const closeRoad = (lon: number, lat: number) =>
  request<RoadClosure>('/api/closures', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lon, lat }),
  })
export async function reopenRoad(closureId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/closures/${encodeURIComponent(closureId)}`, inDashboardLanguage({ method: 'DELETE' }))
  if (!response.ok) throw new Error(`/api/closures/${closureId} returned ${response.status}`)
}
