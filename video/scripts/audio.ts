// The video's audio, from ElevenLabs: one clip per line of src/script.json, the sound effects and the
// music. Run from video/ (pnpm video:voice, video:sfx, video:music at the repo root).
//
//   node scripts/audio.ts lines   narration and the call, plus src/data/narration.json
//   node scripts/audio.ts sfx     public/audio/sfx/*.mp3
//   node scripts/audio.ts music   public/audio/music.mp3 (135 s, or the seconds given) and its loudness curve
//   node scripts/audio.ts envelope   src/data/music-envelope.json only, from the music there is
//   node scripts/audio.ts check   the plan's character count
//
// Every generation spends the plan's characters, so a line is only regenerated when its text, voice
// or settings change (a hash in narration.json), and a sound or the music only when its file is gone.
// The key is ELEVENLABS_API_KEY in the repo's .env; it is never printed.

import { execFileSync, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const PUBLIC = join(ROOT, 'public')
const NARRATION = join(ROOT, 'src/data/narration.json')
const API = 'https://api.elevenlabs.io'
const MODEL = 'eleven_multilingual_v2'

type Speaker = 'narrator' | 'agent' | 'resident'
type Voice = { id: string; name: string; settings: Record<string, number | boolean> }
// `say`, when set, is what the voice reads instead of `text` (a spelling for pronunciation); the screen
// still shows `text`, word for word, so both must have the same number of words.
type ScriptLine = { speaker: Speaker; text: string; say?: string; subtitle?: string }
type Script = { voices: Record<Speaker, Voice>; scenes: { id: string; lines: ScriptLine[] }[] }
export type Word = { text: string; startMs: number; endMs: number }
export type NarrationLine = ScriptLine & { id: string; scene: string; file: string; durationMs: number; words: Word[]; hash: string }

function apiKey(): string {
  const env = readFileSync(join(ROOT, '../.env'), 'utf-8')
  const named = env.match(/^ELEVENLABS_API_KEY=\s*"?([^"\s]+)/m)?.[1]
  // Tolerates a key pasted after other text on an ELEVEN line.
  const pasted = env.split('\n').find((line) => /ELEVEN/i.test(line))?.match(/sk_[0-9a-f]{48}/)?.[0]
  const key = named || pasted
  if (!key) throw new Error('No ELEVENLABS_API_KEY in the repo .env')
  return key
}

async function call(path: string, body?: object): Promise<Response> {
  const response = await fetch(API + path, {
    method: body ? 'POST' : 'GET',
    headers: { 'xi-api-key': apiKey(), 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) throw new Error(`ElevenLabs ${path}: HTTP ${response.status} ${(await response.text()).slice(0, 300)}`)
  return response
}

function ffmpeg(args: string[]): void {
  execFileSync('ffmpeg', ['-y', '-v', 'error', ...args])
}

function durationMs(file: string): number {
  const out = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file])
  return Math.round(Number(out.toString().trim()) * 1000)
}

// A resident is heard down a phone line; the agent a little cleaner, still not studio-bright.
const FILTER: Record<Speaker, string> = {
  narrator: 'loudnorm=I=-16:TP=-1.5:LRA=11',
  agent: 'highpass=f=140,lowpass=f=7200,loudnorm=I=-17:TP=-1.5:LRA=9',
  resident: 'highpass=f=320,lowpass=f=3300,acompressor=threshold=-20dB:ratio=3,loudnorm=I=-18:TP=-1.5:LRA=9',
}

function words(chars: string[], starts: number[], ends: number[], offset: number): Word[] {
  const out: Word[] = []
  let current: Word | null = null
  chars.forEach((char, i) => {
    if (/\s/.test(char)) {
      current = null
      return
    }
    if (!current) {
      current = { text: '', startMs: Math.max(0, Math.round((starts[i] - offset) * 1000)), endMs: 0 }
      out.push(current)
    }
    current.text += char
    current.endMs = Math.round((ends[i] - offset) * 1000)
  })
  return out
}

