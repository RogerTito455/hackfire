// Triage state for the dashboard: polls the backend and exposes plain data.

import { useCallback, useEffect, useMemo, useState } from 'react'
import { countByStatus, type CrewAlert, type Neighbor, type Rescue, type StatusCounts } from '../domain/triage'
import { fetchAlerts, fetchNeighbors, fetchRescues, resetDemo } from '../services/api'

const POLL_MS = 2000

export interface Triage {
  neighbors: Neighbor[]
  rescues: Rescue[]
  /** Crew alerts for new rescues, newest first. */
  alerts: CrewAlert[]
  counts: StatusCounts
  online: boolean
  reset: () => Promise<void>
}

export function useTriage(): Triage {
  const [neighbors, setNeighbors] = useState<Neighbor[]>([])
  const [rescues, setRescues] = useState<Rescue[]>([])
  const [alerts, setAlerts] = useState<CrewAlert[]>([])
  const [online, setOnline] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const [nextNeighbors, nextRescues, nextAlerts] = await Promise.all([
        fetchNeighbors(),
        fetchRescues(),
        fetchAlerts(),
      ])
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
    await resetDemo()
    await refresh()
  }, [refresh])

  const counts = useMemo(() => countByStatus(neighbors), [neighbors])

  return { neighbors, rescues, alerts, counts, online, reset }
}
