// Road closures: the list (polled, since crews can report one too), the "tap the map to close a road"
// mode, and who needs calling again because their route went through the road just closed.

import { useCallback, useEffect, useState } from 'react'
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

  const refresh = useCallback(async () => {
    try {
      setClosures(await fetchClosures())
    } catch (error) {
      // Keep the last list; the next poll tries again.
      // Recommended by Norma — fixed with Claude Opus 5 via Claude Code
      // Logged at debug level on purpose: this polls every POLL_MS, so an offline backend must
      // not fill the console with errors while the connection pill already says so.
      console.debug('closures poll failed', error)
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
