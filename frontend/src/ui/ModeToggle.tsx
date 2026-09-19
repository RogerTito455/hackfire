import type { MapMode } from '../hooks/useMapMode'
import { Icon } from './Icon'
import { MAP_MODE_ICON, MAP_MODE_LABEL } from './theme'

interface ModeToggleProps {
  mode: MapMode
  onChange: (mode: MapMode) => void
}

const MODES: readonly MapMode[] = ['replay', 'live']

export function ModeToggle({ mode, onChange }: ModeToggleProps) {
  return (
    <div className="mode-toggle" role="group" aria-label="Map mode">
      {MODES.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={mode === option}
          className={mode === option ? 'icon-button active' : 'icon-button'}
          onClick={() => onChange(option)}
        >
          <Icon name={MAP_MODE_ICON[option]} size={16} />
          {MAP_MODE_LABEL[option]}
        </button>
      ))}
    </div>
  )
}
