// The fire crews' plan, refreshed as rescues come in; the coordinator sets how many crews there are.

import { useCallback, useEffect, useState } from 'react'
import type { CrewPlan } from '../domain/crewPlan'
import { fetchCrewPlan } from '../services/api'

const POLL_MS = 3000
const DEFAULT_CREWS = 2

export interface CrewPlanView {
  plan: CrewPlan | null
  crews: number
  setCrews: (crews: number) => void
}

export function useCrewPlan(): CrewPlanView {
  const [plan, setPlan] = useState<CrewPlan | null>(null)
  const [crews, setCrewsState] = useState(DEFAULT_CREWS)

  const refresh = useCallback(async () => {
    try {
      setPlan(await fetchCrewPlan(crews))
    } catch {
      // Keep the last plan; the next poll tries again.
    }
  }, [crews])

  useEffect(() => {
    const first = setTimeout(refresh, 0)
    const timer = setInterval(refresh, POLL_MS)
    return () => {
      clearTimeout(first)
      clearInterval(timer)
    }
  }, [refresh])

  const setCrews = useCallback((next: number) => setCrewsState(Math.max(1, Math.min(next, 10))), [])

  return { plan, crews, setCrews }
}
