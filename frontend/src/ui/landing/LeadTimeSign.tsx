import { useRef } from 'react'
import { useCountUp, useInView } from '../../hooks/usePlayhead'
import { Icon } from '../Icon'
import { useI18n } from '../i18n'
import { formatMinutes, formatSpanishClock } from '../theme'

/** The published lead time (domain/leadTime.ts PUBLISHED_LEAD_TIME). */
export interface PublishedLeadTime {
  zoneName: string
  radiusKm: number
  flaggedAt: string
  reachedAt: string
  minutes: number
}

interface LeadTimeSignProps {
  leadTime: PublishedLeadTime
}

// The fire-coloured band: the lead time in giant numerals, counted up once when it comes into view,
// and the two moments it spans.
export function LeadTimeSign({ leadTime }: LeadTimeSignProps) {
  const { t, intl } = useI18n()
  const band = useRef<HTMLElement>(null)
  const shown = useCountUp(leadTime.minutes, useInView(band, 0.4))
  const flagged = formatSpanishClock(Date.parse(leadTime.flaggedAt), intl)
  const reached = formatSpanishClock(Date.parse(leadTime.reachedAt), intl)
  const vars = { zone: leadTime.zoneName, radius: leadTime.radiusKm, flagged, reached }
  // Always "h" and "min" while counting, so the figure keeps its shape.
  const parts: [string, string][] = [
    [String(Math.floor(shown / 60)), ' h '],
    [String(shown % 60), ' min'],
  ]

  return (
    <section className="band-fire" aria-labelledby="lead-time" ref={band}>
      <div className="band-inner">
        <h2 id="lead-time" className="sign-title">
          <span className="sign-figure" aria-hidden="true">
            {parts.map(([number, unit]) => (
              <span key={unit}>
                {number}
                <span className="sign-unit">{unit}</span>
              </span>
            ))}
          </span>
          <span className="sr-only">{formatMinutes(leadTime.minutes)}</span>
          <span className="sign-label">{t('landing.leadTime.label', vars)}</span>
        </h2>
        <ol className="sign-timeline">
          <li className="sign-moment sign-start">
            <span className="sign-time">
              <Icon name="flag" size={20} />
              {flagged}
            </span>
            <span className="sign-event">{t('landing.leadTime.start')}</span>
          </li>
          <li className="sign-moment sign-end">
            <span className="sign-time">
              {reached}
              <Icon name="flame" size={20} />
            </span>
            <span className="sign-event">{t('landing.leadTime.end', vars)}</span>
          </li>
        </ol>
        <p className="sign-body">{t('landing.leadTime.body', vars)}</p>
        <p className="sign-caveat">{t('landing.leadTime.caveat')}</p>
      </div>
    </section>
  )
}
