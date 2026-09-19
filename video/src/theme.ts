// The video's look: HackFire's night palette (DESIGN.md), where warm is the fire, blue is the way out
// and the status colours are people. One colour is the video's own: cyan is the voice agent, the part
// that listens.

import { loadFont as loadInter } from '@remotion/google-fonts/Inter'
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono'
import type { CSSProperties } from 'react'
import { spring } from 'remotion'

export const FPS = 30
export const W = 1920
export const H = 1080

export const SANS = loadInter('normal', { weights: ['400', '500', '600', '700', '800'], subsets: ['latin', 'latin-ext'] }).fontFamily
export const MONO = loadMono('normal', { weights: ['400', '500', '700'], subsets: ['latin', 'latin-ext'] }).fontFamily

export const C = {
  night: '#040817',
  mist: '#0b1330',
  paper: '#141e42',
  line: '#26325c',
  ink: '#eef2ff',
  ink2: '#a7b1d6',
  ink3: '#66729c',
  route: '#6f8cff',
  routeDeep: '#2447d6',
  agent: '#5fe3ff',
  zone: '#b36bff',
  fire: ['#ffe066', '#ff8c1a', '#d93025', '#5c1d14'],
  spread: ['#e8261a', '#f2551a', '#f7811f', '#f7811f', '#fbb02a', '#fbb02a', '#ffe066'],
  status: { pending: '#8a95b8', evacuating: '#19c28a', no_answer: '#f2b01e', needs_rescue: '#ff4a3d' },
} as const

export type Status = keyof typeof C.status

export const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
/** Cubic in-out, for camera moves and anything that travels. */
export const ease = (v: number) => {
  const t = clamp01(v)
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}
export const easeOut = (v: number) => 1 - Math.pow(1 - clamp01(v), 3)
export const sp = (t: number, damping = 13, stiffness = 180) => spring({ frame: t, fps: FPS, config: { damping, stiffness } })

/** Rise and settle, for anything that appears. */
export const pop = (t: number): CSSProperties => {
  const s = sp(t)
  return { opacity: clamp01(s * 1.6), transform: `translateY(${24 * (1 - Math.min(1, s))}px) scale(${0.92 + 0.08 * Math.min(1.03, s)})` }
}

export const fade = (t: number, frames = 8) => clamp01(t / frames)

export const text = (size: number, weight = 600, color: string = C.ink): CSSProperties => ({
  fontFamily: SANS,
  fontWeight: weight,
  fontSize: size,
  color,
  lineHeight: 1.2,
})

export const mono = (size: number, weight = 500, color: string = C.ink2): CSSProperties => ({
  fontFamily: MONO,
  fontWeight: weight,
  fontSize: size,
  color,
  lineHeight: 1.25,
  fontVariantNumeric: 'tabular-nums',
})

/** Local time in Spain (CEST, UTC+2 in July) for a replay minute counted from 22 July 00:00 UTC. */
export const clock = (minutes: number) => {
  const local = Math.floor(minutes) + 120
  const day = 22 + Math.floor(local / 1440)
  const hh = Math.floor((local % 1440) / 60)
  const mm = Math.floor(local % 60)
  return { day: `${day} July 2026`, time: `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}` }
}
