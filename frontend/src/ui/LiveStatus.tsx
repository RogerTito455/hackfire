import type { LiveMode } from '../hooks/useLiveFires'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatSpanishTime } from './theme'

// Status bar for live mode. A Deepfire outage shows up here as a message, never as a broken map.
export function LiveStatus({ status, data }: LiveMode) {
  const { t, intl } = useI18n()
  if (data === null) {
    return (
      <div className="replay">
        {status === 'error' ? t('live.down') : t('live.loading')}
      </div>
    )
  }

  const time = formatSpanishTime(data.fetchedAt, intl)
  const note = t(status === 'error' ? 'live.refreshFailed' : data.stale ? 'live.busy' : 'live.updated', { time })

  return (
    <div className="replay">
      <div className="replay-body">
        <div className="replay-head">
          <strong className="icon-button">
            <Icon name="satellite" size={16} />
            {t('live.clusters', { count: data.fires.length })}
          </strong>
        </div>
        <div className={status === 'error' || data.stale ? 'live-note warn' : 'live-note'}>{note}</div>
      </div>
    </div>
  )
}
