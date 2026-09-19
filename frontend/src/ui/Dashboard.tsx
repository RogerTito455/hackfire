import type { FireReplay } from '../hooks/useFireReplay'
import type { LiveMode } from '../hooks/useLiveFires'
import type { MapMode } from '../hooks/useMapMode'
import type { SelectedRoute } from '../hooks/useSelectedRoute'
import type { Triage } from '../hooks/useTriage'
import { LiveStatus } from './LiveStatus'
import { CrewAlerts } from './CrewAlerts'
import { ModeToggle } from './ModeToggle'
import { ReplayControls } from './ReplayControls'
import { RescueQueue } from './RescueQueue'
import { RoutePanel } from './RoutePanel'
import { StatusCounts } from './StatusCounts'
import { TriageMap } from './TriageMap'
import './dashboard.css'

interface DashboardProps {
  triage: Triage
  replay: FireReplay
  mode: MapMode
  onModeChange: (mode: MapMode) => void
  live: LiveMode
  selection: SelectedRoute
}

// Presentation only: everything arrives through props, nothing is fetched here.
export function Dashboard({ triage, replay, mode, onModeChange, live, selection }: DashboardProps) {
  const { neighbors, rescues, alerts, counts, online, reset } = triage
  const selected = neighbors.find((neighbor) => neighbor.id === selection.neighborId) ?? null
  return (
    <div className="layout">
      <aside className="panel">
        <header>
          <h1>HackFire</h1>
          <p className={online ? 'conn ok' : 'conn down'}>
            {online ? 'Backend connected' : 'Backend unreachable'}
          </p>
        </header>

        <section>
          <h2>Triage</h2>
          <StatusCounts counts={counts} />
        </section>

        <section>
          <h2>Evacuation route</h2>
          <RoutePanel
            neighbor={selected}
            mode={selection.mode}
            route={selection.route}
            status={selection.status}
            avoidsUntil={selection.fireArea?.properties.until ?? null}
            onModeChange={selection.setMode}
            onClose={() => selection.select(null)}
          />
        </section>

        <section>
          <h2>Rescue queue</h2>
          <RescueQueue rescues={rescues} />
        </section>

        <section>
          <h2>Crew alerts</h2>
          <CrewAlerts
            alerts={alerts}
            onShowRoute={(neighborId) => {
              onModeChange('replay')
              selection.showRescue(neighborId)
            }}
          />
        </section>

        <button type="button" className="reset" onClick={reset}>
          Reset demo
        </button>
      </aside>
      <div className="map-area">
        <TriageMap
          mode={mode}
          neighbors={neighbors}
          hotspots={replay.hotspots}
          time={replay.time}
          live={live.data}
          selectedNeighborId={selection.neighborId}
          route={selection.route}
          fireArea={selection.fireArea}
          onSelectNeighbor={selection.select}
        />
        <ModeToggle mode={mode} onChange={onModeChange} />
        {mode === 'replay' ? (
          <ReplayControls
            status={replay.status}
            range={replay.range}
            time={replay.time}
            observedCount={replay.observedCount}
            playing={replay.playing}
            onTimeChange={replay.setTime}
            onTogglePlay={replay.togglePlay}
          />
        ) : (
          <LiveStatus {...live} />
        )}
      </div>
    </div>
  )
}
