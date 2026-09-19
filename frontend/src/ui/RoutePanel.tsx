import type { Neighbor, Route, RouteKind } from '../domain/triage'
import type { RouteStatus } from '../hooks/useSelectedRoute'
import { formatDistance, formatDuration, formatSpanishTime, ROUTE_KIND_LABEL } from './theme'

interface RoutePanelProps {
  neighbor: Neighbor | null
  mode: RouteKind
  route: Route | null
  status: RouteStatus
  /** ISO time the avoided fire area runs up to. */
  avoidsUntil: string | null
  onModeChange: (mode: RouteKind) => void
  onClose: () => void
}

const MODES: readonly RouteKind[] = ['car', 'walking', 'rescue']

// The selected resident's way out, as the agent would read it to them, or the crew's way in.
export function RoutePanel({ neighbor, mode, route, status, avoidsUntil, onModeChange, onClose }: RoutePanelProps) {
  if (neighbor === null) {
    return <p className="empty">Click a resident on the map to see their route out.</p>
  }

  return (
    <div className="route-panel">
      <div className="route-head">
        <strong>{neighbor.name}</strong>
        <button type="button" className="route-close" onClick={onClose} aria-label="Close route">
          ×
        </button>
      </div>
      <div className="route-modes" role="group" aria-label="Travel mode">
        {MODES.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={mode === option}
            className={mode === option ? 'active' : ''}
            onClick={() => onModeChange(option)}
          >
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
              {avoidsUntil !== null && <> · avoids the area burned by {formatSpanishTime(Date.parse(avoidsUntil))}</>}
            </p>
          )}
        </>
      )}
    </div>
  )
}
