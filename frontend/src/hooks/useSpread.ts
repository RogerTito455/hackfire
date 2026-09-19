// The predicted spread and the places at risk at the replay time. Follows the slider in 15-minute
// steps, waiting for it to settle, and keeps showing the last answer while the next one loads.

import { useEffect, useState } from 'react'
import { snapToStep, type SpreadCollection, type ZoneRiskList, type ZoneShapes } from '../domain/spread'
import { fetchSpread, fetchZoneRisk, fetchZoneShapes } from '../services/api'

const SETTLE_MS = 250

export type SpreadStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface Spread {
  status: SpreadStatus
  cone: SpreadCollection | null
  risk: ZoneRiskList | null
  /** Zone outlines, loaded once. */
  shapes: ZoneShapes | null
}

export function useSpread(time: number | null, enabled: boolean): Spread {
  const [cone, setCone] = useState<SpreadCollection | null>(null)
  const [risk, setRisk] = useState<ZoneRiskList | null>(null)
  const [shapes, setShapes] = useState<ZoneShapes | null>(null)
  const [status, setStatus] = useState<SpreadStatus>('idle')

  const step = time === null ? null : snapToStep(time)

  useEffect(() => {
    if (!enabled || shapes !== null) return
    let cancelled = false
    fetchZoneShapes()
      .then((next) => {
        if (!cancelled) setShapes(next)
      })
      .catch(() => {
        // Without outlines the panel still lists the places; the map just draws no zones.
      })
    return () => {
      cancelled = true
    }
  }, [enabled, shapes])

  useEffect(() => {
    if (!enabled || step === null) return
    let cancelled = false
    const timer = setTimeout(() => {
      setStatus('loading')
      Promise.all([fetchSpread(step), fetchZoneRisk(step)])
        .then(([nextCone, nextRisk]) => {
          if (cancelled) return
          setCone(nextCone)
          setRisk(nextRisk)
          setStatus('ready')
        })
        .catch(() => {
          if (!cancelled) setStatus('error')
        })
    }, SETTLE_MS)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [enabled, step])

  return { status, cone, risk, shapes }
}
