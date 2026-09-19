import { useState } from 'react'
import type { Neighbor, TriageStatus } from '../domain/triage'
import type { TextTriage } from '../hooks/useTextTriage'
import { Icon } from './Icon'
import { STATUS_COLOR, STATUS_ICON, STATUS_LABEL } from './theme'

interface TextTriagePanelProps {
  neighbor: Neighbor
  triage: TextTriage
}

const MANUAL: readonly TriageStatus[] = ['evacuating', 'no_answer', 'needs_rescue']

// If the call fails on stage: type what the resident said, or set the status by hand.
export function TextTriagePanel({ neighbor, triage }: TextTriagePanelProps) {
  const [text, setText] = useState('')

  return (
    <div className="text-triage">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (text.trim()) triage.classify(neighbor.id, text.trim())
        }}
      >
        <label htmlFor="typed-answer">What did {neighbor.name} say?</label>
        <textarea
          id="typed-answer"
          rows={2}
          value={text}
          placeholder="“Mi madre no puede andar”"
          onChange={(event) => setText(event.target.value)}
          disabled={!triage.available || triage.sending}
        />
        <button type="submit" className="text-triage-send" disabled={!triage.available || triage.sending || !text.trim()}>
          {triage.sending ? 'Classifying…' : 'Classify and record'}
        </button>
        {!triage.available && <p className="empty">No LLM configured: use the buttons below.</p>}
      </form>
      <div className="text-triage-manual" role="group" aria-label="Set the status by hand">
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
            {STATUS_LABEL[status]}
          </button>
        ))}
      </div>
      {triage.error && <p className="empty">{triage.error}</p>}
      {triage.result && (
        <p className="text-triage-result" style={{ color: STATUS_COLOR[triage.result.status] }}>
          Recorded: {STATUS_LABEL[triage.result.status]}
          {triage.result.people !== null && ` · ${triage.result.people} people`}
          {triage.result.mobility && ` · ${triage.result.mobility}`}
        </p>
      )}
    </div>
  )
}
