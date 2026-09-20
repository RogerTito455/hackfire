// The browser side of a conversation with the voice agent: LiveKit's room, the microphone and the
// agent's audio. The only file that knows LiveKit.

import type { WebSession } from '../domain/voice'

export interface Conversation {
  hangUp: () => void
}

/** Join the agent's room with the microphone on. `onEnded` runs once, whoever hangs up. */
export async function joinConversation(session: WebSession, onEnded: () => void): Promise<Conversation> {
  // Loaded on the first call only: LiveKit is half a megabyte the dashboard rarely needs.
  // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: each await below logs its failure.
  let livekit: typeof import('livekit-client')
  try {
    livekit = await import('livekit-client')
  } catch (error) {
    console.error('The voice library did not load', error)
    throw error
  }
  const { Room, RoomEvent, Track } = livekit
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

  try {
    await room.connect(session.livekit_url, session.livekit_token)
  } catch (error) {
    // Not disconnected here: a call that never got through must not report an end.
    console.error('Could not join the voice room', error)
    throw error
  }
  try {
    await room.localParticipant.setMicrophoneEnabled(true)
    await room.startAudio()
  } catch (error) {
    // A refused microphone must not leave the agent talking to nobody.
    console.error('The microphone or the audio did not start', error)
    await room.disconnect()
    throw error
  }
  return { hangUp: () => void room.disconnect() }
}
