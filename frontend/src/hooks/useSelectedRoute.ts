// The resident selected on the map and their evacuation route, by car or on foot.

import { useCallback, useEffect, useState } from 'react'
import type { FireArea, Route, TravelMode } from '../domain/triage'
import { fetchFireArea, fetchRoute } from '../services/api'

export type RouteStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface SelectedRoute {
  neighborId: string | null
  mode: TravelMode
  route: Route | null
  status: RouteStatus
  /** The area the routes avoid; loaded once, with the first route. */
  fireArea: FireArea | null
  select: (neighborId: string | null) => void
  setMode: (mode: TravelMode) => void
}

export function useSelectedRoute(): SelectedRoute {
  const [neighborId, setNeighborId] = useState<string | null>(null)
  const [mode, setMode] = useState<TravelMode>('car')
  const [route, setRoute] = useState<Route | null>(null)
  const [status, setStatus] = useState<RouteStatus>('idle')
  const [fireArea, setFireArea] = useState<FireArea | null>(null)

  const select = useCallback((next: string | null) => {
    setNeighborId(next)
    setRoute(null)
    setStatus(next === null ? 'idle' : 'loading')
  }, [])

  const changeMode = useCallback(
    (next: TravelMode) => {
      setMode(next)
      if (neighborId !== null) {
        setRoute(null)
        setStatus('loading')
      }
    },
    [neighborId],
  )

  useEffect(() => {
    if (neighborId === null) return
    let cancelled = false
    fetchRoute(neighborId, mode)
      .then((next) => {
        if (cancelled) return
        setRoute(next)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [neighborId, mode])

  const wantsFireArea = neighborId !== null && fireArea === null
  useEffect(() => {
    if (!wantsFireArea) return
    let cancelled = false
    fetchFireArea()
      .then((area) => {
        if (!cancelled) setFireArea(area)
      })
      .catch(() => {
        // The route still draws without the area; nothing to tell the user.
      })
    return () => {
      cancelled = true
    }
  }, [wantsFireArea])

  return { neighborId, mode, route, status, fireArea, select, setMode: changeMode }
}
