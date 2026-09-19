// A voice conversation with an agent in the browser: a resident's call taken on the dashboard when
// no phone can ring (#8), or the coordinator asking about rescues (#10). The dashboard's usual
// polling shows what the conversation changes.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ConversationState, WebSession } from '../domain/voice'
import { createCoordinatorSession, createWebSession } from '../services/api'
import { joinConversation, type Conversation } from '../services/voiceSession'

export interface Conversations {
  /** Who the conversation is about (a resident's id), or was last started for. */
  neighborId: string | null
  state: ConversationState
  start: (neighborId: string) => Promise<void>
  hangUp: () => void
}

/** The coordinator's own conversation with the coordinator agent (#10). */
export interface CoordinatorConversation {
  state: ConversationState
  start: () => void
  hangUp: () => void
}

export interface VoiceConversations {
  /** Take a resident's call on the dashboard, as that resident (#8). */
  resident: Conversations
  coordinator: CoordinatorConversation
}

/** Both conversations, one at a time: the microphone must reach one agent only. */
export function useVoiceConversations(): VoiceConversations {
  const resident = useConversation(createWebSession)
  const coordinator = useConversation(createCoordinatorSession)
  return {
    resident: {
      ...resident,
      start: (neighborId: string) => {
        coordinator.hangUp()
        return resident.start(neighborId)
      },
    },
    coordinator: {
      state: coordinator.state,
      start: () => {
        resident.hangUp()
        void coordinator.start('coordinator')
      },
      hangUp: coordinator.hangUp,
    },
  }
}

function useConversation(openSession: (id: string) => Promise<WebSession>): Conversations {
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
      const session = await openSession(id)
      if (attempt.current !== mine) return // hung up while the session was being created
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
  }, [openSession])

  // Also cancels a conversation still connecting: bumping the attempt makes it hang up on arrival.
  const hangUp = useCallback(() => {
    attempt.current += 1
    const conversation = current.current
    current.current = null
    setState('idle')
    conversation?.hangUp()
  }, [])

  return { neighborId, state, start, hangUp }
}
