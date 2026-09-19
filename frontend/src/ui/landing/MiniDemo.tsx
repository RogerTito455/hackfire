import { useMemo, useRef, useState } from 'react'
import type { TriageStatus } from '../../domain/triage'
import { prefersReducedMotion, useInView, usePlayhead } from '../../hooks/usePlayhead'
import { Icon, type IconName } from '../Icon'
import { useI18n } from '../i18n'
import { formatSpanishClock, SPREAD_HOUR_COLORS, STATUS_COLOR, STATUS_ICON } from '../theme'
import {
  CALL_LINES,
  CONE_AT,
  CREW_DRAW,
  DAY_START,
  EVACUATION_DRAW,
  hotspotColor,
  LOOP_SECONDS,
  MINI,
  minuteAt,
  OUTCOMES,
  progress,
  STEP_FRAMES,
  STEP_STARTS,
  stepAt,
  ZONES_AT,
} from './miniDemoScript'

const STATUSES: readonly TriageStatus[] = ['pending', 'evacuating', 'no_answer', 'needs_rescue']
const STEP_ICONS: readonly IconName[] = ['flame', 'home', 'phone', 'lifebuoy']
// The residents sit a few metres apart; spread them out from their zone's centre so each pin reads.
const PIN_SPREAD = 2.5

function spreadPin([x, y]: number[]): [number, number] {
  const zone = MINI.zones.reduce((a, b) =>
    Math.hypot(b.centre[0] - x, b.centre[1] - y) < Math.hypot(a.centre[0] - x, a.centre[1] - y) ? b : a,
  )
  return [zone.centre[0] + (x - zone.centre[0]) * PIN_SPREAD, zone.centre[1] + (y - zone.centre[1]) * PIN_SPREAD]
}

const PINS = MINI.residents.map(spreadPin)
const EVACUEE = OUTCOMES.find((o) => o.status === 'evacuating')!.resident
const RESCUE = OUTCOMES.find((o) => o.status === 'needs_rescue')!.resident
const EVACUATION_PATH = `${PINS[EVACUEE].join(',')} ${MINI.evacuationRoute}`
const CREW_PATH = `${MINI.crewRoute} ${PINS[RESCUE].join(',')}`

function coneColor(hour: number): string {
  let color = SPREAD_HOUR_COLORS[0][1]
  for (const [hours, stop] of SPREAD_HOUR_COLORS) if (hour >= hours) color = stop
  return color
}

