import type { LeadTimeRange, PublishedLeadTime } from '../../domain/leadTime'
import { Icon } from '../Icon'
import { useI18n } from '../i18n'
import { formatSpanishClock } from '../theme'

interface LeadTimeProps {
  leadTime: PublishedLeadTime
  range: LeadTimeRange
}

// The timeline runs from 15:00 to 24:00 CEST on 23 July: the flag, the published arrival and the
// window in which the first hotspot came within 2 to 5 km.
const AXIS_START = Date.parse('2026-07-23T13:00:00Z')
const AXIS_END = Date.parse('2026-07-23T22:00:00Z')
const at = (epochMs: number) => `${((epochMs - AXIS_START) / (AXIS_END - AXIS_START)) * 100}%`

// The lead time as an honest range: about six hours, five to eight depending on the radius, with
// the two moments it spans and why it is not a precise figure. No count-up: the number is a range.
export function LeadTime({ leadTime, range }: LeadTimeProps) {
  const { t, intl } = useI18n()
  const clock = (epochMs: number) => formatSpanishClock(epochMs, intl)
  const vars = {
    zone: leadTime.zoneName,
    radius: leadTime.radiusKm,
    flagged: clock(range.flagged),
    reached: clock(range.reached),
    hours: range.aboutHours,
    min: range.minHours,
    max: range.maxHours,
    near: range.nearKm,
    far: range.farKm,
    early: clock(range.earliest),
    late: clock(range.latest),
  }

  return (
    <section className="section lead-time" aria-labelledby="lead-time">
      <div className="wrap">
        <div className="section-head">
          <h2 id="lead-time" className="lead-time-title">
            {t('landing.leadTime.title', vars)}
          </h2>
          <p className="section-lead">{t('landing.leadTime.range', vars)}</p>
        </div>

        <figure className="lt" aria-label={t('landing.leadTime.timeline')}>
          <div className="lt-track" aria-hidden="true">
            <span className="lt-lead" style={{ left: at(range.flagged), width: `calc(${at(range.reached)} - ${at(range.flagged)})` }} />
            <span className="lt-window" style={{ left: at(range.earliest), width: `calc(${at(range.latest)} - ${at(range.earliest)})` }} />
            <span className="lt-mark flag" style={{ left: at(range.flagged) }} />
            <span className="lt-mark reach" style={{ left: at(range.reached) }} />
          </div>
          <ol className="lt-events">
            <li className="lt-event">
              <span className="lt-time">
                <Icon name="flag" size={18} />
                {vars.flagged}
              </span>
              <span className="lt-what">{t('landing.leadTime.start', vars)}</span>
            </li>
            <li className="lt-event">
              <span className="lt-time">
                <Icon name="flame" size={18} />
                {vars.reached}
              </span>
              <span className="lt-what">{t('landing.leadTime.end', vars)}</span>
            </li>
          </ol>
          <figcaption className="lt-legend">
            <span className="lt-swatch" aria-hidden="true" />
            {t('landing.leadTime.window', vars)}
          </figcaption>
        </figure>

        <div className="lt-notes">
          <div>
            <p>{t('landing.leadTime.body', vars)}</p>
            <p className="lt-caveat">{t('landing.leadTime.caveat')}</p>
          </div>
          <div>
            <h3>{t('landing.leadTime.whyTitle')}</h3>
            <p>{t('landing.leadTime.why')}</p>
          </div>
        </div>
      </div>
    </section>
  )
}
