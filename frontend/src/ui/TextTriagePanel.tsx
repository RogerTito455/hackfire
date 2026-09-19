import { useState } from 'react'
import type { Neighbor, TriageStatus } from '../domain/triage'
import type { TextTriage } from '../hooks/useTextTriage'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { STATUS_COLOR, STATUS_ICON } from './theme'

interface TextTriagePanelProps {
  neighbor: Neighbor
  triage: TextTriage
}

const MANUAL: readonly TriageStatus[] = ['evacuating', 'no_answer', 'needs_rescue']

// If the call fails on stage: type what the resident said, or set the status by hand.
export function TextTriagePanel({ neighbor, triage }: TextTriagePanelProps) {
  const { t } = useI18n()
  const [text, setText] = useState('')

  return (
    <div className="text-triage">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (text.trim()) triage.classify(neighbor.id, text.trim())
        }}
      >
        <label htmlFor="typed-answer">{t('typed.question', { name: neighbor.name })}</label>
        <textarea
          id="typed-answer"
          rows={2}
          value={text}
          placeholder={t('typed.placeholder')}
          onChange={(event) => setText(event.target.value)}
          disabled={!triage.available || triage.sending}
        />
        <button type="submit" className="text-triage-send" disabled={!triage.available || triage.sending || !text.trim()}>
          {triage.sending ? t('typed.sending') : t('typed.send')}
        </button>
        {!triage.available && <p className="empty">{t('typed.noLlm')}</p>}
      </form>
      <div className="text-triage-manual" role="group" aria-label={t('typed.manual')}>
        {MANUAL.map((status) => (
          <button
            key={status}
            type="button"
            className="icon-button"
            style={{ color: STATUS_COLOR[status] }}
            disabled={triage.sending}
            onClick={() => triage.mark(neighbor.id, status)}
          >
            <Icon name={STATUS_ICON[status]} size={16} />
            {t(`status.${status}`)}
          </button>
        ))}
      </div>
      {triage.error && <p className="empty">{t(`typed.${triage.error}`)}</p>}
      {triage.result && (
        <p className="text-triage-result" style={{ color: STATUS_COLOR[triage.result.status] }}>
          {[
            t('typed.recorded', { status: t(`status.${triage.result.status}`) }),
            triage.result.people !== null && t('typed.people', { count: triage.result.people }),
            triage.result.mobility,
          ]
            .filter(Boolean)
            .join(', ')}
        </p>
      )}
    </div>
  )
}
