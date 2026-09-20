// The crews' room (Vonage): the command post shares its map, panels and voice with the fire crews,
// and each crew joins from a phone with the link.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { RoomState } from '../domain/video'
import { joinCrewRoomAccess, openCrewRoom } from '../services/api'
import { joinCrewRoom, shareScreen, type VideoCall } from '../services/videoCall'

export interface CrewRoomHost {
  state: RoomState
  /** The link to send the crews, once the room is open. */
  link: string | null
  start: () => Promise<void>
  stop: () => void
}

/** The command post's side: share the screen and the microphone with the crews. */
export function useCrewRoomHost(): CrewRoomHost {
  const [state, setState] = useState<RoomState>('idle')
  const [link, setLink] = useState<string | null>(null)
  const call = useRef<VideoCall | null>(null)

  const stop = useCallback(() => {
    call.current?.end()
    call.current = null
    setState('idle')
  }, [])

  useEffect(() => () => call.current?.end(), [])

  const start = useCallback(async () => {
    setState('starting')
    try {
      const room = await openCrewRoom()
      setLink(room.link)
      call.current = await shareScreen(room.access, () => setState('idle'))
      setState('live')
    } catch {
      setState('error')
    }
  }, [])

  return { state, link, start, stop }
}

export interface CrewRoomMember {
  state: RoomState
  caption: string
  videoRef: React.RefObject<HTMLDivElement | null>
}

/** A crew's side: watch the command post's map and talk to it. */
export function useCrewRoomMember(roomId: string): CrewRoomMember {
  const [state, setState] = useState<RoomState>('starting')
  const [caption, setCaption] = useState('')
  const videoRef = useRef<HTMLDivElement | null>(null)
  const joined = useRef(false)
  const call = useRef<VideoCall | null>(null)

  // Norma rct-prf-setstate-in-useeffect: neither setState is in the effect body. Both are the
  // continuation of an async IIFE (and its catch), because joining a room is a network round trip
  // whose outcome cannot be derived during render. `joined` keeps the effect to one run per room.
  useEffect(() => {
    if (joined.current) return
    joined.current = true
    ;(async () => {
      try {
        const access = await joinCrewRoomAccess(roomId)
        if (!videoRef.current) throw new Error('no video container')
        call.current = await joinCrewRoom(access, videoRef.current, setCaption)
        setState('live')
      } catch {
        setState('error')
      }
    })()
  }, [roomId])

  useEffect(() => () => call.current?.end(), [])

  return { state, caption, videoRef }
}