async function lines(): Promise<void> {
  const script: Script = JSON.parse(readFileSync(join(ROOT, 'src/script.json'), 'utf-8'))
  const previous: NarrationLine[] = existsSync(NARRATION) ? JSON.parse(readFileSync(NARRATION, 'utf-8')).lines : []
  const out: NarrationLine[] = []
  mkdirSync(join(PUBLIC, 'audio/lines'), { recursive: true })
  mkdirSync(dirname(NARRATION), { recursive: true })

  for (const scene of script.scenes) {
    for (const [index, line] of scene.lines.entries()) {
      const id = `${scene.id}-${index}`
      const file = `audio/lines/${id}.mp3`
      const voice = script.voices[line.speaker]
      const hash = createHash('sha1').update(JSON.stringify([MODEL, voice.id, voice.settings, line.say ?? line.text, FILTER[line.speaker]])).digest('hex').slice(0, 12)
      const kept = previous.find((p) => p.id === id && p.hash === hash)
      if (kept && existsSync(join(PUBLIC, file))) {
        out.push({ ...kept, ...line, id, scene: scene.id, file })
        continue
      }
      const answer = (await (
        await call(`/v1/text-to-speech/${voice.id}/with-timestamps?output_format=mp3_44100_128`, {
          text: line.say ?? line.text,
          model_id: MODEL,
          voice_settings: voice.settings,
        })
      ).json()) as { audio_base64: string; alignment: { characters: string[]; character_start_times_seconds: number[]; character_end_times_seconds: number[] } }
      const { characters, character_start_times_seconds: starts, character_end_times_seconds: ends } = answer.alignment
      const raw = join(PUBLIC, `audio/lines/${id}.raw.mp3`)
      writeFileSync(raw, Buffer.from(answer.audio_base64, 'base64'))
      // Cut the clip to the voice, a breath either side, so the timeline measures speech, not silence.
      const spoken = characters.map((c, i) => (/\s/.test(c) ? -1 : i)).filter((i) => i >= 0)
      const from = Math.max(0, starts[spoken[0]] - 0.05)
      const to = ends[spoken[spoken.length - 1]] + 0.15
      ffmpeg(['-i', raw, '-af', `atrim=start=${from}:end=${to},asetpts=PTS-STARTPTS,${FILTER[line.speaker]}`, '-ar', '44100', '-ac', '2', '-b:a', '192k', join(PUBLIC, file)])
      execFileSync('rm', [raw])
      const timed = words(characters, starts, ends, from)
      const shown = line.text.split(/\s+/)
      if (timed.length !== shown.length) throw new Error(`${id}: \`say\` and \`text\` must have the same number of words`)
      const entry: NarrationLine = { id, scene: scene.id, ...line, file, durationMs: durationMs(join(PUBLIC, file)), words: timed.map((w, i) => ({ ...w, text: shown[i] })), hash }
      out.push(entry)
      console.log(`${id}  ${(entry.durationMs / 1000).toFixed(2)} s  ${line.text.slice(0, 60)}`)
    }
  }
  writeFileSync(NARRATION, JSON.stringify({ about: 'Generated by scripts/audio.ts from script.json. Do not edit.', lines: out }, null, 1) + '\n')
  const total = out.reduce((sum, l) => sum + l.durationMs, 0)
  console.log(`${out.length} lines, ${(total / 1000).toFixed(1)} s of speech`)
}

// Short sounds for the edit. Kept deliberately synthetic: the video's world is an interface.
const SFX: Record<string, [string, number]> = {
  whoosh: ['fast clean futuristic digital whoosh, airy transition swipe, no music', 0.8],
  blip: ['soft futuristic user interface blip, short bright confirmation tone', 0.5],
  tick: ['tiny digital data tick, crisp short click, interface', 0.5],
  hit: ['deep cinematic sub bass impact with a short digital glitch tail', 1.6],
  rewind: ['fast digital rewind glitch, tape spin-back, stuttering electronic', 1.0],
  ring: ['european phone ringback tone, two long beeps, clean, no voice', 3.0],
  alert: ['smartphone emergency broadcast alert tone, harsh urgent electronic buzz', 1.6],
  stamp: ['digital approval confirmation, soft synth chord stab with a click', 0.7],
  scan: ['futuristic scanning sweep, soft digital shimmer rising', 1.4],
}

