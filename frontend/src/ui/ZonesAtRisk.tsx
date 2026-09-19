import { useState } from 'react'
import type { ZoneImpact } from '../domain/zones'
import type { LoadStatus } from '../hooks/useFireReplay'
import { formatMinutesToImpact, ZONE_KIND_LABEL } from './theme'

interface ZonesAtRiskProps {
  status: LoadStatus
  zones: ZoneImpact[]
  /** Whether a forecast is in force at the replay time. */
  hasForecast: boolean
}

const VISIBLE = 8

// Panel list of the places in the fire's path, soonest first.
export function ZonesAtRisk({ status, zones, hasForecast }: ZonesAtRiskProps) {
  const [expanded, setExpanded] = useState(false)

  // A failed load must not look like "no danger".
  if (status === 'loading') return <p className="empty">Loading the forecast…</p>
  if (status === 'error') return <p className="empty warning">Forecast unavailable: is the backend up and the data cached?</p>
  if (!hasForecast) return <p className="empty">No forecast at this time.</p>
  if (zones.length === 0) return <p className="empty">No zone in the predicted path.</p>

  const shown = expanded ? zones : zones.slice(0, VISIBLE)
  return (
    <>
      <ul className="zones">
        {shown.map(({ zone, minutes }) => (
          <li key={zone.id} className={minutes === 0 ? 'zone now' : 'zone'}>
            <span className="zone-name">{zone.name ?? ZONE_KIND_LABEL[zone.kind]}</span>
            <span className="zone-kind">{ZONE_KIND_LABEL[zone.kind]}</span>
            <strong className="zone-time">{formatMinutesToImpact(minutes)}</strong>
          </li>
        ))}
      </ul>
      {zones.length > VISIBLE && (
        <button type="button" className="link" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Show fewer' : `Show ${zones.length - VISIBLE} more`}
        </button>
      )}
    </>
  )
}
