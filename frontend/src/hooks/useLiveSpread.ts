// Live mode's predicted spread: polls Deepfire's own simulations through the backend while live mode is on.

import { useEffect, useState } from 'react'
import { parseLiveSpread, type LiveSpread } from '../domain/liveSpread'
import { fetchLiveSpread } from '../services/api'

/** The backend caches for five minutes and Deepfire reruns a fire every few hours. */
const POLL_MS = 300_000

/** The latest completed run per active fire, or null until the first answer. */
export function useLiveSpread(enabled: boolean): LiveSpread | null {
  const [spread, setSpread] = useState<LiveSpread | null>(null)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    const load = () => {
      fetchLiveSpread()
        .then((response) => {
          if (!cancelled) setSpread(parseLiveSpread(response))
        })
        .catch(() => {
          // Keep showing the last good runs; the fires' own status reports an outage.
        })
    }
    load()
    const timer = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [enabled])

  return spread
}
