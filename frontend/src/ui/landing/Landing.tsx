import { useEffect } from 'react'
import { Icon } from '../Icon'
import { useI18n } from '../i18n'
import { LanguagePicker } from '../LanguagePicker'
import { STATUS_COLOR, STATUS_ICON } from '../theme'
import { FireField } from './FireField'
import { LeadTimeSign, type PublishedLeadTime } from './LeadTimeSign'
import { MiniDemo } from './MiniDemo'
import './landing.css'

interface LandingProps {
  /** The live dashboard. */
  demoUrl: string
  leadTime: PublishedLeadTime
}

const OUTCOMES = ['evacuating', 'no_answer', 'needs_rescue'] as const

const SCREENSHOT = { src: '/dashboard-phone.webp', width: 390, height: 780 }

export function Landing({ demoUrl, leadTime }: LandingProps) {
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
        <a className="landing-brand" href="#top" aria-label={t('landing.home')}>
          <Icon name="logo" size={26} />
          <span>HackFire</span>
        </a>
        <a className="landing-button primary compact" href={demoUrl}>
          {t('landing.nav.demo')}
        </a>
        <LanguagePicker />
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <FireField />
          <div className="hero-inner">
            <h1 id="hero-title">{t('landing.hero.title')}</h1>
            <p className="hero-lead">{t('landing.hero.lead')}</p>
            <div className="hero-actions">
              <a className="landing-button primary glow" href={demoUrl}>
                {t('landing.hero.cta')}
              </a>
              <a className="landing-button ghost" href="#how">
                {t('landing.hero.how')}
              </a>
            </div>
            <p className="hero-event">{t('landing.hero.event')}</p>
          </div>
        </section>

        <LeadTimeSign leadTime={leadTime} />

        <section className="landing-section problem" aria-labelledby="problem">
          <h2 id="problem">{t('landing.problem.title')}</h2>
          <div className="problem-text">
            <p>{t('landing.problem.body')}</p>
            <p>{t('landing.problem.gap')}</p>
          </div>
        </section>

        <section className="how" id="how" aria-labelledby="how-title">
          <div className="how-inner">
            <h2 id="how-title">{t('landing.how.title')}</h2>
            <p className="how-lead">{t('landing.how.lead')}</p>
            <MiniDemo />
          </div>
        </section>

        <section className="outcomes" aria-labelledby="outcomes-title">
          <div className="outcomes-inner">
            <h2 id="outcomes-title">{t('landing.outcomes.title')}</h2>
            <ul className="outcome-tiles">
              {OUTCOMES.map((status) => (
                <li key={status} className={`outcome-tile ${status}`} style={{ borderColor: STATUS_COLOR[status] }}>
                  <span className="outcome-head" style={{ background: STATUS_COLOR[status] }}>
                    <Icon name={STATUS_ICON[status]} size={34} />
                    <span className="outcome-name">{outcomeText[status][0]}</span>
                  </span>
                  <span className="outcome-body">{outcomeText[status][1]}</span>
                </li>
              ))}
            </ul>
            <blockquote className="quote">
              <p>{t('landing.how.quote')}</p>
            </blockquote>
            <p className="network">{t('landing.how.network')}</p>
          </div>
        </section>

        <section className="band-blue" aria-labelledby="demo">
          <div className="band-blue-inner">
            <div className="demo-text">
              <h2 id="demo">{t('landing.demo.title')}</h2>
              <ol className="demo-steps">
                <li>{t('landing.demo.replay')}</li>
                <li>{t('landing.demo.select')}</li>
                <li>{t('landing.demo.call')}</li>
                <li>{t('landing.demo.ask')}</li>
              </ol>
              <p className="demo-line">{t('landing.demo.line')}</p>
              <a className="landing-button inverse" href={demoUrl}>
                {t('landing.hero.cta')}
              </a>
            </div>
            <figure className="phone">
              <div className="phone-body">
                <img
                  src={SCREENSHOT.src}
                  width={SCREENSHOT.width}
                  height={SCREENSHOT.height}
                  alt={t('landing.demo.shot')}
                  loading="lazy"
                  decoding="async"
                />
              </div>
              <figcaption>{t('landing.demo.caption')}</figcaption>
            </figure>
          </div>
        </section>

        <section className="landing-section" aria-labelledby="stack">
          <h2 id="stack">{t('landing.stack.title')}</h2>
          <dl className="stack">
            {stack.map(([term, description]) => (
              <div key={term} className="stack-row">
                <dt>{term}</dt>
                <dd>{description}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="landing-section note" aria-labelledby="note">
          <h2 id="note">{t('landing.note.title')}</h2>
          <p>{t('landing.note.body')}</p>
        </section>
      </main>

      <footer className="landing-footer">
        <p className="footer-links">
          <a href={demoUrl}>{t('landing.nav.demo')}</a>
          <span>{t('landing.footer.license')}</span>
        </p>
      </footer>
    </div>
  )
}
