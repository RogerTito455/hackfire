// The voice agent as the dashboard starts it: phone campaigns and browser conversations (#8).
// Types only. No React, no fetch, no styling.

/** What the backend can start: phone calls need a SIP trunk; browser conversations only SLNG. */
export interface VoiceCapabilities {
  phone_calls: boolean
  web_sessions: boolean
  /** The coordinator agent (#10) can be asked from the dashboard. */
  coordinator: boolean
}

/** One resident's call in a campaign. Never carries the phone number. */
export interface CampaignCall {
  neighbor_id: string
  /** null when SLNG refused to place the call; the resident is then no_answer. */
  call_id: string | null
}

/** What pressing "Call residents" for a zone did, or null counts when the calls could not start. */
export interface CampaignResult {
  zone: string
  placed: number | null
  refused: number | null
}

export function campaignResult(zone: string, calls: readonly CampaignCall[]): CampaignResult {
  const placed = calls.filter((call) => call.call_id !== null).length
  return { zone, placed, refused: calls.length - placed }
}

/** A browser conversation with the agent: LiveKit's room URL and a short-lived token. */
export interface WebSession {
  call_id: string
  livekit_url: string
  livekit_token: string
  max_session_seconds: number
}

export type ConversationState = 'idle' | 'connecting' | 'live' | 'error'
