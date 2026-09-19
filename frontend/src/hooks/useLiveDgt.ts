// Live mode: the DGT's official forest-fire incidents and road closures across Spain, polled while
// live mode is on. A DGT outage only hides the markers; nothing else depends on it.

import { useEffect, useState } from 'react'
import { parseDgtOverview, type DgtOverview } from '../domain/liveDgt'
import { fetchLiveDgt } from '../services/api'

/** The backend caches the feed for five minutes. */
const POLL_MS = 300_000

export function useLiveDgt(enabled: boolean): DgtOverview | null {
  const [data, setData] = useState<DgtOverview | null>(null)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    const load = () => {
      fetchLiveDgt()
        .then((response) => {
          if (!cancelled) setData(parseDgtOverview(response))
        })
        .catch(() => {
          // Keep the last good answer; with none, the map simply shows no DGT markers.
        })
    }
    load()
    const timer = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [enabled])

  return enabled ? data : null
}
