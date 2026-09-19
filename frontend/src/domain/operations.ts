// The audit log and the provider status (backend/app/audit.py, provider_status.py). Plain data.

import type { TriageStatus } from './triage'

/** One decision or outcome, newest first from GET /api/audit. Never carries a phone number. */
export interface AuditEvent {
  id: string
  at: string
  /** Such as order.approved, status.reported, closure.added, demo.reset. */
  action: string
  actor: 'coordinator' | 'agent' | 'autopilot' | 'system' | string
  /** Where a status came from: agent_tool, typed_answer, manual_button, autopilot, safety_net, campaign. */
  source: string | null
  subject: string | null
  values: Record<string, string | number | boolean | null>
  /** The sentence, already in the dashboard's language. */
  message: string
}

export type ProviderState = 'up' | 'degraded' | 'down' | 'configured' | 'not_configured'

export interface ProviderStatus {
  id: string
  name: string
  state: ProviderState
  reason: string
  /** null until the first check has answered. */
  checked_at: string | null
}

/** What an event is about, for its icon: the part of the action before the dot. */
export function auditKind(event: AuditEvent): string {
  return event.action.split('.')[0]
}

/** The triage status a status report set, if the event is one. */
export function reportedStatus(event: AuditEvent): TriageStatus | null {
  const status = event.values.status
  return event.action === 'status.reported' && typeof status === 'string' ? (status as TriageStatus) : null
}
