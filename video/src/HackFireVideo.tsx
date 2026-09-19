// The whole video: the map underneath, opaque scenes over it, the frame's chrome, and the sound.

import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion'
import { Backdrop, Header, Subtitles, Vignette } from './Chrome'
import { MapStage } from './MapStage'
import { Brand, Call, Close, Command, Problem } from './Scenes'
import { ALL_LINES, SCENES, TOTAL, beat, lineEnd, scene } from './timeline'

const OPAQUE = ['problem', 'brand', 'call', 'command', 'close']

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
      <Command f={f} />
      <Close f={f} />
      <Vignette />
      <Header f={f} sceneId={current.id} />
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
      <Sfx at={beat('open-1', 'thirteen')} name="blip" />
      <Sfx at={beat('open-1', 'five')} name="blip" />
      <Sfx at={beat('problem-0', 'every') - 20} name="alert" volume={0.3} />
      <Sfx at={beat('problem-1', 'left')} name="tick" />
      <Sfx at={beat('problem-1', 'move')} name="tick" />
      <Sfx at={beat('problem-1', 'never')} name="tick" />
      <Sfx at={scene('brand').start + 6} name="hit" volume={0.45} />
      <Sfx at={lineEnd('brand-0')} name="scan" volume={0.25} />
      <Sfx at={scene('forecast').start} name="rewind" volume={0.4} />
      <Sfx at={beat('forecast-0', 'satellite')} name="scan" volume={0.3} />
      <Sfx at={beat('forecast-1', 'atalaya')} name="blip" />
      <Sfx at={beat('leadtime-0', 'nine')} name="hit" volume={0.4} />
      <Sfx at={beat('leadtime-1', 'six')} name="hit" volume={0.5} />
      <Sfx at={beat('order-0', 'approves')} name="stamp" volume={0.45} />
      <Sfx at={scene('call').start + 4} name="ring" volume={0.4} />
      <Sfx at={lineEnd('call-2') + 6} name="blip" volume={0.4} />
      <Sfx at={scene('understood').start + 14} name="hit" volume={0.3} />
      <Sfx at={beat('rescue-0', 'queued')} name="blip" />
      <Sfx at={beat('rescue-0', 'crews')} name="blip" />
      <Sfx at={beat('command-0', 'vonage')} name="scan" volume={0.25} />
      <Sfx at={beat('close-0', 'listens')} name="scan" volume={0.3} />
      <Sfx at={lineEnd('close-0') + 4} name="hit" volume={0.35} />
      <Audio
        src={staticFile('audio/music.mp3')}
        volume={(g) => {
          const base = interpolate(g, [0, 24, TOTAL - 60, TOTAL], [0, 0.42, 0.42, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          const speaking = talking.some(([a, b]) => g >= a - 6 && g <= b + 8)
          return base * (speaking ? 0.38 : 1)
        }}
      />
    </>
  )
}
