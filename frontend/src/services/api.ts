// Backend client. The only file that knows URLs and HTTP.

import type { Autopilot } from '../domain/autopilot'
import type { HotspotCollection } from '../domain/hotspots'
import type { EvacuationOrder, OrderDecision, SafePoint } from '../domain/orders'
import type { LeadTime } from '../domain/leadTime'
import type { LiveFireCollection } from '../domain/liveFires'
import type { LiveSpreadResponse } from '../domain/liveSpread'
import type { LiveOperationsResponse } from '../domain/liveOperations'
import type { DgtOverviewResponse } from '../domain/liveDgt'
import type { SpreadCollection } from '../domain/spread'
import type { TextClassification } from '../domain/textTriage'
import type { AgentFocus, CrewAlert, FireArea, Neighbor, Rescue, Route, TravelMode, TriageStatus } from '../domain/triage'
import type { ImpactTable, ZoneCollection } from '../domain/zones'
import type { CampaignCall, VoiceCapabilities, WebSession } from '../domain/voice'
import type { CrewRoom, RescueVideo, RescueVideoLink, VideoAccess, VideoCapabilities } from '../domain/video'
import type { CrewPlan } from '../domain/crewPlan'
import type { RoadClosure } from '../domain/closures'
import type { AuditEvent, ProviderStatus } from '../domain/operations'
import type { Scenario } from '../domain/scenario'

// The API is on the dashboard's own origin: deployed, the backend serves the dashboard, and under
// `pnpm dev:web` Vite proxies the API paths to the backend (vite.config.ts). VITE_API_URL points a
// local dashboard at another backend instead.
const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

// Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: no request waits forever. An
// AbortController rather than AbortSignal.timeout, which iOS before 16 (a crew's phone) lacks.
const REQUEST_TIMEOUT_MS = 30000

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } catch (error) {
    // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a timeout says so, rather
    // than surfacing as a bare AbortError.
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`no answer in ${REQUEST_TIMEOUT_MS / 1000} seconds`, { cause: error })
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}

// The backend writes some sentences itself (route directions, orders, crew alerts): every request
// asks for them in the dashboard's language, which the i18n provider keeps in <html lang>.
function inDashboardLanguage(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers)
  headers.set('Accept-Language', document.documentElement.lang || 'en')
  return { ...init, headers }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a network failure names the
    // path. It is not logged here: the dashboard polls a dozen endpoints every few seconds, so each
    // caller decides what to say when the backend is down (see useClosures, useCrewPlan, useTriage).
    response = await fetchWithTimeout(`${API_URL}${path}`, inDashboardLanguage(init))
  } catch (error) {
    throw new Error(`${path} could not be reached`, { cause: error })
  }
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
/** Official DGT forest-fire incidents and road closures across Spain. */
export const fetchLiveDgt = () => request<DgtOverviewResponse>('/api/live/dgt')
/** Where the fire's alert drafts download as one CAP 1.2 document (status Draft). A plain link. */
export const liveOperationsCapUrl = (fireId: string) => `${API_URL}/api/live/operations/${encodeURIComponent(fireId)}/cap`
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
  request<Neighbor>('/tools/report_status?via=dashboard', {
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
  let response: Response
  try {
    // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a network failure names the path.
    response = await fetchWithTimeout(`${API_URL}/api/video/${encodeURIComponent(linkId)}`)
  } catch (error) {
    throw new Error('/api/video could not be reached', { cause: error })
  }
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
  let response: Response
  try {
    // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a network failure is logged here, then passed on.
    response = await fetchWithTimeout(`${API_URL}/api/closures/${encodeURIComponent(closureId)}`, inDashboardLanguage({ method: 'DELETE' }))
  } catch (error) {
    console.error(`Reopening road ${closureId} failed`, error)
    throw error
  }
  if (!response.ok) throw new Error(`/api/closures/${closureId} returned ${response.status}`)
}

/** The activity log's newest events, each already a sentence in the dashboard's language. */
export const fetchAudit = (limit: number) => request<AuditEvent[]>(`/api/audit?limit=${limit}`)
/** A plain link downloads the whole run as JSON; it names the language, since a link sends no header. */
export const auditDownloadUrl = (locale: string) => `${API_URL}/api/audit/export?lang=${encodeURIComponent(locale)}`
/** Whether each external service answers; the backend checks at most about once a minute. */
export const fetchProviderStatus = () => request<ProviderStatus[]>('/api/status/providers')
