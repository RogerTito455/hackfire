// Animation clocks for the landing page: whether an element is on screen, and a looping playhead
// in seconds driven by requestAnimationFrame. No colours, words or data here.

import { useEffect, useRef, useState, type RefObject } from 'react'

/** Whether the user asked the system for less motion. */
export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

/** True while `ref`'s element has at least `threshold` of itself on screen. */
export function useInView(ref: RefObject<Element | null>, threshold = 0.3): boolean {
  const [inView, setInView] = useState(false)
  // Norma rct-prf-setstate-in-useeffect: the first setInView is the fallback for a browser with no
  // IntersectionObserver (or a ref that never attached) — it runs at most once, since both deps are
  // stable, so there is no render cascade to remove. The second is the observer's own callback,
  // which is the only place an intersection can be known.
  useEffect(() => {
    const element = ref.current
    if (!element || typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold })
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref, threshold])
  return inView
}

/**
 * A playhead from 0 to `duration` seconds that loops while `playing`. Updates at most ~30 times
 * a second, which is plenty for an illustration and gentle on old phones.
 */
export function usePlayhead(duration: number, playing: boolean, initial = 0) {
  const [time, setTime] = useState(initial)
  const timeRef = useRef(initial)

  // Norma rct-prf-setstate-in-useeffect: setTime runs inside the requestAnimationFrame callback —
  // that is the clock, and it is already throttled to ~30 updates a second.
  useEffect(() => {
    if (!playing) return
    let frame = 0
    let last = performance.now()
    let shown = timeRef.current
    const tick = (now: number) => {
      const next = (timeRef.current + Math.min(0.1, (now - last) / 1000)) % duration
      last = now
      timeRef.current = next
      if (Math.abs(next - shown) >= 1 / 30) {
        shown = next
        setTime(next)
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, duration])

  const seek = (seconds: number) => {
    timeRef.current = seconds
    setTime(seconds)
  }
  return { time, seek }
}
