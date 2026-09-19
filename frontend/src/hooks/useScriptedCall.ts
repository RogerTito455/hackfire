// The call card of the demo autopilot: when a scripted outcome with a recorded transcript lands on the
// replay clock, type that transcript out turn by turn. The transcript is a real call of our resident
// agent with a resident simulated by Galtea; the card says so.

import { useEffect, useState } from 'react'
import { callKey, latestRecordedCall, type Autopilot, type AutopilotCall, type AutopilotTranscript } from '../domain/autopilot'

// One turn every so often: slow enough to read a short line, fast enough for a demo.
const TURN_MS = 1100

export interface ScriptedCallView {
  call: AutopilotCall | null
  transcript: AutopilotTranscript | null
  /** How many turns are on screen; the recorded status shows once they all are. */
  shown: number
  typing: boolean
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
}

export function useScriptedCall(script: Autopilot, time: number | null): ScriptedCallView {
  const call = latestRecordedCall(script, time)
  const key = call ? callKey(call) : null
  const transcript = call?.transcript ? (script.transcripts[call.transcript] ?? null) : null
  const total = transcript?.turns.length ?? 0

  // `shown` belongs to one call: a new call starts again from its first turn.
  const [progress, setProgress] = useState<{ key: string | null; shown: number }>({ key: null, shown: 0 })
  const shown = progress.key === key ? progress.shown : prefersReducedMotion() ? total : 1

  useEffect(() => {
    if (key === null || shown >= total) return
    const timer = setTimeout(() => setProgress({ key, shown: shown + 1 }), TURN_MS)
    return () => clearTimeout(timer)
  }, [key, shown, total])

  return { call, transcript, shown: Math.min(shown, total), typing: key !== null && shown < total }
}
