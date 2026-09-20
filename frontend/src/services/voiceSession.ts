// The browser side of a conversation with the voice agent: LiveKit's room, the microphone and the
// agent's audio. The only file that knows LiveKit.

import type { WebSession } from '../domain/voice'

export interface Conversation {
  hangUp: () => void
  /** Open or close the microphone mid-call: a noisy room must not talk over the resident. */
  setMicrophone: (on: boolean) => Promise<void>
}

/** Join the agent's room with the microphone on. `onEnded` runs once, whoever hangs up. */
export async function joinConversation(session: WebSession, onEnded: () => void): Promise<Conversation> {
  // Loaded on the first call only: LiveKit is half a megabyte the dashboard rarely needs.
  const { Room, RoomEvent, Track } = await import('livekit-client')
  const room = new Room()
  const players: HTMLMediaElement[] = []

  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind !== Track.Kind.Audio) return
    const player = track.attach()
    players.push(player)
    document.body.appendChild(player)
  })
  // The agent leaves the room when it ends the call; leave with it.
  room.on(RoomEvent.ParticipantDisconnected, () => {
    if (room.remoteParticipants.size === 0) void room.disconnect()
  })
  room.on(RoomEvent.Disconnected, () => {
    for (const player of players) player.remove()
    onEnded()
  })

  await room.connect(session.livekit_url, session.livekit_token)
  try {
    await room.localParticipant.setMicrophoneEnabled(true)
    await room.startAudio()
  } catch (error) {
    // A refused microphone must not leave the agent talking to nobody.
    await room.disconnect()
    throw error
  }
  return {
    hangUp: () => void room.disconnect(),
    setMicrophone: (on: boolean) => room.localParticipant.setMicrophoneEnabled(on).then(() => undefined),
  }
}
