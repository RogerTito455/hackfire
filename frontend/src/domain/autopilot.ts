// The demo autopilot: a labelled simulation of the coordinator's workflow along the replay, with the
// demo residents (backend/app/autopilot.py). Types and pure functions only. No React, no fetch, no styling.

import type { TriageStatus } from './triage'

export type Speaker = 'agent' | 'resident'

export interface AutopilotTurn {
  speaker: Speaker
  text: string
}

/** A real call of the resident agent with a resident simulated by Galtea (data/demo_calls.json). */
export interface AutopilotTranscript {
  scenario: string
  /** The last status the agent recorded with report_status. */
  status: TriageStatus
  turns: AutopilotTurn[]
}

/** A scripted outcome on the replay clock, and the transcript shown with it. */
export interface AutopilotCall {
  neighbor_id: string
  at: string
  status: TriageStatus
  transcript: string | null
}

export interface Autopilot {
  enabled: boolean
  /** While it is on: every scripted outcome, oldest first. */
  calls: AutopilotCall[]
  transcripts: Record<string, AutopilotTranscript>
}

export const AUTOPILOT_OFF: Autopilot = { enabled: false, calls: [], transcripts: {} }

/** The newest scripted call with a transcript that has landed by `time` (epoch ms), or null. */
export function latestRecordedCall(autopilot: Autopilot, time: number | null): AutopilotCall | null {
  if (!autopilot.enabled || time === null) return null
  let latest: AutopilotCall | null = null
  for (const call of autopilot.calls) {
    if (Date.parse(call.at) > time) break
    if (call.transcript !== null && call.transcript in autopilot.transcripts) latest = call
  }
  return latest
}

/** A key that changes whenever a different call lands, so its transcript starts typing again. */
export function callKey(call: AutopilotCall): string {
  return `${call.neighbor_id}@${call.at}`
}
