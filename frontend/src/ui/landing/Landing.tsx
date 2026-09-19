import { useEffect } from 'react'
import { Icon, type IconName } from '../Icon'
import { useI18n } from '../i18n'
import { LanguagePicker } from '../LanguagePicker'
import { STATUS_COLOR, STATUS_ICON } from '../theme'
import { LeadTimeSign, type PublishedLeadTime } from './LeadTimeSign'
import './landing.css'

interface LandingProps {
  /** The live dashboard. */
  demoUrl: string
  /** The public repository; the findings the page cites live there. */
  repoUrl: string
  leadTime: PublishedLeadTime
}

const OUTCOMES = ['evacuating', 'no_answer', 'needs_rescue'] as const

const SCREENSHOT = { src: '/dashboard-phone.webp', width: 390, height: 780 }

export function Landing({ demoUrl, repoUrl, leadTime }: LandingProps) {
  const { t } = useI18n()
  const doc = (name: string) => `${repoUrl}/blob/main/docs/findings/${name}`

  useEffect(() => {
    document.title = t('landing.title')
  }, [t])

  // Each step's icon takes the colour that thing has on the dashboard's map: warm is the fire,
  // purple the places at risk, blue the way out, red a rescue.
  const steps: { icon: IconName; tone: string; title: string; body: string }[] = [
    { icon: 'flame', tone: 'fire', title: t('landing.how.fireTitle'), body: t('landing.how.fireBody') },
    { icon: 'home', tone: 'zone', title: t('landing.how.zonesTitle'), body: t('landing.how.zonesBody') },
    { icon: 'phone', tone: 'route', title: t('landing.how.callTitle'), body: t('landing.how.callBody') },
    { icon: 'lifebuoy', tone: 'rescue', title: t('landing.how.triageTitle'), body: t('landing.how.triageBody') },
  ]
  const outcomeText = {
    evacuating: t('status.evacuating'),
    no_answer: t('status.no_answer'),
    needs_rescue: t('status.needs_rescue'),
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
        <div className="landing-hero">
          <section className="hero" aria-labelledby="hero-title">
            <h1 id="hero-title">{t('landing.hero.title')}</h1>
            <p className="hero-lead">{t('landing.hero.lead')}</p>
            <div className="hero-actions">
              <a className="landing-button primary" href={demoUrl}>
                {t('landing.hero.cta')}
              </a>
              <a className="landing-button secondary" href={repoUrl}>
                {t('landing.hero.code')}
              </a>
            </div>
            <p className="hero-event">{t('landing.hero.event')}</p>
          </section>
          <LeadTimeSign leadTime={leadTime} howUrl={doc('2026-09-19-lead-time.md')} />
        </div>

        <section className="landing-section problem" aria-labelledby="problem">
          <h2 id="problem">{t('landing.problem.title')}</h2>
          <div className="problem-text">
            <p>{t('landing.problem.body')}</p>
            <p>{t('landing.problem.gap')}</p>
            <p className="landing-meta">
              <a href={doc('2026-09-19-press-figures.md')}>{t('landing.problem.sources')}</a>
            </p>
          </div>
        </section>

        <section className="landing-section" aria-labelledby="how">
          <h2 id="how">{t('landing.how.title')}</h2>
          <ol className="steps">
            {steps.map((step, index) => (
              <li key={step.icon} className={`step tone-${step.tone}`}>
                <span className="step-marker">
                  <span className="step-number">{index + 1}</span>
                  <Icon name={step.icon} size={26} />
                </span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
          <div className="outcomes">
            <p className="outcomes-label">{t('landing.how.outcomes')}</p>
            <ul className="outcome-list">
              {OUTCOMES.map((status) => (
                <li key={status} className="outcome" style={{ borderColor: STATUS_COLOR[status] }}>
                  <span className="outcome-icon" style={{ color: STATUS_COLOR[status] }}>
                    <Icon name={STATUS_ICON[status]} size={18} />
                  </span>
                  {outcomeText[status]}
                </li>
              ))}
            </ul>
          </div>
          <blockquote className="quote">
            <p>{t('landing.how.quote')}</p>
          </blockquote>
          <p className="network">{t('landing.how.network')}</p>
        </section>

        <section className="landing-section demo" aria-labelledby="demo">
          <div className="demo-text">
            <h2 id="demo">{t('landing.demo.title')}</h2>
            <ol className="demo-steps">
              <li>{t('landing.demo.replay')}</li>
              <li>{t('landing.demo.select')}</li>
              <li>{t('landing.demo.call')}</li>
              <li>{t('landing.demo.ask')}</li>
            </ol>
            <p className="landing-meta">{t('landing.demo.line')}</p>
            <a className="landing-button primary" href={demoUrl}>
              {t('landing.hero.cta')}
            </a>
          </div>
          <figure className="shot">
            <img
              src={SCREENSHOT.src}
              width={SCREENSHOT.width}
              height={SCREENSHOT.height}
              alt={t('landing.demo.shot')}
              loading="lazy"
              decoding="async"
            />
            <figcaption>{t('landing.demo.caption')}</figcaption>
          </figure>
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
          <a href={repoUrl}>GitHub</a>
          <a href={`${repoUrl}/blob/main/LICENSE`}>{t('landing.footer.license')}</a>
        </p>
      </footer>
    </div>
  )
}
