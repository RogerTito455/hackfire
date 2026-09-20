// What stays on screen across scenes: the background, the chapter and progress, the replay clock,
// the simulation label and the subtitles.

import { AbsoluteFill } from 'remotion'
import { Icon } from './Icon'
import { ALL_LINES, CHAPTERS, SCENES, type TimedLine } from './timeline'
import { C, MONO, clamp01, fade, mono, text } from './theme'

export function Backdrop({ f }: { f: number }) {
  return (
    <AbsoluteFill style={{ background: C.night }}>
      <AbsoluteFill
        style={{
          backgroundImage: 'linear-gradient(rgba(111,140,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(111,140,255,0.05) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          backgroundPosition: `${-(f * 0.25) % 64}px ${-(f * 0.12) % 64}px`,
        }}
      />
    </AbsoluteFill>
  )
}

/** Darkens the edges so the eye stays in the middle; drawn over everything but the text. */
export function Vignette() {
  return <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(2,5,15,0.75) 100%)', pointerEvents: 'none' }} />
}

export function Header({ f, sceneId }: { f: number; sceneId: string }) {
  const chapter = CHAPTERS.find(([, , ids]) => ids.includes(sceneId)) ?? CHAPTERS[0]
  const intro = fade(f - 4, 14)
  return (
    <div style={{ position: 'absolute', left: 48, right: 48, top: 36, opacity: intro, zIndex: 40 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 18px 8px 12px', borderRadius: 999, background: 'rgba(20,30,66,0.85)', border: `1px solid ${C.line}` }}>
          <Icon name="logo" size={28} color={C.fire[1]} />
          <span style={text(24, 800)}>HackFire</span>
        </div>
        <div key={chapter[0]} style={{ display: 'flex', alignItems: 'baseline', gap: 12, opacity: fade(f - chapterStart(chapter[2]), 10) }}>
          <span style={mono(20, 700, C.agent)}>{chapter[0]}</span>
          <span style={text(24, 600, C.ink2)}>{chapter[1]}</span>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 16, height: 4 }}>
        {CHAPTERS.map(([num, , ids]) => {
          const inChapter = SCENES.filter((s) => ids.includes(s.id))
          const a = inChapter[0].start
          const b = inChapter[inChapter.length - 1].end
          return (
            <div key={num} style={{ flex: b - a, borderRadius: 2, background: 'rgba(167,177,214,0.14)', overflow: 'hidden' }}>
              <div style={{ width: `${clamp01((f - a) / (b - a)) * 100}%`, height: '100%', background: C.ink2 }} />
            </div>
          )
        })}
      </div>
    </div>
  )
}

const chapterStart = (ids: string[]) => SCENES.find((s) => ids.includes(s.id))?.start ?? 0

/** The replay's clock, in Spain's time: the one number that tells you where in the day you are. */
export function Clock({ day, time, label, opacity }: { day: string; time: string; label: string; opacity: number }) {
  return (
    <div style={{ position: 'absolute', right: 48, top: 30, textAlign: 'right', opacity, zIndex: 40 }}>
      <div style={mono(56, 700, C.ink)}>{time}</div>
      <div style={{ ...mono(18, 500, C.ink2), marginTop: 2 }}>
        {day} <span style={{ color: C.ink3 }}>/ {label}</span>
      </div>
    </div>
  )
}

export function SimulationTag({ opacity, top = 132 }: { opacity: number; top?: number }) {
  if (opacity <= 0) return null
  return (
    <div style={{ position: 'absolute', right: 48, top, opacity, zIndex: 40, display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 999, border: `1px solid ${C.status.no_answer}`, color: C.status.no_answer, ...mono(17, 500, C.status.no_answer) }}>
      Simulation with demo residents
    </div>
  )
}

