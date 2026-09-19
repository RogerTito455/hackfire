// The browser side of Vonage Video (#18): a resident's camera, and the coordinator watching it with
// live captions. The only file that knows the Vonage SDK; it loads on first use.

import type { VideoAccess } from '../domain/video'

export interface VideoCall {
  end: () => void
}

async function sdk() {
  return (await import('@vonage/client-sdk-video')).default
}

function connect(session: { connect: (token: string, done: (error?: Error) => void) => void }, token: string) {
  return new Promise<void>((resolve, reject) => session.connect(token, (error) => (error ? reject(error) : resolve())))
}

/** The resident's phone: the back camera, with captions published so the coordinator can read them. */
export async function publishCamera(access: VideoAccess, target: HTMLElement): Promise<VideoCall> {
  const OT = await sdk()
  const session = OT.initSession(access.application_id, access.session_id)
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
  await connect(session, access.token)
  return { end: () => void session.disconnect() }
}
