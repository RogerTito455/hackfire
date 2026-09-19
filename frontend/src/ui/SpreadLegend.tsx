import { useI18n } from './i18n'
import { formatSpanishTime, SPREAD_HOUR_COLORS } from './theme'

interface SpreadLegendProps {
  /** When the forecast in force was issued, epoch ms; null when there is none. */
  issuedAt: number | null
}

// What the coloured areas on the map mean.
export function SpreadLegend({ issuedAt }: SpreadLegendProps) {
  const { t, intl } = useI18n()
  const gradient = SPREAD_HOUR_COLORS.map(([, color]) => color).join(', ')
  return (
    <div className="spread-legend">
      <span>{t('fire.legendNow')}</span>
      <span className="replay-ramp" style={{ background: `linear-gradient(to right, ${gradient})` }} />
      <span>{t('fire.legendAhead')}</span>
      <span className="issued">
        {issuedAt === null ? t('fire.noForecast') : t('fire.issued', { time: formatSpanishTime(issuedAt, intl) })}
      </span>
    </div>
  )
}
