import { compass, reachedCount, upcomingZones, type ZoneRiskList } from '../domain/spread'
import type { SpreadStatus } from '../hooks/useSpread'
import { Icon } from './Icon'
import { formatImpact, ZONE_KIND_LABEL, ZONE_RISK_COLORS } from './theme'

interface ZonesPanelProps {
  status: SpreadStatus
  risk: ZoneRiskList | null
  motion: { bearing_deg: number; speed_km_h: number } | null
  /** Replay mode only: live fires have no prediction here. */
  enabled: boolean
}

const SHOWN = 5

function riskColor(minutes: number): string {
  const band = ZONE_RISK_COLORS.find(([limit]) => minutes <= limit) ?? ZONE_RISK_COLORS[ZONE_RISK_COLORS.length - 1]
  return band[1]
}

// Step 2 of the plan: which places the fire is heading for, and how soon, at the replay time.
export function ZonesPanel({ status, risk, motion, enabled }: ZonesPanelProps) {
  if (!enabled) return <p className="empty">The prediction is shown in replay mode.</p>
  if (risk === null) {
    return <p className="empty">{status === 'error' ? 'Prediction unavailable.' : 'Predicting the spread…'}</p>
  }

  const zones = upcomingZones(risk)
  const reached = reachedCount(risk)
  return (
    <div className="zones">
      <p className="zones-motion">
        <Icon name="flame" size={16} />
        {motion
          ? `Front moving ${compass(motion.bearing_deg)} at ${motion.speed_km_h.toFixed(1)} km/h`
          : 'No clear direction of spread at this time'}
      </p>
      {zones.length === 0 ? (
        <p className="empty">No other place in the fire's path within 6 hours.</p>
      ) : (
        <ol className="zone-list">
          {zones.slice(0, SHOWN).map((zone) => (
            <li key={zone.id} style={{ borderLeftColor: riskColor(zone.minutes_to_impact ?? 0) }}>
              <span>
                <strong>{zone.name}</strong>
                <span className="zone-kind">{ZONE_KIND_LABEL[zone.kind]}</span>
              </span>
              <span className="zone-impact">{formatImpact(zone.minutes_to_impact ?? 0)}</span>
            </li>
          ))}
        </ol>
      )}
      {zones.length > SHOWN && <p className="empty">and {zones.length - SHOWN} more on the map</p>}
      {reached > 0 && (
        <p className="empty">
          {reached} {reached === 1 ? 'place' : 'places'} already reached, in dark red on the map
        </p>
      )}
    </div>
  )
}
