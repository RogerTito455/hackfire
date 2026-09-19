import type { RoadClosure } from '../domain/closures'
import { Icon } from './Icon'
import { useI18n } from './i18n'

interface ClosuresPanelProps {
  closures: RoadClosure[]
  closing: boolean
  saving: boolean
  error: boolean
  onToggleClosing: () => void
  onReopen: (closureId: string) => void
  /** A resident's name by id, for the ones who need calling again. */
  nameOf: (neighborId: string) => string
}

// Roads the coordinator marked as cut. Routes go around them; residents already on their way through
// one are named, so they can be called again with the new route.
export function ClosuresPanel({ closures, closing, saving, error, onToggleClosing, onReopen, nameOf }: ClosuresPanelProps) {
  const { t, intl } = useI18n()
  return (
    <div className="closures">
      <button
        type="button"
        className={`${closing ? 'talk-hang-up' : 'text-triage-send'} icon-button`}
        onClick={onToggleClosing}
        disabled={saving}
        aria-pressed={closing}
      >
        <Icon name={closing ? 'close' : 'road-closed'} size={16} />
        {closing ? t('closures.cancel') : t('closures.close')}
      </button>
      {closing && <p className="hint">{t('closures.hint')}</p>}
      {error && <p className="error">{t('closures.error')}</p>}
      {closures.length === 0 ? (
        <p className="empty">{t('closures.empty')}</p>
      ) : (
        <ol>
          {closures.map((closure, index) => (
            <li key={closure.id}>
              <div className="closure-row">
                <Icon name="road-closed" size={18} />
                <span className="closure-name">
                  {t('closures.item', { number: index + 1 })}
                  <small>
                    {new Date(closure.created_at).toLocaleTimeString(intl, { hour: '2-digit', minute: '2-digit' })}
                  </small>
                </span>
                <button type="button" className="link" onClick={() => onReopen(closure.id)}>
                  {t('closures.reopen')}
                </button>
              </div>
              {closure.affected.length > 0 && (
                <p className="closure-affected">{t('closures.affected', { names: closure.affected.map(nameOf).join(', ') })}</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
