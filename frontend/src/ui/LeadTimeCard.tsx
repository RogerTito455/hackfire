import type { LeadTimeView } from '../hooks/useLeadTime'
import { formatMinutes, formatSpanishTime } from './theme'

interface LeadTimeCardProps {
  view: LeadTimeView
}

// The pitch's headline number, shown once the replay reaches the moment the zone was first flagged.
export function LeadTimeCard({ view }: LeadTimeCardProps) {
  const { status, leadTime, flagged } = view
  if (status === 'loading') return <p className="empty">Loading the lead time…</p>
  if (status === 'error' || leadTime === null) {
    return <p className="empty warning">Lead time unavailable: run pnpm data:lead-time.</p>
  }
  if (!flagged) return <p className="empty">{leadTime.zone_name} has not been flagged yet.</p>

  return (
    <div className="lead">
      <p className="lead-figure">
        <strong>{formatMinutes(leadTime.minutes)}</strong> lead time
      </p>
      <p>
        {leadTime.zone_name} was flagged at {formatSpanishTime(Date.parse(leadTime.flagged_at))}, using only
        the hotspots seen up to then. In the recorded satellite data the first hotspot within{' '}
        {leadTime.radius_km} km of it came at {formatSpanishTime(Date.parse(leadTime.reached_at))}.
      </p>
      <details>
        <summary>How it is computed</summary>
        <p>{leadTime.definition}</p>
      </details>
    </div>
  )
}
