// When everything happens, measured from the narration: each line starts after the one before it, so
// changing a line's words or voice moves everything after it and nothing needs retiming by hand.
// Visual beats hang off words (`beat('open-1', 'thirteen')`), so they land on the word being said.

import narration from './data/narration.json'
import { FPS } from './theme'

type Word = { text: string; startMs: number; endMs: number }
type NarrationLine = { id: string; scene: string; speaker: 'narrator' | 'agent' | 'resident'; text: string; subtitle?: string; file: string; durationMs: number; words: Word[] }

export type TimedLine = NarrationLine & { at: number; frames: number }
export type Scene = { id: string; start: number; end: number; lines: TimedLine[] }

const frames = (ms: number) => Math.round((ms / 1000) * FPS)

// Frames before a scene's first line: room for a sound or a picture to arrive first.
const LEAD: Record<string, number> = { open: 22, brand: 24, forecast: 20, call: 50, leadtime: 8, close: 12, handover: 16, scale: 14 }
// Frames after a scene's last line, before the next scene: a picture that needs to be seen.
const HOLD: Record<string, number> = { compare: 40, roadmap: 24, brand: 84, leadtime: 30, understood: 10, command: 16, close: 96, handover: 30, scale: 34 }
const GAP = 6 // between two sentences of the narrator
const TURN = 8 // between turns in the call

const LINES = (narration as { lines: NarrationLine[] }).lines

export const SCENES: Scene[] = (() => {
  const ids = [...new Set(LINES.map((l) => l.scene))]
  let start = 0
  return ids.map((id) => {
    let t = start + (LEAD[id] ?? 8)
    const lines = LINES.filter((l) => l.scene === id).map((l, i, all) => {
      if (i > 0) t += all[i - 1].speaker !== l.speaker || id === 'call' ? TURN : GAP
      const line = { ...l, at: t, frames: frames(l.durationMs) }
      t += line.frames
      return line
    })
    const scene = { id, start, end: t + (HOLD[id] ?? 8), lines }
    start = scene.end
    return scene
  })
})()

export const TOTAL = SCENES[SCENES.length - 1].end
export const ALL_LINES = SCENES.flatMap((s) => s.lines)

export const scene = (id: string) => {
  const found = SCENES.find((s) => s.id === id)
  if (!found) throw new Error(`No scene ${id}`)
  return found
}

export const line = (id: string) => {
  const found = ALL_LINES.find((l) => l.id === id)
  if (!found) throw new Error(`No line ${id}`)
  return found
}

/** The frame a word starts on: the first word of `id` that starts with `word`, case-insensitive. */
export const beat = (id: string, word: string, nth = 0) => {
  const l = line(id)
  const matches = l.words.filter((w) => w.text.toLowerCase().replace(/[^\p{L}\p{N}'-]/gu, '').startsWith(word.toLowerCase()))
  const w = matches[nth]
  if (!w) throw new Error(`No word "${word}" in ${id}`)
  return l.at + frames(w.startMs)
}

export const lineEnd = (id: string) => {
  const l = line(id)
  return l.at + l.frames
}

// Chapters: the number says where you are in the story, the bar how much is left.
export const CHAPTERS: [string, string, string[]][] = [
  ['01', 'That day', ['open', 'problem', 'compare']],
  ['02', 'The forecast', ['brand', 'forecast', 'leadtime']],
  ['03', 'The call', ['order', 'call', 'understood']],
  ['04', 'The rescue', ['rescue', 'handover', 'command']],
  ['05', 'Beyond this fire', ['scale', 'roadmap']],
  ['06', 'Listening back', ['close']],
]
