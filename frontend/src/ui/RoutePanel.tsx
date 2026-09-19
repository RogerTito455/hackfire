import type { FireArea, Neighbor, Route, RouteKind } from '../domain/triage'
import type { RouteStatus } from '../hooks/useSelectedRoute'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatDistance, formatDuration, formatSpanishTime, ROUTE_KIND_ICON } from './theme'

interface RoutePanelProps {
  neighbor: Neighbor | null
  mode: RouteKind
  route: Route | null
  status: RouteStatus
  /** What the route keeps away from. */
  avoids: FireArea | null
  onModeChange: (mode: RouteKind) => void
  onClose: () => void
}

const MODES: readonly RouteKind[] = ['car', 'walking', 'rescue']

// The selected resident's way out, as the agent would read it to them, or the crew's way in.
export function RoutePanel({ neighbor, mode, route, status, avoids, onModeChange, onClose }: RoutePanelProps) {
  const { t, intl } = useI18n()
  if (neighbor === null) {
    return <p className="empty">{t('route.pick')}</p>
  }

  return (
    <div className="route-panel">
      <div className="route-head">
        <strong>{neighbor.name}</strong>
        <button type="button" className="route-close" onClick={onClose} aria-label={t('route.close')}>
          <Icon name="close" size={18} />
        </button>
      </div>
      <div className="route-modes" role="group" aria-label={t('route.modes')}>
        {MODES.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={mode === option}
            className={mode === option ? 'icon-button active' : 'icon-button'}
            onClick={() => onModeChange(option)}
          >
            <Icon name={ROUTE_KIND_ICON[option]} size={16} />
            {t(`route.${option}`)}
          </button>
        ))}
      </div>
      {status === 'loading' && <p className="empty">{t('route.planning')}</p>}
      {status === 'error' && <p className="empty">{t('route.unavailable')}</p>}
      {status === 'ready' && route !== null && (
        <>
          <p className="route-directions">“{route.spoken_directions}”</p>
          {route.distance_m !== null && route.duration_s !== null && (
            <p className="route-meta">
              <strong>
                {t('route.summary', {
                  distance: formatDistance(route.distance_m, intl),
                  duration: formatDuration(route.duration_s),
                })}
              </strong>
              {avoids !== null && (
                <span>
                  {t(avoids.properties.ahead_hours > 0 ? 'route.avoidsAhead' : 'route.avoidsBurned', {
                    count: avoids.properties.ahead_hours,
                    time: formatSpanishTime(Date.parse(avoids.properties.until), intl),
                  })}
                </span>
              )}
            </p>
          )}
        </>
      )}
    </div>
  )
}
