import type { Neighbor } from '../domain/triage'
import type { ConversationState } from '../domain/voice'
import { Icon } from './Icon'

interface TalkPanelProps {
  neighbor: Neighbor
  /** Whether the backend can open a browser conversation with the agent. */
  available: boolean
  /** Whether the resident's zone has an approved order: nobody is called without one. */
  orderApproved: boolean
  zoneName: string
  /** The resident the agent is talking to, if any, and how that is going. */
  activeId: string | null
  state: ConversationState
  onTalk: () => void
  onHangUp: () => void
}

// No phone can ring: the resident agent calls this laptop, and someone answers as the resident.
export function TalkPanel({ neighbor, available, orderApproved, zoneName, activeId, state, onTalk, onHangUp }: TalkPanelProps) {
  if (!available) return <p className="empty">The voice agent is not configured (SLNG_API_KEY).</p>
  if (!orderApproved) {
    return (
      <p className="empty warning">
        {zoneName}'s order is not approved: approve it under Evacuation orders, then call {neighbor.name}.
      </p>
    )
  }

  const mine = activeId === neighbor.id
  if (mine && state === 'connecting') return <p className="empty">Connecting to the agent…</p>
  if (mine && state === 'live') {
    return (
      <div className="talk">
        <p className="talk-live">The resident agent is calling {neighbor.name}: answer as them.</p>
        <button type="button" className="talk-hang-up icon-button" onClick={onHangUp}>
          <Icon name="close" size={16} />
          Hang up
        </button>
      </div>
    )
  }
  return (
    <div className="talk">
      <button type="button" className="text-triage-send icon-button" disabled={state === 'connecting'} onClick={onTalk}>
        <Icon name="live" size={16} />
        Call {neighbor.name} (answer here)
      </button>
      {mine && state === 'error' && <p className="empty">Could not reach the agent. Use the typed answer below.</p>}
    </div>
  )
}
