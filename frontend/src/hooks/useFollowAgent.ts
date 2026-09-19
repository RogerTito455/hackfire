// The dashboard follows the coordinator's voice agent (#10): when the agent asks for the route to
// a rescue, show that rescue's crew route on the map, once per request.

import { useEffect, useRef } from 'react'
import type { AgentFocus } from '../domain/triage'

export function useFollowAgent(focus: AgentFocus | null, show: (neighborId: string) => void): void {
  const seen = useRef<string | null>(null)
  const showRef = useRef(show)
  useEffect(() => {
    showRef.current = show
  }, [show])

  useEffect(() => {
    if (focus === null || focus.at === seen.current) return
    seen.current = focus.at
    showRef.current(focus.neighbor_id)
  }, [focus])
}
