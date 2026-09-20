import { spreadModels, type LiveSpread } from '../domain/liveSpread'
import type { LiveMode } from '../hooks/useLiveFires'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatSpanishTime, SPREAD_HOUR_COLORS, spreadModelLabel } from './theme'

// Status bar for live mode. A Deepfire outage shows up here as a message, never as a broken map.
export function LiveStatus({ status, data, spread }: LiveMode) {
  const { t, intl } = useI18n()
  if (data === null) {
    return (
      <div className="replay">
        {status === 'error' ? t('live.down') : t('live.loading')}
      </div>
    )
  }

  const time = formatSpanishTime(data.fetchedAt, intl)
  // Norma js-nested-ternary: one locale key chosen from three, already named and on its own line.
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
        {spread !== null && <SpreadLine spread={spread} />}
      </div>
    </div>
  )
}

// What the warm areas around the fires are: Deepfire's own simulations, drawn with the replay's ramp.
function SpreadLine({ spread }: { spread: LiveSpread }) {
  const { t } = useI18n()
  const gradient = SPREAD_HOUR_COLORS.map(([, color]) => color).join(', ')
  const count = spread.fires.length
  const models = spreadModels(spread).map(spreadModelLabel).join(', ')
  return (
    <div className="live-spread">
      {count > 0 && (
        <span className="replay-ramp" aria-hidden="true" style={{ background: `linear-gradient(to right, ${gradient})` }} />
      )}
      <span>{count > 0 ? t('live.spread', { count, models }) : t('live.spreadNone')}</span>
    </div>
  )
}
