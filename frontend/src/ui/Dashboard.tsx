import type { Triage } from '../hooks/useTriage'
import { RescueQueue } from './RescueQueue'
import { StatusCounts } from './StatusCounts'
import { TriageMap } from './TriageMap'
import './dashboard.css'

// Presentation only: everything arrives through props, nothing is fetched here.
export function Dashboard({ neighbors, rescues, counts, online, reset }: Triage) {
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
      <TriageMap neighbors={neighbors} />
    </div>
  )
}
