// The resident's side of #18: open the single-use link once and put the back camera on.

import { useEffect, useRef, useState } from 'react'
import type { CameraState } from '../domain/video'
import { joinVideo } from '../services/api'
import { publishCamera, type VideoCall } from '../services/videoCall'

export interface ResidentCamera {
  state: CameraState
  /** Where the camera preview goes. */
  videoRef: React.RefObject<HTMLDivElement | null>
}

export function useResidentCamera(linkId: string): ResidentCamera {
  const [state, setState] = useState<CameraState>('joining')
  const videoRef = useRef<HTMLDivElement | null>(null)
  // The link works once: never open it twice, even when React re-runs the effect in development.
  const opened = useRef(false)
  const call = useRef<VideoCall | null>(null)

  useEffect(() => {
    if (opened.current) return
    opened.current = true
    // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: the effect only starts the
    // work; the state is set from the promise that settles it, not inside the effect body.
    void openCamera(linkId, videoRef, call).then(setState)
  }, [linkId])

  useEffect(() => () => call.current?.end(), [])

  return { state, videoRef }
}

/** Open the link and publish the camera. Resolves to the state to show; it never rejects. */
async function openCamera(
  linkId: string,
  videoRef: React.RefObject<HTMLDivElement | null>,
  call: React.MutableRefObject<VideoCall | null>,
): Promise<CameraState> {
  try {
    const access = await joinVideo(linkId)
    if (access === 'used' || access === 'unknown') return 'used'
    if (!videoRef.current) throw new Error('no video container')
    call.current = await publishCamera(access, videoRef.current)
    return 'live'
  } catch (error) {
    console.error('The camera did not start', error)
    return 'error'
  }
}
