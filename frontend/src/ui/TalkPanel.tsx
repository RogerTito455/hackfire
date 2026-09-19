import type { EvacuationOrder } from '../domain/orders'
import type { Neighbor } from '../domain/triage'
import type { ConversationState } from '../domain/voice'
import { useI18n } from './i18n'
import { Icon } from './Icon'

interface TalkPanelProps {
  neighbor: Neighbor
  /** Whether the backend can open a browser conversation with the agent. */
  available: boolean
  /** The resident's zone order: nobody is called before it is approved. */
  order: EvacuationOrder | undefined
  /** The resident the agent is talking to, if any, and how that is going. */
  activeId: string | null
  state: ConversationState
  onTalk: () => void
  onHangUp: () => void
}

// No phone can ring: the resident agent calls this laptop, and someone answers as the resident.
export function TalkPanel({
  neighbor,
  available,
  order,
  activeId,
  state,
  onTalk,
  onHangUp,
}: TalkPanelProps) {
  const { t } = useI18n()
  if (!available) return <p className="empty">{t('talk.notConfigured')}</p>
  if (!order?.approved) {
    return (
      <p className="empty warning">
        {t('talk.approveFirst', { zone: order?.zone_name ?? neighbor.zone, name: neighbor.name })}
      </p>
    )
  }

  const mine = activeId === neighbor.id
  if (mine && state === 'connecting') return <p className="empty">{t('talk.connecting')}</p>
  if (mine && state === 'live') {
    return (
      <div className="talk">
        <p className="talk-live">{t('talk.onTheLine', { name: neighbor.name })}</p>
        <button type="button" className="talk-hang-up icon-button" onClick={onHangUp}>
          <Icon name="close" size={16} />
          {t('talk.hangUp')}
        </button>
      </div>
    )
  }
  return (
    <div className="talk">
      <button type="button" className="text-triage-send icon-button" disabled={state === 'connecting'} onClick={onTalk}>
        <Icon name="live" size={16} />
        {t('talk.take', { name: neighbor.name })}
      </button>
      {mine && state === 'error' && <p className="empty">{t('talk.failed')}</p>}
    </div>
  )
}
