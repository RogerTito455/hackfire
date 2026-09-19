import type { Rescue } from '../domain/triage'

interface RescueQueueProps {
  rescues: Rescue[]
}

export function RescueQueue({ rescues }: RescueQueueProps) {
  if (rescues.length === 0) return <p className="empty">No rescues pending.</p>

  return (
    <ol className="rescues">
      {rescues.map((rescue) => (
        <li key={rescue.rescue_id}>
          <strong>{rescue.neighbor.name}</strong>
          <span>{rescue.neighbor.address}</span>
          <span>
            {rescue.neighbor.people ?? '?'} people · {rescue.neighbor.mobility ?? 'mobility unknown'}
          </span>
          {rescue.minutes_to_impact !== null && (
            <span className="impact">~{rescue.minutes_to_impact} min to impact</span>
          )}
        </li>
      ))}
    </ol>
  )
}