// "How it works" as a looping illustration: real hotspots of 23 July fill the map, the predicted
// spread reaches two zones, an example call plays out and the example residents' pins change state.
export function MiniDemo() {
  const { t, intl } = useI18n()
  const root = useRef<HTMLDivElement>(null)
  const inView = useInView(root, 0.35)
  const [reduced] = useState(prefersReducedMotion)
  const [paused, setPaused] = useState(false)
  const playing = inView && !paused && !reduced
  // Scrolling away and back resumes where it was; a pause the user chose sticks. Under reduced
  // motion it never plays: it opens on the final frame and the steps jump between still frames.
  const { time, seek } = usePlayhead(LOOP_SECONDS, playing, reduced ? STEP_FRAMES[3] : 0)

  const minute = minuteAt(time)
  const step = stepAt(time)
  const steps = [
    { title: t('landing.how.fireTitle'), body: t('landing.how.fireBody') },
    { title: t('landing.how.zonesTitle'), body: t('landing.how.zonesBody') },
    { title: t('landing.how.callTitle'), body: t('landing.how.callBody') },
    { title: t('landing.how.triageTitle'), body: t('landing.how.triageBody') },
  ]
  const lines = {
    agentLine: t('landing.how.agentLine'),
    agentAsk: t('landing.how.agentAsk'),
    residentLine: t('landing.how.residentLine'),
  }
  const statusText: Record<TriageStatus, string> = {
    pending: t('status.pending'),
    evacuating: t('status.evacuating'),
    no_answer: t('status.no_answer'),
    needs_rescue: t('status.needs_rescue'),
  }

  const statusOf = PINS.map((_, index) => {
    const outcome = OUTCOMES.find((o) => o.resident === index)
    return outcome && time >= outcome.at ? outcome.status : 'pending'
  })
  const counts = STATUSES.map((status) => statusOf.filter((s) => s === status).length)
  const speaking = CALL_LINES.find((line) => time >= line.from && time < line.to + 0.2)

  // Hotspots are the only thing redrawn every frame; bucket the minute so memo work stays small.
  const bucket = Math.floor(minute / 5)
  const hotspots = useMemo(
    () =>
      MINI.hotspots
        .filter((h) => h[2] <= bucket * 5)
        .map((h) => ({ x: h[0], y: h[1], age: (bucket * 5 - h[2]) / 60 })),
    [bucket],
  )

  const jump = (index: number) => {
    seek(reduced || paused ? STEP_FRAMES[index] : STEP_STARTS[index])
  }

  return (
    <div className="mini" ref={root}>
      <div className="mini-stage">
        <div className="mini-map">
          <svg viewBox={`0 0 ${MINI.width} ${MINI.height}`} role="img" aria-label={t('landing.how.map')}>
            <g className={`mini-cone${time >= CONE_AT ? ' shown' : ''}`}>
              {MINI.cone
                .slice()
                .reverse()
                .map((ring) => (
                  <polygon key={ring.hour} points={ring.points} fill={coneColor(ring.hour)} color={coneColor(ring.hour)} />
                ))}
            </g>
            {MINI.zones.map((zone) => (
              <g key={zone.id} className={`mini-zone${time >= ZONES_AT ? ' lit' : ''}`}>
                <polygon points={zone.outline} />
              </g>
            ))}
            <polyline
              className="mini-route crew"
              points={CREW_PATH}
              pathLength={1}
              style={{ strokeDashoffset: 1 - progress(time, CREW_DRAW) }}
            />
            <polyline
              className="mini-route way-out"
              points={EVACUATION_PATH}
              pathLength={1}
              style={{ strokeDashoffset: 1 - progress(time, EVACUATION_DRAW) }}
            />
            <g className="mini-hotspots">
              {hotspots.map((h, index) => (
                <circle
                  key={index}
                  cx={h.x}
                  cy={h.y}
                  r={h.age < 1 ? 9 : 6.5}
                  fill={hotspotColor(h.age)}
                  className={h.age < 1 ? 'fresh' : undefined}
                />
              ))}
            </g>
            <g className="mini-place safe">
              <circle cx={MINI.safePoint.at[0]} cy={MINI.safePoint.at[1]} r={13} />
              <text x={MINI.safePoint.at[0] + 20} y={MINI.safePoint.at[1] - 34} textAnchor="end">
                {t('landing.how.safe')}
              </text>
            </g>
            <g className="mini-place crew-base">
              <rect x={MINI.crewBase[0] - 11} y={MINI.crewBase[1] - 11} width={22} height={22} rx={5} />
              <text x={MINI.crewBase[0] - 24} y={MINI.crewBase[1] + 46} textAnchor="end">
                {t('landing.how.crew')}
              </text>
            </g>
            {MINI.zones.map((zone) => (
              <g key={zone.id} className={`mini-zone-label${time >= ZONES_AT ? ' lit' : ''}`}>
                <text x={zone.centre[0]} y={zone.centre[1] + (zone.id === 'la-atalaya' ? 80 : -78)} textAnchor="middle">
                  <tspan className="name">{zone.name}</tspan>
                  {zone.impactHours !== null && (
                    <tspan className="impact" x={zone.centre[0]} dy={34}>
                      {t('landing.how.impact', { hours: zone.impactHours })}
                    </tspan>
                  )}
                </text>
              </g>
            ))}
            {PINS.map(([x, y], index) => (
              <circle
                key={index}
                className={`mini-pin${statusOf[index] !== 'pending' ? ' done' : ''}`}
                cx={x}
                cy={y}
                r={11}
                fill={STATUS_COLOR[statusOf[index]]}
              />
            ))}
          </svg>
          <p className="mini-clock">
            {t('landing.how.clock', { time: formatSpanishClock(DAY_START + Math.min(minute, 1439) * 60000, intl) })}
          </p>
        </div>

        <div className="mini-side">
          <section className={`mini-call${step >= 2 ? ' live' : ''}`} aria-label={t('landing.how.call')}>
            <header className="mini-call-head">
              <span className="mini-call-icon">
                <Icon name="phone" size={18} />
              </span>
              <span className="mini-call-title">{t('landing.how.call')}</span>
              <span className={`mini-wave${speaking ? ' speaking' : ''}`} aria-hidden="true">
                <i />
                <i />
                <i />
                <i />
                <i />
              </span>
            </header>
            {step < 2 ? (
              <p className="mini-waiting">{t('landing.how.waiting')}</p>
            ) : (
              <ol className="mini-bubbles">
                {CALL_LINES.filter((line) => time >= line.from).map((line) => {
                  const text = lines[line.key]
                  const shown = text.slice(0, Math.ceil(text.length * progress(time, line)))
                  return (
                    <li key={line.key} className={`mini-bubble ${line.who}`}>
                      <span className="mini-who">
                        {line.who === 'agent' ? t('landing.how.agent') : t('landing.how.resident')}
                      </span>
                      <span className="mini-said" aria-label={text}>
                        {shown}
                      </span>
                    </li>
                  )
                })}
              </ol>
            )}
          </section>

          <ul className="mini-strip" aria-label={t('status.strip')}>
            {STATUSES.map((status, index) => (
              <li
                key={status}
                className={`mini-tile ${status}${counts[index] > 0 ? ' filled' : ''}`}
                style={{ color: STATUS_COLOR[status], borderColor: STATUS_COLOR[status] }}
              >
                <span className="mini-tile-count">
                  <Icon name={STATUS_ICON[status]} size={16} />
                  {counts[index]}
                </span>
                <span className="mini-tile-label">{statusText[status]}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mini-controls">
        {!reduced && (
          <button
            type="button"
            className="mini-play"
            onClick={() => setPaused((p) => !p)}
            aria-label={paused ? t('landing.how.play') : t('landing.how.pause')}
          >
            <Icon name={paused ? 'play' : 'pause'} size={20} />
          </button>
        )}
        <p className="mini-honest">{t('landing.how.honest')}</p>
      </div>

      <ol className="mini-steps">
        {steps.map((s, index) => (
          <li key={s.title}>
            <button
              type="button"
              className={`mini-step tone-${index}${index === step ? ' active' : ''}${index < step ? ' past' : ''}`}
              onClick={() => jump(index)}
              aria-label={t('landing.how.jump', { step: index + 1, title: s.title })}
              aria-current={index === step ? 'step' : undefined}
            >
              <span className="mini-step-mark">
                <span className="mini-step-number">{index + 1}</span>
                <Icon name={STEP_ICONS[index]} size={22} />
              </span>
              <span className="mini-step-title">{s.title}</span>
              <span className="mini-step-body">{s.body}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  )
}