// Where the data each scene shows comes from, in small type at the bottom left. The press figures are
// the checked ones (docs/findings/2026-09-19-press-figures.md).
const SOURCES: Record<string, string> = {
  open: 'Hotspots: Deepfire (MTG, VIIRS, MODIS, Sentinel-3). Map: OpenStreetMap. 37,818 ha: Junta de CyL via Ávilared, 21 Aug, provisional. 3 km in 40 min, 1,300 evacuated from La Atalaya, 5 homes: Tribuna de Ávila and Ávilared, 23 July. 229 homes inside the burned area: Idealista via Ávilared.',
  problem: 'Source: ES-Alert text as published by Ávilared, 23 July 2026, translated from Spanish.',
  brand: 'Built on Deepfire (hotspots), SLNG (voice agents), openrouteservice and OpenStreetMap (routes), Vonage (texts).',
  forecast: "Hotspots: Deepfire, up to 15:30. Forecast: HackFire's spread model on those hotspots only. Map: OpenStreetMap.",
  leadtime: 'Lead time: HackFire, from Deepfire hotspots (docs/findings/2026-09-19-lead-time.md); a range over 2 to 5 km, as the site publishes it. Map: OpenStreetMap.',
  order: "Simulation with demo residents, at the demo autopilot's times. The order is HackFire's proposal, approved by hand.",
  call: 'Simulated call, condensed. Voice agent: SLNG. Route: openrouteservice on OpenStreetMap data.',
  understood: "Classified by the voice agent's language model (SLNG) from what the resident said. Map: OpenStreetMap.",
  rescue: "Routes: openrouteservice on OpenStreetMap. Dashed red: roads inside the area routes avoid, burned plus the next hour of HackFire's forecast.",
  command: 'Coordinator agent: SLNG. Crew route: openrouteservice on OpenStreetMap.',
  handover: "Crew SMS: the text HackFire sends (backend/app/locales), by Twilio or Vonage when a crew phone is set; otherwise the alert stays on the dashboard. Route: openrouteservice on OpenStreetMap.",
  scale: 'Live mode as built: Deepfire\'s active fires, official DGT incidents, and the alert drafts downloaded as CAP 1.2. Drafts only: HackFire sends nothing to the public.',
  compare: "Left: the ES-Alert of that day (Ávilared). Right: HackFire as built. 2 s is how often the dashboard refreshes the triage; the lead time is the replay's.",
  roadmap: 'Transfer to a person: SLNG transfer_call, on an outbound phone line (SIP).',
  devin: 'Planned (issue #19): Devin, by Cognition, iterating the spread model against real hotspots. Not running yet.',
}

export function SceneSources({ f }: { f: number }) {
  const s = [...SCENES].reverse().find((x) => f >= x.start)
  const words = s && SOURCES[s.id]
  if (!s || !words) return null
  const opacity = Math.min(fade(f - s.start - 6, 10), fade(s.end - f, 8))
  return <div style={{ position: 'absolute', left: 48, right: 48, bottom: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', opacity, ...mono(15, 400, C.ink2), zIndex: 60 }}>{words}</div>
}

const SPEAKER = { agent: ['Agent', C.agent], resident: ['Resident', C.ink] } as const

/** The line being said. The narrator's words light up as they are spoken; a Spanish line shows its
 * English subtitle, marked with who is talking. */
export function Subtitles({ f }: { f: number }) {
  const current = [...ALL_LINES].reverse().find((l) => f >= l.at - 3)
  if (!current) return null
  const next = ALL_LINES[ALL_LINES.indexOf(current) + 1]
  const until = Math.min(current.at + current.frames + 14, next ? next.at - 3 : Infinity)
  if (f > until) return null
  const opacity = Math.min(fade(f - current.at + 3, 5), fade(until - f, 5))
  return (
    <div style={{ position: 'absolute', left: 160, right: 160, bottom: 48, display: 'flex', justifyContent: 'center', zIndex: 50, opacity }}>
      <div style={{ maxWidth: 1500, padding: '14px 30px 16px', borderRadius: 18, background: 'rgba(4,8,23,0.82)', border: `1px solid ${C.line}`, textAlign: 'center' }}>
        {current.speaker === 'narrator' ? <Karaoke line={current} f={f} /> : <Spoken line={current} />}
      </div>
    </div>
  )
}

function Karaoke({ line, f }: { line: TimedLine; f: number }) {
  const ms = ((f - line.at) / 30) * 1000
  return (
    <span style={text(40, 600, C.ink3)}>
      {line.words.map((w, i) => (
        <span key={i} style={{ color: ms >= w.startMs - 40 ? C.ink : C.ink3, transition: 'none' }}>
          {w.text}
          {i < line.words.length - 1 ? ' ' : ''}
        </span>
      ))}
    </span>
  )
}

function Spoken({ line }: { line: TimedLine }) {
  const [who, color] = SPEAKER[line.speaker as 'agent' | 'resident']
  return (
    <span style={text(38, 600, C.ink)}>
      <span style={{ fontFamily: MONO, fontSize: 22, fontWeight: 700, color, marginRight: 14, verticalAlign: 4 }}>{who}</span>
      {line.subtitle ?? line.text}
    </span>
  )
}
