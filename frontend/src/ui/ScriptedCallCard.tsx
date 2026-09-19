import { useEffect, useRef } from 'react'
import type { AutopilotCall, AutopilotTranscript } from '../domain/autopilot'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { STATUS_COLOR, STATUS_ICON, formatSpanishClock } from './theme'

interface ScriptedCallCardProps {
  call: AutopilotCall
  transcript: AutopilotTranscript
  /** The registry resident whose pin the scripted outcome set. */
  residentName: string | null
  shown: number
  typing: boolean
}

// The demo autopilot's call card. The bubbles are a real call of our resident agent with a resident that
// Galtea simulated, not a call to the resident on the map: the card says both, and the pin's outcome is
// scripted. The transcript types out turn by turn in its own short scroll box, and the status the agent
// recorded is its last line.
export function ScriptedCallCard({ call, transcript, residentName, shown, typing }: ScriptedCallCardProps) {
  const { t, intl } = useI18n()
  const list = useRef<HTMLOListElement>(null)

  // Keep the newest bubble in view inside the card's own scroll box.
  useEffect(() => {
    const element = list.current
    if (element) element.scrollTop = element.scrollHeight
  }, [shown, typing])

  const turns = transcript.turns.slice(0, shown)
  const next = transcript.turns[shown]
  return (
    <section className="group call-card" aria-label={t('autopilot.call.title')}>
      <h2 className="icon-button">
        <Icon name="phone" size={18} />
        {t('autopilot.call.title')}
      </h2>
      <p className="call-for">
        {t('autopilot.call.outcome', {
          name: residentName ?? '—',
          time: formatSpanishClock(Date.parse(call.at), intl),
        })}
      </p>
      <p className="call-label">{t('autopilot.call.label')}</p>
      <ol className="call-turns" ref={list}>
        {turns.map((turn, index) => (
          <li key={index} className={`call-bubble ${turn.speaker}`}>
            <span className="call-who">{t(`autopilot.call.${turn.speaker}`)}</span>
            {turn.text}
          </li>
        ))}
        {typing && next && (
          <li className={`call-bubble ${next.speaker} call-typing`} aria-hidden="true">
            <span className="call-dots">
              <span />
              <span />
              <span />
            </span>
          </li>
        )}
        {!typing && (
          <li className="call-recorded" role="status" style={{ ['--tone' as string]: STATUS_COLOR[transcript.status] }}>
            <Icon name={STATUS_ICON[transcript.status]} size={16} />
            {t('autopilot.call.recorded', { status: t(`status.${transcript.status}`) })}
          </li>
        )}
      </ol>
    </section>
  )
}
