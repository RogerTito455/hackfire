// The browser side of Vonage Video (#18): a resident's camera, and the coordinator watching it with
// live captions. The only file that knows the Vonage SDK; it loads on first use.

import type { VideoAccess } from '../domain/video'

export interface VideoCall {
  end: () => void
}

// Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: every await below either logs
// its failure here or runs inside `guarded`, so a failed step is seen in the console and never
// leaves a session connected.
async function sdk() {
  try {
    return (await import('@vonage/client-sdk-video')).default
  } catch (error) {
    console.error('The video library did not load', error)
    throw error
  }
}

/** Run the steps that follow `initSession`. If one fails, log it, leave the session and pass the error on. */
async function guarded<T>(session: { disconnect: () => void }, what: string, steps: () => Promise<T>): Promise<T> {
  try {
    return await steps()
  } catch (error) {
    console.error(`Video call: ${what} failed`, error)
    session.disconnect()
    throw error
  }
}

function connect(session: { connect: (token: string, done: (error?: Error) => void) => void }, token: string) {
  return new Promise<void>((resolve, reject) => session.connect(token, (error) => (error ? reject(error) : resolve())))
}

/** The resident's phone: the back camera, with captions published so the coordinator can read them. */
export async function publishCamera(access: VideoAccess, target: HTMLElement): Promise<VideoCall> {
  const OT = await sdk()
  const session = OT.initSession(access.application_id, access.session_id)
  return guarded(session, 'publishing the camera', async () => {
    await connect(session, access.token)
    const publisher = OT.initPublisher(target, {
      facingMode: 'environment',
      mirror: false, // the back camera: show the scene as it is
      publishCaptions: true,
      insertMode: 'append',
      width: '100%',
      height: '100%',
    })
    await new Promise<void>((resolve, reject) => session.publish(publisher, (error) => (error ? reject(error) : resolve())))
    return { end: () => void session.disconnect() }
  })
}

/** The coordinator: the resident's stream in `target`, and each caption as it arrives. */
export async function watchCamera(
  access: VideoAccess,
  target: HTMLElement,
  onCaption: (text: string) => void,
  onEnded: () => void,
): Promise<VideoCall> {
  const OT = await sdk()
  const session = OT.initSession(access.application_id, access.session_id)
  session.on('streamCreated', (event) => {
    const subscriber = session.subscribe(event.stream, target, {
      insertMode: 'append',
      width: '100%',
      height: '100%',
      subscribeToCaptions: true,
    })
    subscriber.on('captionReceived', (caption) => onCaption(caption.caption))
  })
  session.on('streamDestroyed', () => onEnded())
  return guarded(session, 'watching the camera', async () => {
    await connect(session, access.token)
    return { end: () => void session.disconnect() }
  })
}

function publish(session: { publish: (p: never, done: (error?: Error) => void) => unknown }, publisher: unknown) {
  return new Promise<void>((resolve, reject) =>
    session.publish(publisher as never, (error) => (error ? reject(error) : resolve())),
  )
}

/** The command post: its screen (the map and panels) and its microphone, with captions. It hears the crews. */
export async function shareScreen(access: VideoAccess, onEnded: () => void): Promise<VideoCall> {
  const OT = await sdk()
  const session = OT.initSession(access.application_id, access.session_id)
  const hidden = document.createElement('div')
  session.on('streamCreated', (event) => {
    session.subscribe(event.stream, hidden, { insertMode: 'append', subscribeToVideo: false })
  })
  return guarded(session, 'sharing the screen', async () => {
    await connect(session, access.token)
    const screen = OT.initPublisher(hidden, { videoSource: 'screen', publishCaptions: true, insertMode: 'append' })
    screen.on('streamDestroyed', () => onEnded()) // stopped from the browser's "Stop sharing"
    await publish(session, screen)
    return { end: () => void session.disconnect() }
  })
}

/** A crew's phone: the command post's screen in `target`, its own microphone, and each caption. */
export async function joinCrewRoom(
  access: VideoAccess,
  target: HTMLElement,
  onCaption: (text: string) => void,
): Promise<VideoCall> {
  const OT = await sdk()
  const session = OT.initSession(access.application_id, access.session_id)
  const hidden = document.createElement('div')
  session.on('streamCreated', (event) => {
    const screen = event.stream.videoType === 'screen'
    const subscriber = session.subscribe(event.stream, screen ? target : hidden, {
      insertMode: 'append',
      width: '100%',
      height: '100%',
      fitMode: 'contain',
      subscribeToVideo: screen,
      subscribeToCaptions: true,
    })
    subscriber.on('captionReceived', (caption) => onCaption(caption.caption))
  })
  return guarded(session, 'joining the crew room', async () => {
    await connect(session, access.token)
    const microphone = OT.initPublisher(hidden, { videoSource: null, publishCaptions: true, insertMode: 'append' })
    await publish(session, microphone)
    return { end: () => void session.disconnect() }
  })
}

