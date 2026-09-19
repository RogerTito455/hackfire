// The coordinator's side of #18: ask a resident in the rescue queue for live video, wait for them to
// open the link, then watch them with Spanish captions. One resident at a time.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { RescueVideoLink, VideoCapabilities, WatchState } from '../domain/video'
import { fetchVideoCapabilities, requestRescueVideo, watchRescueVideo } from '../services/api'
import { watchCamera, type VideoCall } from '../services/videoCall'

const POLL_MS = 2000

export interface LiveVideo {
  neighborId: string
  state: WatchState
  /** The element the stream plays in, for the map to anchor next to the resident's pin. */
  element: HTMLElement
  /** The last caption: what the resident is saying, in Spanish. */
  caption: string
}

export interface RescueVideoControl {
  capabilities: VideoCapabilities
  /** The link sent to each resident asked for video, by neighbor id. */
  links: Record<string, RescueVideoLink>
  /** Neighbor id whose link is being created, if any. */
  requesting: string | null
  /** 'link' when the video link could not be created. */
  error: 'link' | null
  live: LiveVideo | null
  request: (neighborId: string) => Promise<void>
  stop: () => void
}

export function useRescueVideo(): RescueVideoControl {
  const [capabilities, setCapabilities] = useState<VideoCapabilities>({ video: false, sms: false })
  const [links, setLinks] = useState<Record<string, RescueVideoLink>>({})
  const [requesting, setRequesting] = useState<string | null>(null)
  const [error, setError] = useState<'link' | null>(null)
  const [live, setLive] = useState<LiveVideo | null>(null)
  const call = useRef<VideoCall | null>(null)

  useEffect(() => {
    fetchVideoCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities({ video: false, sms: false }))
  }, [])

  const stop = useCallback(() => {
    call.current?.end()
    call.current = null
    setLive(null)
  }, [])

  useEffect(() => () => call.current?.end(), [])

  const request = useCallback(
    async (neighborId: string) => {
      setRequesting(neighborId)
      setError(null)
      try {
        const link = await requestRescueVideo(neighborId)
        setLinks((current) => ({ ...current, [neighborId]: link }))
        stop()
        setLive({ neighborId, state: 'waiting', element: document.createElement('div'), caption: '' })
      } catch {
        setError('link')
      } finally {
        setRequesting(null)
      }
    },
    [stop],
  )

  // Waiting: poll until the resident opens the link, then join their stream. Keyed on who and where,
  // not the whole object, so a caption update does not restart the polling.
  const waitingId = live?.state === 'waiting' ? live.neighborId : null
  const waitingElement = live?.state === 'waiting' ? live.element : null
  useEffect(() => {
    if (!waitingId || !waitingElement) return
    let cancelled = false
    const timer = setInterval(async () => {
      try {
        const video = await watchRescueVideo(waitingId)
        if (cancelled || !video.joined || !video.access) return
        clearInterval(timer)
        call.current = await watchCamera(
          video.access,
          waitingElement,
          (caption) => setLive((current) => (current ? { ...current, caption } : current)),
          () => setLive((current) => (current ? { ...current, state: 'ended' } : current)),
        )
        if (!cancelled) setLive((current) => (current ? { ...current, state: 'live' } : current))
      } catch {
        if (!cancelled) setLive((current) => (current ? { ...current, state: 'error' } : current))
      }
    }, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [waitingId, waitingElement])

  return { capabilities, links, requesting, error, live, request, stop }
}
