// The whole video: the map underneath, opaque scenes over it, the frame's chrome, and the sound.

import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion'
import { Backdrop, Header, SceneSources, Subtitles, Vignette } from './Chrome'
import { MapStage } from './MapStage'
import { Brand, Call, Close, Command, Compare, Handover, Problem, Roadmap, Scale } from './Scenes'
import envelope from './data/music-envelope.json'
import { ALL_LINES, SCENES, TOTAL, beat, line, lineEnd, scene } from './timeline'
import { FPS } from './theme'

// The music sits at MUSIC_LUFS between lines and about 9 dB lower under the voice (narration is at
// -16 LUFS). The generated track builds up by 10 dB or more, so each moment is turned down by how
// far its loudness (src/data/music-envelope.json) is over the target; nothing is turned up.
const MUSIC_LUFS = -24
const DUCK = 0.35
const LUFS: number[] = (envelope as { lufs: number[] }).lufs

function evenOut(frame: number): number {
  const second = frame / FPS
  // The power over the three seconds around this moment, so the level glides instead of stepping.
  const around = [second - 1, second, second + 1].map((s) => LUFS[Math.max(0, Math.min(LUFS.length - 1, Math.floor(s)))])
  const loudness = 10 * Math.log10(around.reduce((sum, l) => sum + Math.pow(10, l / 10), 0) / around.length)
  return Math.min(1, Math.pow(10, (MUSIC_LUFS - loudness) / 20))
}

const OPAQUE = ['problem', 'compare', 'brand', 'call', 'handover', 'command', 'scale', 'roadmap', 'close']

export function HackFireVideo() {
  const f = useCurrentFrame()
  const current = [...SCENES].reverse().find((s) => f >= s.start) ?? SCENES[0]
  // The map only needs drawing when no opaque scene fully covers it.
  const covered = SCENES.some((s) => OPAQUE.includes(s.id) && f >= s.start + 8 && f < s.end)
  return (
    <AbsoluteFill style={{ background: '#040817', overflow: 'hidden' }}>
      <Backdrop f={f} />
      {!covered && <MapStage f={f} />}
      <Problem f={f} />
      <Brand f={f} />
      <Call f={f} />
      <Handover f={f} />
      <Command f={f} />
      <Scale f={f} />
      <Compare f={f} />
      <Roadmap f={f} />
      <Close f={f} />
      <Vignette />
      <Header f={f} sceneId={current.id} />
      <SceneSources f={f} />
      <Subtitles f={f} />
      <Sound />
    </AbsoluteFill>
  )
}

function Sfx({ at, name, volume = 0.35 }: { at: number; name: string; volume?: number }) {
  return (
    <Sequence from={Math.max(0, Math.round(at))} durationInFrames={120}>
      <Audio src={staticFile(`audio/sfx/${name}.mp3`)} volume={volume} />
    </Sequence>
  )
}

function Sound() {
  const talking = ALL_LINES.map((l) => [l.at, l.at + l.frames] as const)
  return (
    <>
      {ALL_LINES.map((l) => (
        <Sequence key={l.id} from={l.at} durationInFrames={l.frames + 10}>
          <Audio src={staticFile(l.file)} />
        </Sequence>
      ))}
      {SCENES.slice(1).map((s) => (
        <Sfx key={s.id} at={s.start - 4} name="whoosh" volume={0.22} />
      ))}
      <Sfx at={beat('open-0', 'reached')} name="hit" volume={0.3} />
      <Sfx at={beat('open-1', 'thirty')} name="blip" />
      <Sfx at={beat('open-1', 'two')} name="blip" />
      <Sfx at={beat('problem-0', 'every') - 20} name="alert" volume={0.3} />
      <Sfx at={beat('problem-1', 'left')} name="tick" />
      <Sfx at={beat('problem-1', 'move')} name="tick" />
      <Sfx at={beat('problem-1', 'never')} name="tick" />
      <Sfx at={scene('brand').start + 6} name="hit" volume={0.32} />
      <Sfx at={lineEnd('brand-0')} name="scan" volume={0.25} />
      <Sfx at={scene('forecast').start} name="rewind" volume={0.4} />
      <Sfx at={beat('forecast-0', 'satellite')} name="scan" volume={0.3} />
      <Sfx at={beat('forecast-1', 'atalaya')} name="blip" />
      <Sfx at={beat('leadtime-0', 'nine')} name="hit" volume={0.28} />
      <Sfx at={beat('leadtime-1', 'six')} name="hit" volume={0.32} />
      <Sfx at={beat('order-0', 'approves')} name="stamp" volume={0.45} />
      <Sfx at={scene('call').start + 4} name="ring" volume={0.4} />
      <Sfx at={lineEnd('call-2') + 6} name="blip" volume={0.4} />
      <Sfx at={scene('understood').start + 14} name="hit" volume={0.3} />
      <Sfx at={beat('rescue-0', 'queued')} name="blip" />
      <Sfx at={beat('rescue-0', 'crews')} name="blip" />
      <Sfx at={scene('handover').start + 10} name="blip" volume={0.42} />
      <Sfx at={beat('handover-0', 'link')} name="tick" />
      <Sfx at={beat('handover-1', 'route')} name="scan" volume={0.28} />
      <Sfx at={beat('command-0', 'agent')} name="scan" volume={0.25} />
      <Sfx at={scene('scale').start + 6} name="scan" volume={0.25} />
      <Sfx at={beat('scale-1', 'point')} name="stamp" volume={0.32} />
      <Sfx at={scene('compare').start + 6} name="scan" volume={0.25} />
      <Sfx at={beat('compare-0', 'two')} name="tick" />
      <Sfx at={beat('rescue-1', 'closed')} name="tick" />
      <Sfx at={beat('rescue-1', 'close')} name="stamp" volume={0.35} />
      <Sfx at={line('roadmap-0').at} name="blip" />
      <Sfx at={beat('close-0', 'listens')} name="scan" volume={0.3} />
      <Sfx at={lineEnd('close-0') + 4} name="hit" volume={0.35} />
      <Audio
        src={staticFile('audio/music.mp3')}
        volume={(g) => {
          const fadeInOut = interpolate(g, [0, 24, TOTAL - 45, TOTAL], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          // Frames to the nearest speech: under the voice the music drops, and comes back over 12 frames.
          const away = Math.min(...talking.map(([a, b]) => (g < a - 6 ? a - 6 - g : g > b + 8 ? g - b - 8 : 0)))
          const duck = DUCK + (1 - DUCK) * Math.min(1, away / 12)
          return fadeInOut * evenOut(g) * duck
        }}
      />
    </>
  )
}
