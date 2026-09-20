import type { MapMode } from '../hooks/useMapMode'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { MAP_MODE_ICON } from './theme'

interface ModeToggleProps {
  mode: MapMode
  onChange: (mode: MapMode) => void
}

const MODES: readonly MapMode[] = ['replay', 'live']

export function ModeToggle({ mode, onChange }: ModeToggleProps) {
  const { t } = useI18n()
  return (
    <div className="mode-toggle" role="group" aria-label={t('mode.label')}>
      {MODES.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={mode === option}
          className={mode === option ? 'icon-button active' : 'icon-button'}
          onClick={() => onChange(option)}
          title={t(`mode.${option}`)}
        >
          <Icon name={MAP_MODE_ICON[option]} size={18} />
          <span className="mode-label">{t(`mode.${option}`)}</span>
        </button>
      ))}
    </div>
  )
}
