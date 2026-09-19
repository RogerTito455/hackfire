// Live operations for the live fire the coordinator selects: places at risk, alert drafts and roads to
// close. Fetched for that fire only, and refreshed while it stays selected.

import { useEffect, useState } from 'react'
import { parseLiveOperations, type LiveOperations } from '../domain/liveOperations'
import { simulationFor, type LiveSpread } from '../domain/liveSpread'
import { fetchLiveOperations } from '../services/api'

/** Times to impact count down and Deepfire reruns a fire every few hours; the backend caches the places. */
const POLL_MS = 300_000

/** `no-run`: Deepfire has not simulated this fire, so there is nothing to intersect with places. */
export type LiveOperationsStatus = 'idle' | 'loading' | 'ready' | 'error' | 'no-run'

export interface LiveOperationsView {
  fireId: string | null
  status: LiveOperationsStatus
  /** Only ever the selected fire's; null while it loads. */
  data: LiveOperations | null
  select: (fireId: string | null) => void
  retry: () => void
}

export function useLiveOperations(enabled: boolean, spread: LiveSpread | null): LiveOperationsView {
  const [fireId, setFireId] = useState<string | null>(null)
  const [data, setData] = useState<LiveOperations | null>(null)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  // Leaving live mode lets go of the selected fire.
  const [wasEnabled, setWasEnabled] = useState(enabled)
  if (enabled !== wasEnabled) {
    setWasEnabled(enabled)
    if (!enabled) {
      setFireId(null)
      setData(null)
      setFailed(false)
    }
  }
  // A new Deepfire run of the same fire is fetched again.
  const simulationId = fireId === null ? undefined : simulationFor(spread, fireId)?.simulationId

  useEffect(() => {
    if (!enabled || fireId === null || simulationId === undefined) return
    let cancelled = false
    const load = () => {
      fetchLiveOperations(fireId)
        .then((response) => {
          if (cancelled) return
          setData(parseLiveOperations(response))
          setFailed(false)
        })
        .catch(() => {
          // Keep the last good answer for this fire; the panel says it could not refresh.
          if (!cancelled) setFailed(true)
        })
    }
    load()
    const timer = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [enabled, fireId, simulationId, attempt])

  const select = (next: string | null) => {
    if (next === fireId) return
    setFireId(next)
    setData(null)
    setFailed(false)
  }

  const shown = enabled && data !== null && data.fireId === fireId ? data : null
  let status: LiveOperationsStatus = 'idle'
  if (enabled && fireId !== null) {
    if (spread !== null && simulationId === undefined) status = 'no-run'
    else if (shown !== null) status = failed ? 'error' : 'ready'
    else status = failed ? 'error' : 'loading'
  }

  return {
    fireId: enabled ? fireId : null,
    status,
    data: shown,
    select,
    retry: () => {
      setFailed(false)
      setAttempt((count) => count + 1)
    },
  }
}
