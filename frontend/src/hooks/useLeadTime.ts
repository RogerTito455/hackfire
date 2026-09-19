// Lead time for La Atalaya: loads the cached number once and says whether the replay has reached
// the moment the system first flagged the zone.

import { useEffect, useMemo, useState } from 'react'
import { isFlagged, type LeadTime } from '../domain/leadTime'
import { fetchLeadTime } from '../services/api'
import type { LoadStatus } from './useFireReplay'

export interface LeadTimeView {
  status: LoadStatus
  leadTime: LeadTime | null
  /** True once the replay time has passed the moment the zone was first flagged. */
  flagged: boolean
}

export function useLeadTime(time: number | null): LeadTimeView {
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [leadTime, setLeadTime] = useState<LeadTime | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchLeadTime()
      .then((loaded) => {
        if (cancelled) return
        setLeadTime(loaded)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const flagged = useMemo(() => isFlagged(leadTime, time), [leadTime, time])
  return { status, leadTime, flagged }
}
