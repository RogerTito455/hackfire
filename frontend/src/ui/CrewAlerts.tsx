import type { CrewAlert } from '../domain/triage'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatClock } from './theme'

interface CrewAlertsProps {
  alerts: CrewAlert[]
  onShowRoute: (neighborId: string) => void
}

// What the fire crew is told for every new rescue. Until SMS is wired, the dashboard is the channel.
export function CrewAlerts({ alerts, onShowRoute }: CrewAlertsProps) {
  const { t, intl } = useI18n()
  if (alerts.length === 0) return <p className="empty">{t('alerts.empty')}</p>

  return (
    <ol className="alerts">
      {alerts.map((alert) => (
        <li key={`${alert.rescue_id}-${alert.created_at}`}>
          <span className="alert-meta icon-button">
            <Icon name="bell" size={14} />
            <time dateTime={alert.created_at}>{formatClock(alert.created_at, intl)}</time>
            {alert.sent_by_sms ? t('alerts.sms') : t('alerts.dashboardOnly')}
          </span>
          <span>{alert.message}</span>
          <button type="button" className="alert-route icon-button" onClick={() => onShowRoute(alert.neighbor_id)}>
            <Icon name="fire-truck" size={16} />
            {t('alerts.showRoute')}
          </button>
        </li>
      ))}
    </ol>
  )
}
