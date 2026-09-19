// The demo's last resort (#13): classify a typed answer, or set the status by hand.

import { useCallback, useEffect, useState } from 'react'
import type { TextClassification } from '../domain/textTriage'
import type { TriageStatus } from '../domain/triage'
import { fetchTextTriageAvailable, reportStatus, triageFromText } from '../services/api'

export interface TextTriage {
  /** Whether an LLM is configured; without one only the buttons work. */
  available: boolean
  sending: boolean
  result: TextClassification | null
  error: string | null
  classify: (neighborId: string, text: string) => Promise<void>
  mark: (neighborId: string, status: TriageStatus) => Promise<void>
  clear: () => void
}

export function useTextTriage(): TextTriage {
  const [available, setAvailable] = useState(false)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<TextClassification | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTextTriageAvailable()
      .then((answer) => setAvailable(answer.available))
      .catch(() => setAvailable(false))
  }, [])

  const classify = useCallback(async (neighborId: string, text: string) => {
    setSending(true)
    setError(null)
    try {
      setResult((await triageFromText(neighborId, text)).classification)
    } catch {
      setResult(null)
      setError('Could not classify it. Use the buttons.')
    } finally {
      setSending(false)
    }
  }, [])

  const mark = useCallback(async (neighborId: string, status: TriageStatus) => {
    setSending(true)
    setError(null)
    try {
      await reportStatus(neighborId, status)
      setResult({ status, people: null, mobility: null, observation: null })
    } catch {
      setError('Could not record it.')
    } finally {
      setSending(false)
    }
  }, [])

  const clear = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { available, sending, result, error, classify, mark, clear }
}
