import { Icon } from './Icon'
import { useI18n } from './i18n'

interface StartDemoProps {
  /** Who gets the call: the first resident in the registry. Null while it loads. */
  name: string | null
  /** The zone's order still has to be approved; the button does it first. */
  needsApproval: boolean
  /** Ringing, or approving on the way there. */
  busy: boolean
  /** Real phones cannot ring while the scripted simulation is running. */
  blockedBySimulation: boolean
  /** How the last press went, so the button is never silent. */
  result: 'placed' | 'busy' | 'noline' | 'failed' | null
  onStart: () => void
}

// One press for the pitch: approve the zone's order if it is not approved yet, then ring the first
// resident in the registry. Everything after that happens on its own — what they answer becomes
// their triage state, and a rescue rings and texts the crew.
export function StartDemo({ name, needsApproval, busy, blockedBySimulation, result, onStart }: StartDemoProps) {
  const { t } = useI18n()
  if (name === null) return null
  return (
    <div className="start-demo">
      <button type="button" className="start-demo-button icon-button" disabled={busy || blockedBySimulation} onClick={onStart}>
        <Icon name="phone" size={20} />
        {busy ? t('demo.starting') : t('demo.start')}
      </button>
      {result === null ? (
        <p className="start-demo-note">
          {blockedBySimulation
            ? t('demo.simulationOn')
            : needsApproval
              ? t('demo.willApprove', { name })
              : t('demo.willCall', { name })}
        </p>
      ) : (
        <p className={result === 'placed' ? 'start-demo-note placed' : 'start-demo-note warning'}>
          {t(`demo.${result}`, { name })}
        </p>
      )}
    </div>
  )
}
