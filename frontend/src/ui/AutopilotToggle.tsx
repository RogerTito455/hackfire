import { useI18n } from './i18n'

interface AutopilotToggleProps {
  enabled: boolean
  busy: boolean
  onToggle: () => void
}

// The demo autopilot's switch under the replay scrubber. While it is on, a line says plainly that the
// strip shows a simulation with the demo residents, not what happened on 23 July.
export function AutopilotToggle({ enabled, busy, onToggle }: AutopilotToggleProps) {
  const { t } = useI18n()
  return (
    <div className="autopilot">
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        className={enabled ? 'autopilot-switch on' : 'autopilot-switch'}
        onClick={onToggle}
        disabled={busy}
      >
        <span className="autopilot-track" aria-hidden="true">
          <span className="autopilot-knob" />
        </span>
        <span>{t('autopilot.toggle')}</span>
      </button>
      {enabled && (
        <p className="autopilot-note" role="status">
          {t('autopilot.note')}
        </p>
      )}
    </div>
  )
}