// Norma js-no-error-handling-async: `call` throws on any non-2xx from ElevenLabs and every
// generator here lets it through, so one failed sound stops the run instead of writing a truncated
// file. The single handler at the bottom of this script turns it into one line and exit code 1.
async function sfx(): Promise<void> {
  mkdirSync(join(PUBLIC, 'audio/sfx'), { recursive: true })
  for (const [name, [prompt, seconds]] of Object.entries(SFX)) {
    const file = join(PUBLIC, `audio/sfx/${name}.mp3`)
    if (existsSync(file)) continue
    const audio = await (await call('/v1/sound-generation', { text: prompt, duration_seconds: seconds, prompt_influence: 0.5 })).arrayBuffer()
    writeFileSync(file, Buffer.from(audio))
    console.log(`sfx/${name}.mp3  ${seconds} s`)
  }
}

const MUSIC_PROMPT =
  'Instrumental soundtrack for an artificial intelligence technology film. Pulsing analog synth arpeggios, ' +
  'deep sub bass, glitchy digital textures, airy pads, precise electronic percussion at 100 BPM. ' +
  'Opens dark and tense, builds steadily, lifts into a hopeful, confident resolution near the end. ' +
  'Serious and modern, no vocals, no drops, no cheesy EDM.'

// Longer than the video, which is about 125 s: a track that ends early leaves the close in silence.
async function music(seconds = Number(process.argv[3] ?? 135)): Promise<void> {
  const file = join(PUBLIC, 'audio/music.mp3')
  if (existsSync(file)) {
    console.log('audio/music.mp3 exists; delete it to make a new one')
  } else {
    const audio = await (await call('/v1/music', { prompt: MUSIC_PROMPT, music_length_ms: seconds * 1000 })).arrayBuffer()
    mkdirSync(dirname(file), { recursive: true })
    writeFileSync(file, Buffer.from(audio))
    console.log(`audio/music.mp3  ${(durationMs(file) / 1000).toFixed(1)} s`)
  }
  await envelope()
}

const ENVELOPE = join(ROOT, 'src/data/music-envelope.json')

/** The music's loudness second by second (EBU R128 momentary, LUFS), so the mix can even it out:
 * a generated track that builds up can be 10 dB louder at its peak than where it starts. */
async function envelope(): Promise<void> {
  const run = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', join(PUBLIC, 'audio/music.mp3'), '-af', 'ebur128', '-f', 'null', '-'], { encoding: 'utf-8' })
  const perSecond: number[][] = []
  for (const match of run.stderr.matchAll(/t:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+|-inf)/g)) {
    const second = Math.floor(Number(match[1]))
    const lufs = match[2] === '-inf' ? -70 : Number(match[2])
    ;(perSecond[second] ??= []).push(lufs)
  }
  const lufs = perSecond.map((values) => Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 10) / 10)
  writeFileSync(ENVELOPE, JSON.stringify({ about: 'Generated by scripts/audio.ts music: the music loudness per second, LUFS.', lufs }) + '\n')
  console.log(`src/data/music-envelope.json  ${lufs.length} s, ${Math.min(...lufs)} to ${Math.max(...lufs)} LUFS`)
}

async function check(): Promise<void> {
  const plan = (await (await call('/v1/user/subscription')).json()) as Record<string, unknown>
  console.log({ tier: plan.tier, used: plan.character_count, limit: plan.character_limit })
}

const commands: Record<string, () => Promise<void>> = { lines, sfx, music: () => music(), envelope, check }
const command = commands[process.argv[2] ?? '']
if (!command) {
  console.error(`Usage: node scripts/audio.ts ${Object.keys(commands).join('|')}`)
  process.exit(1)
}
// Recommended by Norma — fixed with Claude Opus 5 via Claude Code
// A failed run (no key, an error from ElevenLabs, ffmpeg missing) ends with one line and a
// non-zero exit code, instead of an unhandled rejection's stack trace.
try {
  await command()
} catch (error) {
  console.error(`scripts/audio.ts ${process.argv[2]}: ${error instanceof Error ? error.message : String(error)}`)
  process.exit(1)
}
