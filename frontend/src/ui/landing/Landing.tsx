import { useEffect } from 'react'
import type { LeadTimeRange, PublishedLeadTime } from '../../domain/leadTime'
import { Icon } from '../Icon'
import { useI18n } from '../i18n'
import { LanguagePicker } from '../LanguagePicker'
import { STATUS_COLOR, STATUS_ICON } from '../theme'
import { LeadTime } from './LeadTime'
import { MiniDemo } from './MiniDemo'
import './landing.css'

interface LandingProps {
  /** The live dashboard. */
  demoUrl: string
  leadTime: PublishedLeadTime
  leadTimeRange: LeadTimeRange
}

const OUTCOMES = ['evacuating', 'no_answer', 'needs_rescue'] as const

const SCREENSHOT = { src: '/dashboard-phone.webp', width: 390, height: 780 }

export function Landing({ demoUrl, leadTime, leadTimeRange }: LandingProps) {
  const { t } = useI18n()

  useEffect(() => {
    document.title = t('landing.title')
  }, [t])

  const outcomeText = {
    evacuating: [t('status.evacuating'), t('landing.outcomes.evacuating')],
    no_answer: [t('status.no_answer'), t('landing.outcomes.no_answer')],
    needs_rescue: [t('status.needs_rescue'), t('landing.outcomes.needs_rescue')],
  }
  const stack = [
    [t('landing.stack.deepfire'), t('landing.stack.deepfireBody')],
    [t('landing.stack.spread'), t('landing.stack.spreadBody')],
    [t('landing.stack.routing'), t('landing.stack.routingBody')],
    [t('landing.stack.voice'), t('landing.stack.voiceBody')],
    [t('landing.stack.places'), t('landing.stack.placesBody')],
  ]

  return (
    <div className="landing">
      <header className="landing-bar">
        <div className="wrap landing-bar-inner">
          <a className="landing-brand" href="#top" aria-label={t('landing.home')}>
            <Icon name="logo" size={24} />
            <span>HackFire</span>
          </a>
          <a className="button primary small" href={demoUrl}>
            {t('landing.nav.demo')}
          </a>
          <LanguagePicker />
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="wrap hero-grid">
            <div className="hero-copy">
              <h1 id="hero-title">{t('landing.hero.title')}</h1>
              <p className="hero-lead">{t('landing.hero.lead')}</p>
              <div className="hero-actions">
                <a className="button primary" href={demoUrl}>
                  {t('landing.hero.cta')}
                </a>
                <a className="button secondary" href="#how">
                  {t('landing.hero.how')}
                </a>
              </div>
              <p className="hero-event">{t('landing.hero.event')}</p>
            </div>
            <figure className="device">
              <div className="device-body">
                <img
                  src={SCREENSHOT.src}
                  width={SCREENSHOT.width}
                  height={SCREENSHOT.height}
                  alt={t('landing.hero.shot')}
                  decoding="async"
                />
              </div>
              <figcaption>{t('landing.hero.caption')}</figcaption>
            </figure>
          </div>
        </section>

        <LeadTime leadTime={leadTime} range={leadTimeRange} />

        <section className="section" aria-labelledby="problem">
          <div className="wrap split">
            <h2 id="problem">{t('landing.problem.title')}</h2>
            <div className="prose">
              <p>{t('landing.problem.body')}</p>
              <p>{t('landing.problem.gap')}</p>
            </div>
          </div>
        </section>

        <section className="section" id="how" aria-labelledby="how-title">
          <div className="wrap">
            <div className="section-head">
              <h2 id="how-title">{t('landing.how.title')}</h2>
              <p className="section-lead">{t('landing.how.lead')}</p>
            </div>
            <MiniDemo />
          </div>
        </section>

        <section className="section" aria-labelledby="outcomes-title">
          <div className="wrap">
            <div className="section-head">
              <h2 id="outcomes-title">{t('landing.outcomes.title')}</h2>
              <p className="section-lead">{t('landing.outcomes.lead')}</p>
            </div>
            <ul className="outcomes">
              {OUTCOMES.map((status) => (
                <li key={status} className="outcome" style={{ borderTopColor: STATUS_COLOR[status] }}>
                  <span className={`outcome-icon ${status}`} style={{ background: STATUS_COLOR[status] }}>
                    <Icon name={STATUS_ICON[status]} size={20} />
                  </span>
                  <h3>{outcomeText[status][0]}</h3>
                  <p>{outcomeText[status][1]}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section" aria-labelledby="demo">
          <div className="wrap split">
            <div>
              <h2 id="demo">{t('landing.demo.title')}</h2>
              <p className="demo-line">{t('landing.demo.line')}</p>
              <a className="button primary" href={demoUrl}>
                {t('landing.hero.cta')}
              </a>
            </div>
            <ol className="demo-steps">
              <li>{t('landing.demo.replay')}</li>
              <li>{t('landing.demo.select')}</li>
              <li>{t('landing.demo.call')}</li>
              <li>{t('landing.demo.ask')}</li>
            </ol>
          </div>
        </section>

        <section className="section" aria-labelledby="stack">
          <div className="wrap split">
            <h2 id="stack">{t('landing.stack.title')}</h2>
            <dl className="stack">
              {stack.map(([term, description]) => (
                <div key={term} className="stack-row">
                  <dt>{term}</dt>
                  <dd>{description}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="section note" aria-labelledby="note">
          <div className="wrap split">
            <h2 id="note">{t('landing.note.title')}</h2>
            <p>{t('landing.note.body')}</p>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="wrap footer-inner">
          <span>HackFire, HackBarna 2026</span>
          <span>{t('landing.footer.license')}</span>
        </div>
      </footer>
    </div>
  )
}
