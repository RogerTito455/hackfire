import type { ConversationState } from '../domain/voice'
import { Icon } from './Icon'

interface AskAgentPanelProps {
  /** Whether the backend can open a conversation with the coordinator agent. */
  available: boolean
  state: ConversationState
  onAsk: () => void
  onHangUp: () => void
}

// The coordinator asks the agent by voice which rescues to do first; the map draws the route it gives.
export function AskAgentPanel({ available, state, onAsk, onHangUp }: AskAgentPanelProps) {
  if (!available) return null
  if (state === 'connecting') return <p className="empty">Connecting to the agent…</p>
  if (state === 'live') {
    return (
      <div className="talk">
        <p className="talk-live">
          You are talking to the coordinator agent. Ask: “¿Qué rescates tengo y en qué orden?”, then “Dame la ruta al
          más urgente”.
        </p>
        <button type="button" className="talk-hang-up icon-button" onClick={onHangUp}>
          <Icon name="close" size={16} />
          Hang up
        </button>
      </div>
    )
  }
  return (
    <div className="talk">
      <button type="button" className="text-triage-send icon-button" onClick={onAsk}>
        <Icon name="live" size={16} />
        Ask the coordinator agent
      </button>
      {state === 'error' && <p className="empty">Could not reach the agent. Read the queue below.</p>}
    </div>
  )
}
