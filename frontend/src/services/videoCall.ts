// The browser side of Vonage Video (#18): a resident's camera, and the coordinator watching it with
// live captions. The only file that knows the Vonage SDK; it loads on first use.

import type { VideoAccess } from '../domain/video'

export interface VideoCall {
  end: () => void
}

async function sdk() {
  try {
    return (await import('@vonage/client-sdk-video')).default
  } catch (error) {
    throw new Error('The video library did not load', { cause: error })
  }
}

type Session = ReturnType<Awaited<ReturnType<typeof sdk>>['initSession']>

// Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: every function below runs each
// of its awaits inside its own try/catch. A failed step is logged, and the session it had opened is
// left, so a failure never leaves one connected; the error still reaches the caller.
function abandon(session: Session | null, what: string, error: unknown): void {
  console.error(`Video call: ${what} failed`, error)
  session?.disconnect()
}

function connect(session: { connect: (token: string, done: (error?: Error) => void) => void }, token: string) {
  return new Promise<void>((resolve, reject) => session.connect(token, (error) => (error ? reject(error) : resolve())))
}

function publish(session: { publish: (p: never, done: (error?: Error) => void) => unknown }, publisher: unknown) {
  return new Promise<void>((resolve, reject) =>
    session.publish(publisher as never, (error) => (error ? reject(error) : resolve())),
  )
}

/** The resident's phone: the back camera, with captions published so the coordinator can read them. */
export async function publishCamera(access: VideoAccess, target: HTMLElement): Promise<VideoCall> {
  let session: Session | null = null
  try {
    const OT = await sdk()
    const current = OT.initSession(access.application_id, access.session_id)
    session = current
    await connect(current, access.token)
    const publisher = OT.initPublisher(target, {
      facingMode: 'environment',
      mirror: false, // the back camera: show the scene as it is
      publishCaptions: true,
      insertMode: 'append',
      width: '100%',
      height: '100%',
    })
    await publish(current, publisher)
    return { end: () => void current.disconnect() }
  } catch (error) {
    abandon(session, 'publishing the camera', error)
    throw error
  }
}

/** The coordinator: the resident's stream in `target`, and each caption as it arrives. */
export async function watchCamera(
  access: VideoAccess,
  target: HTMLElement,
  onCaption: (text: string) => void,
  onEnded: () => void,
): Promise<VideoCall> {
  let session: Session | null = null
  try {
    const OT = await sdk()
    const current = OT.initSession(access.application_id, access.session_id)
    session = current
    current.on('streamCreated', (event) => {
      const subscriber = current.subscribe(event.stream, target, {
        insertMode: 'append',
        width: '100%',
        height: '100%',
        subscribeToCaptions: true,
      })
      subscriber.on('captionReceived', (caption) => onCaption(caption.caption))
    })
    current.on('streamDestroyed', () => onEnded())
    await connect(current, access.token)
    return { end: () => void current.disconnect() }
  } catch (error) {
    abandon(session, 'watching the camera', error)
    throw error
  }
}

/** The command post: its screen (the map and panels) and its microphone, with captions. It hears the crews. */
export async function shareScreen(access: VideoAccess, onEnded: () => void): Promise<VideoCall> {
  let session: Session | null = null
  try {
    const OT = await sdk()
    const current = OT.initSession(access.application_id, access.session_id)
    session = current
    const hidden = document.createElement('div')
    current.on('streamCreated', (event) => {
      current.subscribe(event.stream, hidden, { insertMode: 'append', subscribeToVideo: false })
    })
    await connect(current, access.token)
    const screen = OT.initPublisher(hidden, { videoSource: 'screen', publishCaptions: true, insertMode: 'append' })
    screen.on('streamDestroyed', () => onEnded()) // stopped from the browser's "Stop sharing"
    await publish(current, screen)
    return { end: () => void current.disconnect() }
  } catch (error) {
    abandon(session, 'sharing the screen', error)
    throw error
  }
}

/** A crew's phone: the command post's screen in `target`, its own microphone, and each caption. */
export async function joinCrewRoom(
  access: VideoAccess,
  target: HTMLElement,
  onCaption: (text: string) => void,
): Promise<VideoCall> {
  let session: Session | null = null
  try {
    const OT = await sdk()
    const current = OT.initSession(access.application_id, access.session_id)
    session = current
    const hidden = document.createElement('div')
    current.on('streamCreated', (event) => {
      const screen = event.stream.videoType === 'screen'
      const subscriber = current.subscribe(event.stream, screen ? target : hidden, {
        insertMode: 'append',
        width: '100%',
        height: '100%',
        fitMode: 'contain',
        subscribeToVideo: screen,
        subscribeToCaptions: true,
      })
      subscriber.on('captionReceived', (caption) => onCaption(caption.caption))
    })
    await connect(current, access.token)
    const microphone = OT.initPublisher(hidden, { videoSource: null, publishCaptions: true, insertMode: 'append' })
    await publish(current, microphone)
    return { end: () => void current.disconnect() }
  } catch (error) {
    abandon(session, 'joining the crew room', error)
    throw error
  }
}
