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
  /** The finding that explains how the number was computed. */
  howUrl: string
}

// The page's one loud element: the lead time, set like a sign, with the two moments it spans.
// The bar between them is the window to act, so it is blue; its end is the fire, so it is warm.
export function LeadTimeSign({ leadTime, howUrl }: LeadTimeSignProps) {
  const { t, intl } = useI18n()
  const flagged = formatSpanishClock(Date.parse(leadTime.flaggedAt), intl)
  const reached = formatSpanishClock(Date.parse(leadTime.reachedAt), intl)
  const vars = { zone: leadTime.zoneName, radius: leadTime.radiusKm, flagged, reached }

  return (
    <section className="sign" aria-labelledby="lead-time">
      <h2 id="lead-time" className="sign-title">
        <span className="sign-figure">
          {/* "6 h 8 min": numerals full size; units, with their spaces, small. */}
          {formatMinutes(leadTime.minutes)
            .split(/(\d+)/)
            .filter((part) => part !== '')
            .map((part, index) =>
              /^\d+$/.test(part) ? (
                part
              ) : (
                <span key={index} className="sign-unit">
                  {part}
                </span>
              ),
            )}
        </span>
        <span className="sign-label">{t('landing.leadTime.label', vars)}</span>
      </h2>
      <ol className="sign-timeline">
        <li className="sign-moment sign-start">
          <span className="sign-time icon-button">
            <Icon name="flag" size={18} />
            {flagged}
          </span>
          <span className="sign-event">{t('landing.leadTime.start')}</span>
        </li>
        <li className="sign-moment sign-end">
          <span className="sign-time icon-button">
            {reached}
            <Icon name="flame" size={18} />
          </span>
          <span className="sign-event">{t('landing.leadTime.end', vars)}</span>
        </li>
      </ol>
      <p className="sign-body">{t('landing.leadTime.body', vars)}</p>
      <p className="sign-caveat">
        {t('landing.leadTime.caveat')}{' '}
        <a href={howUrl}>{t('landing.leadTime.how')}</a>
      </p>
    </section>
  )
}
