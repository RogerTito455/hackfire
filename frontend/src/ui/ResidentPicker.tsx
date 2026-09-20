import type { Neighbor } from '../domain/triage'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { STATUS_COLOR, STATUS_ICON } from './theme'

// What the way out shows before a resident is picked: the registry itself, so the coordinator can
// reach anyone by name instead of hunting for their pin. Same rows as the map markers, in the same
// status colours, each one with its icon.
export function ResidentPicker({ neighbors, onSelect }: { neighbors: Neighbor[]; onSelect: (id: string) => void }) {
  const { t } = useI18n()
  if (neighbors.length === 0) return <p className="empty">{t('app.noResidents')}</p>
  return (
    <ul className="picker" aria-label={t('app.residents')}>
      {neighbors.map((neighbor) => (
        <li key={neighbor.id}>
          <button type="button" className="picker-item" onClick={() => onSelect(neighbor.id)}>
            <span className="picker-status" style={{ color: STATUS_COLOR[neighbor.status] }}>
              <Icon name={STATUS_ICON[neighbor.status]} size={16} />
            </span>
            <span className="picker-name">{neighbor.name}</span>
            <span className="picker-state">{t(`status.${neighbor.status}`)}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
