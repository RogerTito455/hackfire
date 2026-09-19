import { TRIAGE_STATUSES, type StatusCounts as Counts } from '../domain/triage'
import { STATUS_COLOR, STATUS_LABEL } from './theme'

interface StatusCountsProps {
  counts: Counts
}

export function StatusCounts({ counts }: StatusCountsProps) {
  return (
    <ul className="counts">
      {TRIAGE_STATUSES.map((status) => (
        <li key={status}>
          <span className="dot" style={{ background: STATUS_COLOR[status] }} />
          {STATUS_LABEL[status]}
          <strong>{counts[status]}</strong>
        </li>
      ))}
    </ul>
  )
}
