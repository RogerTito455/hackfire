// Live mode: polls Deepfire's active fires through the backend while live mode is on.

import { useEffect, useState } from 'react'
import { parseLiveFires, type LiveFires } from '../domain/liveFires'
import type { LiveSpread } from '../domain/liveSpread'
import { fetchLiveFires } from '../services/api'
import { useLiveSpread } from './useLiveSpread'

/** The backend caches for a minute; polling faster would only return the same answer. */
const POLL_MS = 60_000

export type LiveStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface LiveMode {
  status: LiveStatus
  data: LiveFires | null
  /** Deepfire's own spread simulations of these fires; null until they first load. */
  spread: LiveSpread | null
}

export function useLiveFires(enabled: boolean): LiveMode {
  const [status, setStatus] = useState<LiveStatus>('idle')
  const [data, setData] = useState<LiveFires | null>(null)
  const spread = useLiveSpread(enabled)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    const load = () => {
      fetchLiveFires()
        .then((collection) => {
          if (cancelled) return
          setData(parseLiveFires(collection))
          setStatus('ready')
        })
        .catch(() => {
          // Keep showing the last good data; the status says it could not refresh.
          if (!cancelled) setStatus('error')
        })
    }
    load()
    const timer = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [enabled])

  return { status: enabled && status === 'idle' ? 'loading' : status, data, spread }
}
