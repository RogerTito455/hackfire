import type { CrewAlert } from '../domain/triage'
import { formatClock } from './theme'

interface CrewAlertsProps {
  alerts: CrewAlert[]
  onShowRoute: (neighborId: string) => void
}

// What the fire crew is told for every new rescue. Until SMS is wired, the dashboard is the channel.
export function CrewAlerts({ alerts, onShowRoute }: CrewAlertsProps) {
  if (alerts.length === 0) return <p className="empty">No alerts sent to the crew yet.</p>

  return (
    <ol className="alerts">
      {alerts.map((alert) => (
        <li key={`${alert.rescue_id}-${alert.created_at}`}>
          <span className="alert-meta">
            {formatClock(alert.created_at)} · {alert.sent_by_sms ? 'sent by SMS' : 'dashboard only, SMS not set up'}
          </span>
          <span>{alert.message}</span>
          <button type="button" className="alert-route" onClick={() => onShowRoute(alert.neighbor_id)}>
            Show crew route
          </button>
        </li>
      ))}
    </ol>
  )
}
