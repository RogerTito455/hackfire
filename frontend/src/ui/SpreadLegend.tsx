import { formatReplayTime, SPREAD_HOUR_COLORS } from './theme'

interface SpreadLegendProps {
  /** When the forecast in force was issued, epoch ms; null when there is none. */
  issuedAt: number | null
}

// What the coloured areas on the map mean.
export function SpreadLegend({ issuedAt }: SpreadLegendProps) {
  const gradient = SPREAD_HOUR_COLORS.map(([, color]) => color).join(', ')
  return (
    <div className="spread-legend">
      <span className="replay-ramp" style={{ background: `linear-gradient(to right, ${gradient})` }} />
      <span>now → 6 h ahead</span>
      <span className="issued">
        {issuedAt === null ? 'No forecast at this time' : `Forecast from ${formatReplayTime(issuedAt)}`}
      </span>
    </div>
  )
}
