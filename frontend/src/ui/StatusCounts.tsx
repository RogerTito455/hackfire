import { TRIAGE_STATUSES, type StatusCounts as Counts } from '../domain/triage'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { STATUS_COLOR, STATUS_ICON } from './theme'

interface StatusCountsProps {
  counts: Counts
}

// The one loud element: four colour blocks, one per triage state, readable at arm's length in
// sunlight. Colour always comes with its icon, so no state depends on colour alone.
export function StatusCounts({ counts }: StatusCountsProps) {
  const { t } = useI18n()
  return (
    <ul className="status-strip" aria-label={t('status.strip')}>
      {TRIAGE_STATUSES.map((status) => (
        <li
          key={status}
          className={counts[status] > 0 ? 'has' : 'none'}
          style={{ ['--tone' as string]: STATUS_COLOR[status] }}
        >
          <Icon name={STATUS_ICON[status]} size={18} />
          <strong>{counts[status]}</strong>
          <span>{t(`status.${status}`)}</span>
        </li>
      ))}
    </ul>
  )
}
