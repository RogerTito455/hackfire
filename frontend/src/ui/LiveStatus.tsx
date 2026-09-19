import type { LiveMode } from '../hooks/useLiveFires'
import { formatSpanishTime } from './theme'

// Status bar for live mode. A Deepfire outage shows up here as a message, never as a broken map.
export function LiveStatus({ status, data }: LiveMode) {
  if (data === null) {
    return (
      <div className="replay">
        {status === 'error'
          ? 'Deepfire is unavailable right now. The replay still works.'
          : 'Loading the fires burning now…'}
      </div>
    )
  }

  const updated = formatSpanishTime(data.fetchedAt)
  const note =
    status === 'error'
      ? `Could not refresh; showing data from ${updated}.`
      : data.stale
        ? `Deepfire is busy; showing data from ${updated}.`
        : `Updated ${updated}. Source: Deepfire.`

  return (
    <div className="replay">
      <div className="replay-body">
        <div className="replay-head">
          <strong>{data.fires.length.toLocaleString('en-GB')} active fire clusters on this map</strong>
        </div>
        <div className={status === 'error' || data.stale ? 'live-note warn' : 'live-note'}>{note}</div>
      </div>
    </div>
  )
}
