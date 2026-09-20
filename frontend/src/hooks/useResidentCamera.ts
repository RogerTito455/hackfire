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

  // Norma rct-prf-setstate-in-useeffect: every setState here is the continuation of an async IIFE
  // or its catch — opening the single-use link is a network round trip, so the outcome cannot be
  // derived during render. `opened` keeps it to one run.
  useEffect(() => {
    if (opened.current) return
    opened.current = true
    ;(async () => {
      try {
        const access = await joinVideo(linkId)
        if (access === 'used' || access === 'unknown') {
          setState('used')
          return
        }
        if (!videoRef.current) throw new Error('no video container')
        call.current = await publishCamera(access, videoRef.current)
        setState('live')
      } catch {
        setState('error')
      }
    })()
  }, [linkId])

  useEffect(() => () => call.current?.end(), [])

  return { state, videoRef }
}
