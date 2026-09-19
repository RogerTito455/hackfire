import type { LoadStatus } from '../hooks/useFireReplay'
import { MINUTE, type TimeRange } from '../domain/hotspots'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatSpanishTime, HOTSPOT_AGE_COLORS } from './theme'

interface ReplayControlsProps {
  status: LoadStatus
  range: TimeRange | null
  time: number | null
  observedCount: number
  playing: boolean
  onTimeChange: (time: number) => void
  onTogglePlay: () => void
}

const SLIDER_STEP = 5 * MINUTE

// Time slider over the map: presentation only, the clock lives in useFireReplay.
export function ReplayControls({
  status,
  range,
  time,
  observedCount,
  playing,
  onTimeChange,
  onTogglePlay,
}: ReplayControlsProps) {
  const { t, intl } = useI18n()
  if (status === 'loading') return <div className="replay">{t('replay.loading')}</div>
  if (status === 'error' || range === null || time === null) {
    return <div className="replay">{t('replay.unavailable')}</div>
  }

  const gradient = HOTSPOT_AGE_COLORS.map(([, color]) => color).join(', ')
  // Round the maximum up to a whole step so the thumb can reach the last hotspot.
  const sliderMax = range.start + Math.ceil((range.end - range.start) / SLIDER_STEP) * SLIDER_STEP

  return (
    <div className="replay">
      <button
        type="button"
        className="replay-play"
        onClick={onTogglePlay}
        aria-label={playing ? t('replay.pause') : t('replay.play')}
      >
        <Icon name={playing ? 'pause' : 'play'} size={18} />
      </button>
      <div className="replay-body">
        <div className="replay-head">
          <strong>{formatSpanishTime(time, intl)}</strong>
          <span>{t('replay.hotspots', { count: observedCount })}</span>
        </div>
        <input
          type="range"
          className="replay-slider"
          min={range.start}
          max={sliderMax}
          step={SLIDER_STEP}
          value={time}
          onChange={(event) => onTimeChange(Number(event.target.value))}
          aria-label={t('replay.slider')}
        />
        <div className="replay-legend">
          <span>{t('replay.fresh')}</span>
          <span className="replay-ramp" style={{ background: `linear-gradient(to right, ${gradient})` }} />
          <span>{t('replay.old')}</span>
        </div>
      </div>
    </div>
  )
}
