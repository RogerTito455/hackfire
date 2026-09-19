// The demo autopilot's switch. On, the backend plays a fixed script of orders and call outcomes as the
// replay clock moves; off, it puts the state back. It never places a call or sends an SMS.

import { useCallback, useEffect, useState } from 'react'
import { fetchAutopilot, setAutopilot } from '../services/api'

export interface AutopilotControl {
  enabled: boolean
  busy: boolean
  /** Turn it on at the slider's moment (epoch ms), or off. */
  toggle: (replayTime: number | null) => Promise<void>
  /** Read it again, e.g. after a demo reset turned it off. */
  refresh: () => Promise<void>
}

/** `onChange` runs after each switch, so the triage state can refresh without waiting for its poll. */
export function useAutopilot(onChange?: () => void): AutopilotControl {
  const [enabled, setEnabled] = useState(false)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setEnabled((await fetchAutopilot()).enabled)
    } catch {
      // Offline: keep what we last knew; the connection pill already says so.
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const toggle = useCallback(
    async (replayTime: number | null) => {
      setBusy(true)
      try {
        const at = replayTime === null ? undefined : new Date(replayTime).toISOString()
        setEnabled((await setAutopilot(!enabled, at)).enabled)
        onChange?.()
      } catch {
        await refresh()
      } finally {
        setBusy(false)
      }
    },
    [enabled, onChange, refresh],
  )

  return { enabled, busy, toggle, refresh }
}
