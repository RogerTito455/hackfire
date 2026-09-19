// Take a resident's call in the browser: the agent talks to whoever answers as that resident, for
// when no phone can ring (#8). The dashboard's usual polling shows the pin change it causes.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConversationState } from '../domain/voice'
import { createWebSession } from '../services/api'
import { joinConversation, type Conversation } from '../services/voiceSession'

export interface Conversations {
  /** The resident the agent is talking to, or was last asked to. */
  neighborId: string | null
  state: ConversationState
  start: (neighborId: string) => Promise<void>
  hangUp: () => void
}

export function useConversation(): Conversations {
  const [neighborId, setNeighborId] = useState<string | null>(null)
  const [state, setState] = useState<ConversationState>('idle')
  const current = useRef<Conversation | null>(null)
  // Each start (and unmounting) bumps this, so a room that ends late cannot touch a newer one.
  const attempt = useRef(0)

  useEffect(
    () => () => {
      attempt.current += 1
      current.current?.hangUp()
    },
    [],
  )

  const start = useCallback(async (id: string) => {
    current.current?.hangUp()
    const mine = ++attempt.current
    setNeighborId(id)
    setState('connecting')
    try {
      const session = await createWebSession(id)
      const conversation = await joinConversation(session, () => {
        if (attempt.current !== mine) return
        current.current = null
        setState('idle')
      })
      if (attempt.current !== mine) {
        conversation.hangUp() // started again, or the dashboard went away, while connecting
        return
      }
      current.current = conversation
      setState('live')
    } catch {
      if (attempt.current === mine) setState('error')
    }
  }, [])

  const hangUp = useCallback(() => current.current?.hangUp(), [])

  return { neighborId, state, start, hangUp }
}
