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

/** Counts from 0 to `target` once `start` turns true, in `ms`; returns the current value. */
export function useCountUp(target: number, start: boolean, ms = 1400): number {
  const [value, setValue] = useState(() => (prefersReducedMotion() ? target : 0))
  const done = useRef(false)
  useEffect(() => {
    if (!start || done.current) return
    if (prefersReducedMotion()) {
      done.current = true
      setValue(target)
      return
    }
    let frame = 0
    const begin = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - begin) / ms)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(target * eased))
      if (progress < 1) frame = requestAnimationFrame(tick)
      else done.current = true
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [start, target, ms])
  return value
}
