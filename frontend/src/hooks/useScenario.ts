// The active scenario, loaded once: the map fits its box.

import { useEffect, useMemo, useState } from 'react'
import { scenarioBounds, type Bounds, type Scenario } from '../domain/scenario'
import { fetchScenario } from '../services/api'
import type { LoadStatus } from './useFireReplay'

export interface ScenarioView {
  status: LoadStatus
  scenario: Scenario | null
  /** The box the replay map fits; null until the scenario has loaded. */
  bounds: Bounds | null
}

export function useScenario(): ScenarioView {
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [scenario, setScenario] = useState<Scenario | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchScenario()
      .then((loaded) => {
        if (cancelled) return
        setScenario(loaded)
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // One array per scenario: the map refits whenever the box it is given changes identity.
  const bounds = useMemo(() => (scenario ? scenarioBounds(scenario) : null), [scenario])
  return { status, scenario, bounds }
}
