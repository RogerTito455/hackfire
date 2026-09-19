// Live video from a resident who needs rescue (#18). Types only. No React, no fetch, no styling.

/** Whether Vonage is set up, and whether the link can be texted or must be passed on by hand. */
export interface VideoCapabilities {
  video: boolean
  sms: boolean
}

/** The single-use link that opens a resident's camera. Never carries their phone number. */
export interface RescueVideoLink {
  neighbor_id: string
  link: string
  sms_sent: boolean
}

/** What a browser needs to join a resident's video: Vonage's application id, the session, a token. */
export interface VideoAccess {
  application_id: string
  session_id: string
  token: string
}

/** The coordinator's side: waiting for the resident to open the link, or a token to watch them. */
export interface RescueVideo {
  neighbor_id: string
  joined: boolean
  access: VideoAccess | null
}

/** The resident's page: joining, on camera, a link already used, or a failure. */
export type CameraState = 'joining' | 'live' | 'used' | 'error'

/** The coordinator's view of one resident: link sent and waiting, or watching them live. */
export type WatchState = 'waiting' | 'live' | 'ended' | 'error'

/** The crews' room: the link crews open, and the command post's token to share its screen. */
export interface CrewRoom {
  link: string
  access: VideoAccess
}

export type RoomState = 'idle' | 'starting' | 'live' | 'error'

