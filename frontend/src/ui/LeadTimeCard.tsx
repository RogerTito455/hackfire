import type { LeadTimeView } from '../hooks/useLeadTime'
import { useI18n } from './i18n'
import { formatMinutes, formatSpanishTime } from './theme'

interface LeadTimeCardProps {
  view: LeadTimeView
}

// The pitch's headline number, shown once the replay reaches the moment the zone was first flagged.
export function LeadTimeCard({ view }: LeadTimeCardProps) {
  const { t, intl } = useI18n()
  const { status, leadTime, flagged } = view
  if (status === 'loading') return <p className="empty">{t('leadTime.loading')}</p>
  if (status === 'error' || leadTime === null) {
    return <p className="empty warning">{t('leadTime.error')}</p>
  }
  if (!flagged) return <p className="empty">{t('leadTime.notFlagged', { zone: leadTime.zone_name })}</p>

  return (
    <div className="lead">
      <p className="lead-figure">
        <strong>{t('leadTime.approx', { count: Math.round(leadTime.minutes / 60) })}</strong> {t('leadTime.label')}
      </p>
      <p className="lead-range">{t('leadTime.range', { exact: formatMinutes(leadTime.minutes) })}</p>
      <p>
        {t('leadTime.explanation', {
          zone: leadTime.zone_name,
          flagged: formatSpanishTime(Date.parse(leadTime.flagged_at), intl),
          radius: leadTime.radius_km,
          reached: formatSpanishTime(Date.parse(leadTime.reached_at), intl),
        })}
      </p>
      <details>
        <summary>{t('leadTime.how')}</summary>
        <p>{leadTime.definition}</p>
      </details>
    </div>
  )
}
