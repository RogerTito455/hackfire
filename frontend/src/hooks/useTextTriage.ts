// The demo's last resort (#13): classify a typed answer, or set the status by hand.

import { useCallback, useEffect, useState } from 'react'
import type { TextClassification } from '../domain/textTriage'
import type { TriageStatus } from '../domain/triage'
import { fetchTextTriageAvailable, reportStatus, triageFromText } from '../services/api'

/** What went wrong, as a code the UI turns into words. */
export type TextTriageError = 'classifyFailed' | 'recordFailed'

export interface TextTriage {
  /** Whether an LLM is configured; without one only the buttons work. */
  available: boolean
  sending: boolean
  result: TextClassification | null
  error: TextTriageError | null
  classify: (neighborId: string, text: string) => Promise<void>
  mark: (neighborId: string, status: TriageStatus) => Promise<void>
  clear: () => void
}

export function useTextTriage(): TextTriage {
  const [available, setAvailable] = useState(false)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<TextClassification | null>(null)
  const [error, setError] = useState<TextTriageError | null>(null)

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
      setError('classifyFailed')
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
      setError('recordFailed')
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
