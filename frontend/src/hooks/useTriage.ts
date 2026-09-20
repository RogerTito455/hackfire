// Triage state for the dashboard: polls the backend and exposes plain data.

import { useCallback, useEffect, useMemo, useState } from 'react'
import { countByStatus, type AgentFocus, type CrewAlert, type Neighbor, type Rescue, type StatusCounts } from '../domain/triage'
import { fetchAlerts, fetchFocus, fetchNeighbors, fetchRescues, resetDemo } from '../services/api'

const POLL_MS = 2000

export interface Triage {
  neighbors: Neighbor[]
  rescues: Rescue[]
  /** Crew alerts for new rescues, newest first. */
  alerts: CrewAlert[]
  /** The rescue the voice agent last asked the route for (#10), or null. */
  focus: AgentFocus | null
  counts: StatusCounts
  online: boolean
  reset: () => Promise<void>
  /** Poll now rather than on the next tick. */
  refresh: () => Promise<void>
}

export function useTriage(): Triage {
  const [neighbors, setNeighbors] = useState<Neighbor[]>([])
  const [rescues, setRescues] = useState<Rescue[]>([])
  const [alerts, setAlerts] = useState<CrewAlert[]>([])
  const [focus, setFocus] = useState<AgentFocus | null>(null)
  const [online, setOnline] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const [nextNeighbors, nextRescues, nextAlerts, nextFocus] = await Promise.all([
        fetchNeighbors(),
        fetchRescues(),
        fetchAlerts(),
        fetchFocus(),
      ])
      setFocus(nextFocus)
      setNeighbors(nextNeighbors)
      setRescues(nextRescues)
      setAlerts(nextAlerts)
      setOnline(true)
    } catch {
      setOnline(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, POLL_MS)
    return () => clearInterval(timer)
  }, [refresh])

  const reset = useCallback(async () => {
    // Recommended by Norma — fixed with Claude Opus 5 via Claude Code
    // A reset against a backend that is down used to be an unhandled rejection behind a click that
    // did nothing. `online` is the error state this hook already owns and the connection pill
    // already shows, so the failure lands there; the refresh below clears it once it answers again.
    try {
      await resetDemo()
    } catch (error) {
      console.error('demo reset failed', error)
      setOnline(false)
    }
    await refresh()
  }, [refresh])

  const counts = useMemo(() => countByStatus(neighbors), [neighbors])

  return { neighbors, rescues, alerts, focus, counts, online, reset, refresh }
}
