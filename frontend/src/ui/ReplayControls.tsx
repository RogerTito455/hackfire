import type { LoadStatus } from '../hooks/useFireReplay'
import { MINUTE, type TimeRange } from '../domain/hotspots'
import { Icon } from './Icon'
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
  if (status === 'loading') return <div className="replay">Loading satellite hotspots…</div>
  if (status === 'error' || range === null || time === null) {
    return <div className="replay">Satellite hotspots unavailable</div>
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
        aria-label={playing ? 'Pause replay' : 'Play replay'}
      >
        <Icon name={playing ? 'pause' : 'play'} size={18} />
      </button>
      <div className="replay-body">
        <div className="replay-head">
          <strong>{formatSpanishTime(time)}</strong>
          <span>{observedCount.toLocaleString('en-GB')} hotspots so far</span>
        </div>
        <input
          type="range"
          className="replay-slider"
          min={range.start}
          max={sliderMax}
          step={SLIDER_STEP}
          value={time}
          onChange={(event) => onTimeChange(Number(event.target.value))}
          aria-label="Replay time"
        />
        <div className="replay-legend">
          <span className="replay-ramp" style={{ background: `linear-gradient(to right, ${gradient})` }} />
          <span>just detected → a day old</span>
        </div>
      </div>
    </div>
  )
}
