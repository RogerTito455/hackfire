import { TRIAGE_STATUSES, type StatusCounts as Counts } from '../domain/triage'
import { Icon } from './Icon'
import { STATUS_COLOR, STATUS_ICON, STATUS_LABEL } from './theme'

interface StatusCountsProps {
  counts: Counts
}

export function StatusCounts({ counts }: StatusCountsProps) {
  return (
    <ul className="counts">
      {TRIAGE_STATUSES.map((status) => (
        <li key={status}>
          <span className="status-icon" style={{ color: STATUS_COLOR[status] }}>
            <Icon name={STATUS_ICON[status]} size={18} />
          </span>
          {STATUS_LABEL[status]}
          <strong>{counts[status]}</strong>
        </li>
      ))}
    </ul>
  )
}
