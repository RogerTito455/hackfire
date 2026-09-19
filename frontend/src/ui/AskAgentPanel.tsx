import type { ConversationState } from '../domain/voice'
import { useI18n } from './i18n'
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
  const { t } = useI18n()
  if (!available) return null
  if (state === 'connecting') return <p className="empty">{t('ask.connecting')}</p>
  if (state === 'live') {
    return (
      <div className="talk">
        <p className="talk-live">{t('ask.onTheLine')}</p>
        <button type="button" className="talk-hang-up icon-button" onClick={onHangUp}>
          <Icon name="close" size={16} />
          {t('ask.hangUp')}
        </button>
      </div>
    )
  }
  return (
    <div className="talk">
      <button type="button" className="text-triage-send icon-button" onClick={onAsk}>
        <Icon name="live" size={16} />
        {t('ask.ask')}
      </button>
      {state === 'error' && <p className="empty">{t('ask.failed')}</p>}
    </div>
  )
}
