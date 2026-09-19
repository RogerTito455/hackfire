import { useState } from 'react'
import type { ZoneImpact } from '../domain/zones'
import type { LoadStatus } from '../hooks/useFireReplay'
import { useI18n } from './i18n'
import { formatMinutesToImpact } from './theme'

interface ZonesAtRiskProps {
  status: LoadStatus
  zones: ZoneImpact[]
  /** Whether a forecast is in force at the replay time. */
  hasForecast: boolean
}

const VISIBLE = 8

// Panel list of the places in the fire's path, soonest first.
export function ZonesAtRisk({ status, zones, hasForecast }: ZonesAtRiskProps) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)

  // A failed load must not look like "no danger".
  if (status === 'loading') return <p className="empty">{t('fire.loading')}</p>
  if (status === 'error') return <p className="empty warning">{t('fire.error')}</p>
  if (!hasForecast) return <p className="empty">{t('fire.noForecast')}</p>
  if (zones.length === 0) return <p className="empty">{t('fire.noZones')}</p>

  const shown = expanded ? zones : zones.slice(0, VISIBLE)
  return (
    <>
      <ul className="zones">
        {shown.map(({ zone, minutes }) => (
          <li key={zone.id} className={minutes === 0 ? 'zone now' : 'zone'}>
            <span className="zone-name">{zone.name ?? t(`zoneKind.${zone.kind}`)}</span>
            <span className="zone-kind">{t(`zoneKind.${zone.kind}`)}</span>
            <strong className="zone-time">{formatMinutesToImpact(minutes, t('time.now'))}</strong>
          </li>
        ))}
      </ul>
      {zones.length > VISIBLE && (
        <button type="button" className="link" onClick={() => setExpanded(!expanded)}>
          {expanded ? t('fire.showFewer') : t('fire.showMore', { count: zones.length - VISIBLE })}
        </button>
      )}
    </>
  )
}
