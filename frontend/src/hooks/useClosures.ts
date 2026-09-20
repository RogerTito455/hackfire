// Road closures: the list (polled, since crews can report one too), the "tap the map to close a road"
// mode, and who needs calling again because their route went through the road just closed.

import { useCallback, useEffect, useRef, useState } from 'react'
import { closuresKey, type RoadClosure } from '../domain/closures'
import { closeRoad, fetchClosures, reopenRoad } from '../services/api'

const POLL_MS = 3000

export interface Closures {
  closures: RoadClosure[]
  /** Changes whenever the closures change: routes are asked again. */
  key: string
  /** The next tap on the map closes the road there. */
  closing: boolean
  setClosing: (closing: boolean) => void
  saving: boolean
  error: boolean
  close: (lon: number, lat: number) => Promise<void>
  reopen: (closureId: string) => Promise<void>
}

export function useClosures(): Closures {
  const [closures, setClosures] = useState<RoadClosure[]>([])
  const [closing, setClosing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  // Polled every few seconds: log the first failure of a run, not every poll while the backend is down.
  const refreshFailing = useRef(false)

  const refresh = useCallback(async () => {
    try {
      setClosures(await fetchClosures())
      refreshFailing.current = false
    } catch (error) {
      // Keep the last list; the next poll tries again.
      // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code
      if (!refreshFailing.current) console.warn('Could not read the road closures; keeping the last list', error)
      refreshFailing.current = true
    }
  }, [])

  useEffect(() => {
    const first = setTimeout(refresh, 0)
    const timer = setInterval(refresh, POLL_MS)
    return () => {
      clearTimeout(first)
      clearInterval(timer)
    }
  }, [refresh])

  const close = useCallback(
    async (lon: number, lat: number) => {
      setSaving(true)
      setError(false)
      try {
        await closeRoad(lon, lat)
        setClosing(false)
        await refresh()
      } catch {
        setError(true)
      } finally {
        setSaving(false)
      }
    },
    [refresh],
  )

  const reopen = useCallback(
    async (closureId: string) => {
      try {
        await reopenRoad(closureId)
        await refresh()
      } catch {
        setError(true)
      }
    },
    [refresh],
  )

  return { closures, key: closuresKey(closures), closing, setClosing, saving, error, close, reopen }
}
