import { useI18n } from './i18n'
import type { MapMode } from '../hooks/useMapMode'

// What on screen is real and what is not, always in view: the fire data is real, the residents,
// calls and evacuations of the replay are fictional.
export function DataNote({ mode }: { mode: MapMode }) {
  const { t } = useI18n()
  return <p className="data-note">{mode === 'replay' ? t('dataNote.replay') : t('dataNote.live')}</p>
}
