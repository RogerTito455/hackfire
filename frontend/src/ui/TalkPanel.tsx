import type { Neighbor } from '../domain/triage'
import type { ConversationState } from '../domain/voice'
import { Icon } from './Icon'

interface TalkPanelProps {
  neighbor: Neighbor
  /** Whether the backend can open a browser conversation with the agent. */
  available: boolean
  /** Whether the resident's zone has an approved order: nobody is called without one. */
  orderApproved: boolean
  /** The resident the agent is talking to, if any, and how that is going. */
  activeId: string | null
  state: ConversationState
  onTalk: () => void
  onHangUp: () => void
}

// No phone can ring: the coordinator's laptop takes the call, and someone answers as the resident.
export function TalkPanel({ neighbor, available, orderApproved, activeId, state, onTalk, onHangUp }: TalkPanelProps) {
  if (!available) return <p className="empty">The voice agent is not configured (SLNG_API_KEY).</p>
  if (!orderApproved) return <p className="empty">Approve the order for this resident's zone before calling them.</p>

  const mine = activeId === neighbor.id
  if (mine && state === 'connecting') return <p className="empty">Connecting to the agent…</p>
  if (mine && state === 'live') {
    return (
      <div className="talk">
        <p className="talk-live">The agent is on the line. Answer as {neighbor.name}.</p>
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
        Take {neighbor.name}'s call here
      </button>
      {mine && state === 'error' && <p className="empty">Could not reach the agent. Use the typed answer below.</p>}
    </div>
  )
}
