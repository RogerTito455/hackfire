import type { FireReplay } from '../hooks/useFireReplay'
import type { Triage } from '../hooks/useTriage'
import { ReplayControls } from './ReplayControls'
import { RescueQueue } from './RescueQueue'
import { StatusCounts } from './StatusCounts'
import { TriageMap } from './TriageMap'
import './dashboard.css'

interface DashboardProps {
  triage: Triage
  replay: FireReplay
}

// Presentation only: everything arrives through props, nothing is fetched here.
export function Dashboard({ triage, replay }: DashboardProps) {
  const { neighbors, rescues, counts, online, reset } = triage
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
          <h2>Rescue queue</h2>
          <RescueQueue rescues={rescues} />
        </section>

        <button type="button" className="reset" onClick={reset}>
          Reset demo
        </button>
      </aside>
      <div className="map-area">
        <TriageMap neighbors={neighbors} hotspots={replay.hotspots} time={replay.time} />
        <ReplayControls
          status={replay.status}
          range={replay.range}
          time={replay.time}
          observedCount={replay.observedCount}
          playing={replay.playing}
          onTimeChange={replay.setTime}
          onTogglePlay={replay.togglePlay}
        />
      </div>
    </div>
  )
}
