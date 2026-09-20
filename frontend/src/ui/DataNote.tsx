import { useI18n } from './i18n'
import type { MapMode } from '../hooks/useMapMode'

// What on screen is real and what is not, always in view: the fire data is real, the residents,
// calls and evacuations of the replay are fictional. The badge says which of the two you are
// looking at before the sentence explains it, and follows the dashed-draft, solid-official rule
// the alert drafts already use.
export function DataNote({ mode }: { mode: MapMode }) {
  const { t } = useI18n()
  return (
    <p className="data-note">
      <span className="data-badge" data-mode={mode}>
        {t(`dataNote.badge.${mode}`)}
      </span>
      {mode === 'replay' ? t('dataNote.replay') : t('dataNote.live')}
    </p>
  )
}
