import { auditKind, reportedStatus, type AuditEvent } from '../domain/operations'
import { safeHref } from '../domain/url'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { AUDIT_ICON, STATUS_COLOR, STATUS_ICON, formatClock } from './theme'

interface ActivityLogProps {
  events: AuditEvent[]
  loaded: boolean
  failed: boolean
  downloadUrl: string
}

// The latest decisions and outcomes, newest first, and the whole run as a JSON download.
export function ActivityLog({ events, loaded, failed, downloadUrl }: ActivityLogProps) {
  const { t, intl } = useI18n()
  return (
    <>
      {failed && events.length === 0 && <p className="empty">{t('audit.unavailable')}</p>}
      {loaded && events.length === 0 && <p className="empty">{t('audit.empty')}</p>}
      {events.length > 0 && (
        <ol className="activity">
          {events.map((event) => {
            const status = reportedStatus(event)
            const icon = status ? STATUS_ICON[status] : AUDIT_ICON[auditKind(event)] ?? 'flag'
            return (
              <li key={event.id}>
                <span className="activity-icon" style={status ? { color: STATUS_COLOR[status] } : undefined}>
                  <Icon name={icon} size={16} />
                </span>
                <time className="activity-time" dateTime={event.at}>
                  {formatClock(event.at, intl)}
                </time>
                <span className="activity-message">{event.message}</span>
              </li>
            )
          })}
        </ol>
      )}
      {/* Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a link that is not http, https or mailto becomes '#'. */}
      <a className="activity-download" href={safeHref(downloadUrl) ?? '#'} download>
        {t('audit.download')}
      </a>
    </>
  )
}
