import type { RoomState } from '../domain/video'
import { Icon } from './Icon'
import { useI18n } from './i18n'

interface ShareWithCrewsPanelProps {
  available: boolean
  state: RoomState
  link: string | null
  onShare: () => void
  onStop: () => void
}

// The command post shares its map and panels, and its voice, with the fire crews (Vonage).
export function ShareWithCrewsPanel({ available, state, link, onShare, onStop }: ShareWithCrewsPanelProps) {
  const { t } = useI18n()
  if (!available) return null
  if (state === 'starting') return <p className="empty">{t('crewRoom.starting')}</p>
  if (state === 'live') {
    return (
      <div className="talk">
        <p className="talk-live">{t('crewRoom.sharing')}</p>
        {link && (
          <span className="video-link">
            {t('crewRoom.linkForCrews')}{' '}
            <a href={link} target="_blank" rel="noreferrer">
              {link}
            </a>
          </span>
        )}
        <button type="button" className="talk-hang-up icon-button" onClick={onStop}>
          <Icon name="close" size={16} />
          {t('crewRoom.stop')}
        </button>
      </div>
    )
  }
  return (
    <div className="talk">
      <button type="button" className="text-triage-send icon-button" onClick={onShare}>
        <Icon name="live" size={16} />
        {t('crewRoom.share')}
      </button>
      {state === 'error' && <p className="empty">{t('crewRoom.failed')}</p>}
    </div>
  )
}
