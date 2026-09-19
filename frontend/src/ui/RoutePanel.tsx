import type { FireArea, Neighbor, Route, RouteKind } from '../domain/triage'
import type { RouteStatus } from '../hooks/useSelectedRoute'
import { Icon } from './Icon'
import { formatDistance, formatDuration, formatSpanishTime, ROUTE_KIND_ICON, ROUTE_KIND_LABEL } from './theme'

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
  if (neighbor === null) {
    return <p className="empty">Click a resident on the map to see their route out.</p>
  }

  return (
    <div className="route-panel">
      <div className="route-head">
        <strong>{neighbor.name}</strong>
        <button type="button" className="route-close" onClick={onClose} aria-label="Close route">
          <Icon name="close" size={18} />
        </button>
      </div>
      <div className="route-modes" role="group" aria-label="Travel mode">
        {MODES.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={mode === option}
            className={mode === option ? 'icon-button active' : 'icon-button'}
            onClick={() => onModeChange(option)}
          >
            <Icon name={ROUTE_KIND_ICON[option]} size={16} />
            {ROUTE_KIND_LABEL[option]}
          </button>
        ))}
      </div>
      {status === 'loading' && <p className="empty">Planning the route…</p>}
      {status === 'error' && <p className="empty">Routing is unavailable right now.</p>}
      {status === 'ready' && route !== null && (
        <>
          <p className="route-directions">“{route.spoken_directions}”</p>
          {route.distance_m !== null && route.duration_s !== null && (
            <p className="route-meta">
              {formatDistance(route.distance_m)} · {formatDuration(route.duration_s)}
              {avoids !== null && (
                <>
                  {' · '}
                  {avoids.properties.ahead_hours > 0
                    ? `avoids the fire and its next ${avoids.properties.ahead_hours} h of predicted spread`
                    : 'avoids the area already burned'}
                  {`, as of ${formatSpanishTime(Date.parse(avoids.properties.until))}`}
                </>
              )}
            </p>
          )}
        </>
      )}
    </div>
  )
}
