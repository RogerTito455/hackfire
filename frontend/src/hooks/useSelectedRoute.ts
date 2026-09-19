// The resident selected on the map and their route: out by car or on foot, or the crew's way in.
// A crew alert links to `/?rescue=<neighbor id>`, which opens here with the crew's route.

import { useCallback, useEffect, useState } from 'react'
import type { FireArea, Route, RouteKind } from '../domain/triage'
import { fetchFireArea, fetchRescueRoute, fetchRoute } from '../services/api'

export type RouteStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface SelectedRoute {
  neighborId: string | null
  mode: RouteKind
  route: Route | null
  status: RouteStatus
  /** The area the routes avoid; loaded once, with the first route. */
  fireArea: FireArea | null
  select: (neighborId: string | null) => void
  setMode: (mode: RouteKind) => void
  /** Select a resident and show the crew's route to them. */
  showRescue: (neighborId: string) => void
}

function rescueFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get('rescue')
}

/** `language` only refetches the route, so its directions follow the dashboard's language;
 * `closures` changes when a road is closed or reopened, and the route is asked again. */
export function useSelectedRoute(language: string, closures = ''): SelectedRoute {
  const [neighborId, setNeighborId] = useState<string | null>(rescueFromUrl)
  const [mode, setMode] = useState<RouteKind>(() => (rescueFromUrl() === null ? 'car' : 'rescue'))
  const [route, setRoute] = useState<Route | null>(null)
  const [status, setStatus] = useState<RouteStatus>(() => (rescueFromUrl() === null ? 'idle' : 'loading'))
  const [areas, setAreas] = useState<{ residents: FireArea | null; crews: FireArea | null }>({
    residents: null,
    crews: null,
  })

  const select = useCallback((next: string | null) => {
    setNeighborId(next)
    setRoute(null)
    setStatus(next === null ? 'idle' : 'loading')
  }, [])

  const changeMode = useCallback(
    (next: RouteKind) => {
      setMode(next)
      if (neighborId !== null) {
        setRoute(null)
        setStatus('loading')
      }
    },
    [neighborId],
  )

  const showRescue = useCallback((next: string) => {
    setNeighborId(next)
    setMode('rescue')
    setRoute(null)
    setStatus('loading')
  }, [])

  useEffect(() => {
    if (neighborId === null) return
    let cancelled = false
    const load = mode === 'rescue' ? fetchRescueRoute(neighborId) : fetchRoute(neighborId, mode)
    load
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
  }, [neighborId, mode, language, closures])

  // Residents' routes avoid the fire plus an hour of predicted spread; crews' only what has burned.
  const crew = mode === 'rescue'
  const fireArea = crew ? areas.crews : areas.residents
  const wantsFireArea = neighborId !== null && fireArea === null
  useEffect(() => {
    if (!wantsFireArea) return
    let cancelled = false
    fetchFireArea(crew)
      .then((area) => {
        if (!cancelled) setAreas((current) => ({ ...current, [crew ? 'crews' : 'residents']: area }))
      })
      .catch(() => {
        // The route still draws without the area; nothing to tell the user.
      })
    return () => {
      cancelled = true
    }
  }, [wantsFireArea, crew])

  return { neighborId, mode, route, status, fireArea, select, setMode: changeMode, showRescue }
}
