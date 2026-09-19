// Predicted spread and zones at risk for the replay time. Loads the cached forecasts once, picks the
// ones in force at `time`, and tells the backend which moment the dashboard is on so the voice
// agent's answers match what the coordinator sees.

import { useEffect, useMemo, useRef, useState } from 'react'
import { spreadPolygons, type SpreadCollection, type SpreadPolygon } from '../domain/spread'
import {
  forecastIssuedAt,
  impactStep,
  parseZones,
  zonesAtRisk,
  type ImpactTable,
  type Zone,
  type ZoneImpact,
} from '../domain/zones'
import { fetchImpact, fetchSpread, fetchZones, setReplayTime } from '../services/api'
import type { LoadStatus } from './useFireReplay'

/** While the slider moves, tell the backend at most this often. */
const SYNC_MS = 500

export interface FireForecast {
  status: LoadStatus
  /** When the forecast in force was issued, epoch ms; null when there is none at this time. */
  issuedAt: number | null
  /** Polygons of the forecast in force, largest first. */
  spread: SpreadPolygon[]
  /** Zones the predicted fire reaches, soonest first. */
  zonesAtRisk: ZoneImpact[]
}

export function useFireForecast(time: number | null): FireForecast {
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [spread, setSpread] = useState<SpreadCollection | null>(null)
  const [zones, setZones] = useState<Zone[]>([])
  const [impact, setImpact] = useState<ImpactTable | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchSpread(), fetchZones(), fetchImpact()])
      .then(([nextSpread, nextZones, nextImpact]) => {
        if (cancelled) return
        setSpread(nextSpread)
        setZones(parseZones(nextZones))
        setImpact(nextImpact)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // The replay opens on its first hotspot, which is before any forecast: until the coordinator
  // moves the slider the backend keeps answering for the demo moment (HACKFIRE_DEMO_TIME).
  const openedAt = useRef<number | null>(null)
  const moved = useRef(false)
  const lastSync = useRef(0)
  useEffect(() => {
    if (time === null) return
    if (openedAt.current === null) openedAt.current = time
    if (time !== openedAt.current) moved.current = true
    if (!moved.current) return
    const timer = setTimeout(
      () => {
        lastSync.current = Date.now()
        // The dashboard works without the voice agent: a failed sync is not worth an error.
        setReplayTime(new Date(time).toISOString()).catch(() => {})
      },
      Math.max(0, lastSync.current + SYNC_MS - Date.now()),
    )
    return () => clearTimeout(timer)
  }, [time])

  // Derived from the 5-minute step, not from `time`: playback ticks every 100 ms and the map
  // should only be handed new data when the forecast or the minutes actually change.
  const step = useMemo(() => impactStep(impact, time), [impact, time])
  const issuedAt = useMemo(() => forecastIssuedAt(impact, step), [impact, step])
  const polygons = useMemo(() => (spread ? spreadPolygons(spread, issuedAt) : []), [spread, issuedAt])
  const atRisk = useMemo(() => zonesAtRisk(impact, zones, step), [impact, zones, step])

  return { status, issuedAt, spread: polygons, zonesAtRisk: atRisk }
}
