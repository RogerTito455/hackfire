// The demo autopilot's switch. On, the backend plays a script of orders and call outcomes timed by the
// forecast as the replay clock moves; off, it puts the state back. It never places a call or sends an SMS.
// While it is on, it also holds the scripted calls and the recorded agent transcripts shown with them.

import { useCallback, useEffect, useState } from 'react'
import { AUTOPILOT_OFF, type Autopilot } from '../domain/autopilot'
import { fetchAutopilot, setAutopilot } from '../services/api'

export interface AutopilotControl {
  enabled: boolean
  busy: boolean
  /** The scripted calls and their transcripts; empty while it is off. */
  script: Autopilot
  /** Turn it on at the slider's moment (epoch ms), or off. */
  toggle: (replayTime: number | null) => Promise<void>
  /** Read it again, e.g. after a demo reset turned it off. */
  refresh: () => Promise<void>
}

/** `onChange` runs after each switch, so the triage state can refresh without waiting for its poll. */
export function useAutopilot(onChange?: () => void): AutopilotControl {
  const [script, setScript] = useState<Autopilot>(AUTOPILOT_OFF)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setScript(await fetchAutopilot())
    } catch (error) {
      // Offline: keep what we last knew; the connection pill already says so.
      // Recommended by Norma — fixed with Claude Opus 5 via Claude Code
      // Logged at debug level so the swallow is visible in the console, without turning an
      // expected offline poll into an error.
      console.debug('autopilot state unavailable', error)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const enabled = script.enabled
  const toggle = useCallback(
    async (replayTime: number | null) => {
      setBusy(true)
      try {
        const at = replayTime === null ? undefined : new Date(replayTime).toISOString()
        setScript(await setAutopilot(!enabled, at))
        onChange?.()
      } catch {
        await refresh()
      } finally {
        setBusy(false)
      }
    },
    [enabled, onChange, refresh],
  )

  return { enabled, busy, script, toggle, refresh }
}
