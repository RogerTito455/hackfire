// Replay of the 22–24 July 2026 fire: loads the cached hotspots once and owns the replay clock.
// `time` is the shared replay time; other layers (spread, zones at risk, lead time) read it too.

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  clampTime,
  countObservedBy,
  HOUR,
  parseHotspots,
  timeRange,
  type Hotspot,
  type TimeRange,
} from '../domain/hotspots'
import { fetchHotspots } from '../services/api'

/** Fire time that passes per real second while playing. The whole replay takes about a minute. */
const PLAY_SPEED = HOUR
const TICK_MS = 100

export type LoadStatus = 'loading' | 'ready' | 'error'

export interface FireReplay {
  status: LoadStatus
  hotspots: Hotspot[]
  range: TimeRange | null
  /** Replay time in epoch milliseconds; null until the hotspots have loaded. */
  time: number | null
  /** Hotspots observed up to `time`. */
  observedCount: number
  playing: boolean
  setTime: (time: number) => void
  togglePlay: () => void
}

export function useFireReplay(): FireReplay {
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [time, setTimeState] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchHotspots()
      .then((collection) => {
        if (cancelled) return
        const parsed = parseHotspots(collection)
        setHotspots(parsed)
        setTimeState(parsed.length > 0 ? parsed[0].observedAt : null)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const range = useMemo(() => timeRange(hotspots), [hotspots])

  const setTime = useCallback(
    (next: number) => {
      if (range) setTimeState(clampTime(range, next))
    },
    [range],
  )

  // Playback stops by itself at the end of the range: `playing` is derived, not synced.
  const atEnd = range !== null && time !== null && time >= range.end
  const isPlaying = playing && !atEnd

  useEffect(() => {
    if (!isPlaying || !range) return
    const timer = setInterval(() => {
      setTimeState((current) => clampTime(range, (current ?? range.start) + (PLAY_SPEED * TICK_MS) / 1000))
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [isPlaying, range])

  const togglePlay = useCallback(() => {
    if (!range) return
    if (!isPlaying && atEnd) setTimeState(range.start)
    setPlaying(!isPlaying)
  }, [isPlaying, range, atEnd])

  const observedCount = useMemo(
    () => (time === null ? 0 : countObservedBy(hotspots, time)),
    [hotspots, time],
  )

  return { status, hotspots, range, time, observedCount, playing: isPlaying, setTime, togglePlay }
}
