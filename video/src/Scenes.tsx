// The scenes that are not the map: the alert that only speaks, HackFire and its pipeline, the call,
// the command post and the close.

import { useAudioData, visualizeAudio } from '@remotion/media-utils'
import type { CSSProperties, ReactNode } from 'react'
import { AbsoluteFill, staticFile } from 'remotion'
import { DATA, FireMap, camAt } from './FireMap'
import { Icon } from './Icon'
import { SimulationTag } from './Chrome'
import { ALL_LINES, beat, line, lineEnd, scene, type TimedLine } from './timeline'
import { C, FPS, MONO, clamp01, ease, easeOut, fade, mono, pop, sp, text } from './theme'

/** An opaque scene over the map: fades in at its start, out after its end while the next arrives. */
export function Overlay({ id, f, children, style }: { id: string; f: number; children: ReactNode; style?: CSSProperties }) {
  const s = scene(id)
  if (f < s.start || f >= s.end + 8) return null
  const opacity = Math.min(fade(f - s.start, 8), 1 - fade(f - s.end, 8))
  return <AbsoluteFill style={{ background: C.night, opacity, ...style }}>{children}</AbsoluteFill>
}

const Grid = ({ f, color = 'rgba(111,140,255,0.06)' }: { f: number; color?: string }) => (
  <AbsoluteFill
    style={{
      backgroundImage: `linear-gradient(${color} 1px, transparent 1px), linear-gradient(90deg, ${color} 1px, transparent 1px)`,
      backgroundSize: '64px 64px',
      backgroundPosition: `${-(f * 0.25) % 64}px ${-(f * 0.12) % 64}px`,
    }}
  />
)

// ── 01 The alert that only speaks ─────────────────────────────────────────────

// The alert of that day (Ávilared, art. 93357), translated from the Spanish.
const ALERT_TEXT =
  'El Tiemblo, Burgohondo and Navaluenga are being confined because of the smoke. Please stay in your homes.'

export function Problem({ f }: { f: number }) {
  const s = scene('problem')
  const every = beat('problem-0', 'every')
  const questions: [number, string][] = [
    [beat('problem-1', 'left'), 'Who has left?'],
    [beat('problem-1', 'move'), "Who can't move?"],
    [beat('problem-1', 'never'), 'Who never got it?'],
  ]
  const t = f - s.start
  return (
    <Overlay id="problem" f={f}>
      <Grid f={f} />
      {/* The tower broadcasts; nothing comes back. */}
      <div style={{ position: 'absolute', left: 90, top: 380, ...pop(t - 2) }}>
        <Icon name="tower" size={220} color={C.ink2} stroke={1.4} />
        <div style={{ ...mono(22, 700, C.status.needs_rescue), textAlign: 'center', marginTop: 4 }}>ES-Alert</div>
      </div>
      {[0, 1, 2, 3].map((i) => {
        const k = ((t + i * 11) % 44) / 44
        return (
          <div key={i} style={{ position: 'absolute', left: 200 - 700 * k, top: 490 - 700 * k, width: 1400 * k, height: 1400 * k, borderRadius: '50%', border: `2px solid ${C.status.needs_rescue}`, opacity: 0.35 * (1 - k) }} />
        )
      })}
      <Phone style={{ left: 430, top: 190, ...pop(t - 6) }} lit={f >= every - 20} big />
      <div style={{ position: 'absolute', left: 900, top: 190, display: 'grid', gridTemplateColumns: 'repeat(6, 132px)', gap: 24 }}>
        {Array.from({ length: 18 }, (_, i) => (
          <Phone key={i} lit={f >= every + (i % 6) * 2 + Math.floor(i / 6)} dim={f >= questions[0][0]} />
        ))}
      </div>
      <div style={{ position: 'absolute', left: 900, top: 240, display: 'flex', flexDirection: 'column', gap: 26 }}>
        {questions.map(([at, q]) => (
          <div key={q} style={{ ...pop(f - at), display: 'inline-flex' }}>
            <span style={{ padding: '10px 26px', borderRadius: 14, background: 'rgba(4,8,23,0.9)', border: `1px solid ${C.line}`, ...text(56, 700) }}>
              {q} <span style={{ color: C.ink3 }}>?</span>
            </span>
          </div>
        ))}
      </div>
      <div style={{ position: 'absolute', left: 900, top: 150, ...pop(f - every - 6), ...mono(22, 500, C.ink2) }}>Same message, every phone in the area. No way to answer.</div>
    </Overlay>
  )
}

function Phone({ style, lit, big = false, dim = false }: { style?: CSSProperties; lit: boolean; big?: boolean; dim?: boolean }) {
  const w = big ? 400 : 132
  const h = big ? 700 : 200
  return (
    <div style={{ position: big ? 'absolute' : 'relative', width: w, height: h, borderRadius: big ? 48 : 20, border: `${big ? 4 : 2}px solid ${C.line}`, background: '#070c22', overflow: 'hidden', opacity: dim ? 0.25 : 1, ...style }}>
      {lit && (
        <div style={{ margin: big ? 22 : 8, marginTop: big ? 70 : 22, borderRadius: big ? 20 : 8, background: 'rgba(224,48,42,0.16)', border: `${big ? 2 : 1}px solid ${C.status.needs_rescue}`, padding: big ? 20 : 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon name="bell" size={big ? 28 : 12} color={C.status.needs_rescue} />
            <span style={big ? text(24, 800, C.status.needs_rescue) : { ...text(10, 800, C.status.needs_rescue) }}>ES-Alert</span>
          </div>
          {big ? (
            <div style={{ ...text(25, 500, C.ink), marginTop: 12, lineHeight: 1.35 }}>{ALERT_TEXT}</div>
          ) : (
            [0.9, 1, 0.7].map((wk, i) => <div key={i} style={{ height: 5, width: `${wk * 100}%`, borderRadius: 3, background: 'rgba(238,242,255,0.5)', marginTop: 6 }} />)
          )}
        </div>
      )}
    </div>
  )
}

// ── 02 HackFire, and how it works ─────────────────────────────────────────────

const PIPELINE: [string, string, string][] = [
  ['satellite', 'Satellites', 'Deepfire hotspots'],
  ['flame', 'Forecast', 'where it is heading'],
  ['flag', 'Order', 'the coordinator approves'],
  ['phone', 'Call', 'voice agent, SLNG'],
  ['lifebuoy', 'Triage', "who can't leave"],
  ['fire-truck', 'Crews', 'plan and live map'],
]
const NODE_W = 250
const NODE_X = (i: number) => 110 + i * 292
const NODE_Y = 600

export function Brand({ f }: { f: number }) {
  const s = scene('brand')
  const t = f - s.start
  const said = lineEnd('brand-0')
  const g = f - (said - 8) // the pipeline's clock
  const zoomAt = s.end - 18
  const z = ease((f - zoomAt) / 18)
  const title = 1 - ease((g - 4) / 14)
  const glitch = t >= 6 && t < 16
  // The camera dives into the Forecast node: the map behind it is the forecast.
  const focus = [NODE_X(1) + NODE_W / 2, NODE_Y + 75]
  return (
    <Overlay id="brand" f={f} style={{ opacity: undefined }}>
      <AbsoluteFill style={{ opacity: 1 - z }}>
        <Grid f={f} />
        <AbsoluteFill style={{ transformOrigin: `${focus[0]}px ${focus[1]}px`, transform: `scale(${1 + 7 * Math.pow(z, 2)})` }}>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 250 - 170 * (1 - title), display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${0.62 + 0.38 * title})` }}>
            <div style={{ position: 'relative', ...pop(t - 6) }}>
              {glitch && (
                <>
                  <div style={{ position: 'absolute', left: -10, top: 0, opacity: 0.7 }}>
                    <Icon name="logo" size={190} color={C.agent} stroke={1.6} />
                  </div>
                  <div style={{ position: 'absolute', left: 10, top: 0, opacity: 0.7 }}>
                    <Icon name="logo" size={190} color={C.status.needs_rescue} stroke={1.6} />
                  </div>
                </>
              )}
              <Icon name="logo" size={190} color={C.fire[1]} stroke={1.6} />
            </div>
            <div style={{ ...text(132, 800), letterSpacing: -3, marginTop: 6, ...pop(t - 12) }}>HackFire</div>
            <div style={{ ...mono(30, 500, C.agent), marginTop: 8, opacity: title }}>
              {typed('Calls every resident. Listens to every answer.', t - 24, 1.6)}
            </div>
          </div>
          {g > 0 && <Pipeline g={g} />}
        </AbsoluteFill>
      </AbsoluteFill>
    </Overlay>
  )
}

const typed = (s: string, t: number, perFrame: number) => s.slice(0, Math.max(0, Math.floor(t * perFrame)))

function Pipeline({ g }: { g: number }) {
  const appear = (i: number) => 8 + i * 4
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        {PIPELINE.slice(1).map((_, i) => {
          const k = ease((g - appear(i + 1)) / 8)
          const x1 = NODE_X(i) + NODE_W
          const x2 = NODE_X(i + 1)
          return <line key={i} x1={x1} y1={NODE_Y + 75} x2={x1 + (x2 - x1) * k} y2={NODE_Y + 75} stroke={C.ink3} strokeWidth={3} />
        })}
        {/* The call answers back to the coordinator: what makes it different from a broadcast. */}
        {(() => {
          const k = ease((g - 36) / 14)
          const x1 = NODE_X(3) + NODE_W / 2
          const x2 = NODE_X(2) + NODE_W / 2
          const d = `M ${x1} ${NODE_Y + 150} C ${x1} ${NODE_Y + 260}, ${x2} ${NODE_Y + 260}, ${x2} ${NODE_Y + 150}`
          return (
            <>
              <path d={d} fill="none" stroke={C.agent} strokeWidth={4} pathLength={1} strokeDasharray={`${k} 1`} />
              <text x={(x1 + x2) / 2} y={NODE_Y + 272} textAnchor="middle" style={{ fontFamily: MONO, fontSize: 24, fontWeight: 700 }} fill={C.agent} opacity={k}>
                listens back
              </text>
            </>
          )
        })()}
      </svg>
      {PIPELINE.map(([icon, title, sub], i) => (
        <div key={title} style={{ position: 'absolute', left: NODE_X(i), top: NODE_Y, width: NODE_W, height: 150, ...pop(g - appear(i)) }}>
          <div style={{ height: '100%', boxSizing: 'border-box', borderRadius: 18, border: `2px solid ${i === 3 ? C.agent : C.line}`, background: 'rgba(20,30,66,0.95)', padding: '18px 20px' }}>
            <Icon name={icon} size={38} color={i < 2 ? C.fire[1] : i === 3 ? C.agent : i === 4 ? C.status.needs_rescue : C.route} />
            <div style={{ ...text(30, 700), marginTop: 10 }}>{title}</div>
            <div style={text(19, 500, C.ink2)}>{sub}</div>
          </div>
        </div>
      ))}
    </AbsoluteFill>
  )
}

// ── 03 The call ───────────────────────────────────────────────────────────────

const CALL_LINES = () => ALL_LINES.filter((l) => l.scene === 'call')

export function Call({ f }: { f: number }) {
  const s = scene('call')
  const lines = CALL_LINES()
  const answered = lines[0].at - 4
  const current = [...lines].reverse().find((l) => f >= l.at && f < l.at + l.frames)
  const seconds = Math.max(0, Math.floor((f - answered) / FPS))
  // The agent records as soon as it knows they can't leave on their own (voice/resident/instructions.md).
  const rescueAt = lineEnd('call-2') + 6
  return (
    <Overlay id="call" f={f}>
      <Grid f={f} color="rgba(95,227,255,0.05)" />
      <SimulationTag opacity={1} top={36} />
      <div style={{ position: 'absolute', left: 80, top: 150, width: 960, height: 780 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(95,227,255,0.12)', border: `2px solid ${C.agent}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="phone" size={28} color={C.agent} />
          </div>
          <div>
            <div style={text(32, 700)}>Resident 03, La Atalaya</div>
            <div style={mono(19, 500, C.ink2)}>voice agent on SLNG. It speaks Spanish; shown in English</div>
          </div>
          <div style={{ marginLeft: 'auto', ...mono(40, 700, f < answered ? C.ink3 : C.agent) }}>
            {f < answered ? 'calling' : `00:${String(seconds).padStart(2, '0')}`}
          </div>
        </div>
        <div style={{ height: 120, marginTop: 26, borderRadius: 16, border: `1px solid ${C.line}`, background: 'rgba(11,19,48,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
          {current ? <Waveform line={current} f={f} /> : f < answered ? <Ringing f={f - s.start} /> : <Flat />}
        </div>
        <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 14, height: 520, justifyContent: 'flex-end', overflow: 'hidden' }}>
          {lines
            .filter((l) => f >= l.at)
            .slice(-4)
            .map((l) => (
              <Bubble key={l.id} line={l} f={f} />
            ))}
        </div>
      </div>

      <div style={{ position: 'absolute', left: 1100, top: 150, width: 740, display: 'flex', flexDirection: 'column', gap: 20 }}>
        <Panel title="Known before dialling" style={pop(f - s.start - 10)}>
          <Row icon="flame" color={C.fire[1]}>Fire expected in about 3 h</Row>
          <Row icon="flag" color={C.zone}>Order: leave for San Martín de Valdeiglesias</Row>
          <Row icon="car" color={C.route}>N-403, {DATA.routes.wayOut.minutes} min by car</Row>
        </Panel>
        <Panel title="Triage record" style={pop(f - s.start - 18)}>
          <Field label="Status" at={rescueAt} f={f} before="Not called yet" after="Needs rescue" color={C.status.needs_rescue} icon="lifebuoy" />
          <Field label="People" at={rescueAt} f={f} before="Unknown" after="2" />
          <Field label="Mobility" at={rescueAt} f={f} before="Unknown" after="mother can't walk" />
        </Panel>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, ...mono(20, 500, C.agent) }}>
          {f >= rescueAt && <div style={pop(f - rescueAt)}>&gt; report_status: needs_rescue, 2 people, "mother can't walk"</div>}
        </div>
      </div>
    </Overlay>
  )
}

function Waveform({ line: l, f }: { line: TimedLine; f: number }) {
  const audio = useAudioData(staticFile(l.file))
  if (!audio) return <Flat />
  const bars = visualizeAudio({ fps: FPS, frame: Math.max(0, f - l.at), audioData: audio, numberOfSamples: 64 }).slice(0, 48)
  const color = l.speaker === 'agent' ? C.agent : C.ink
  return (
    <>
      {bars.map((v, i) => {
        const mirrored = bars[Math.abs(24 - i) * 2 - (i < 24 ? 0 : 1)] ?? v
        return <div key={i} style={{ width: 9, height: 8 + Math.min(96, Math.sqrt(mirrored) * 190), borderRadius: 5, background: color, opacity: 0.9 }} />
      })}
    </>
  )
}

const Flat = () => (
  <>
    {Array.from({ length: 48 }, (_, i) => (
      <div key={i} style={{ width: 9, height: 6, borderRadius: 3, background: C.ink3, opacity: 0.6 }} />
    ))}
  </>
)

function Ringing({ f }: { f: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 18, opacity: 0.55 + 0.45 * Math.abs(Math.sin(f / 9)) }}>
      <Icon name="phone" size={40} color={C.agent} />
      <span style={mono(30, 700, C.agent)}>ringing</span>
    </div>
  )
}

function Bubble({ line: l, f }: { line: TimedLine; f: number }) {
  const ms = ((f - l.at) / FPS) * 1000
  const agent = l.speaker === 'agent'
  return (
    <div style={{ alignSelf: agent ? 'flex-start' : 'flex-end', maxWidth: 780, ...pop(f - l.at) }}>
      <div style={{ ...mono(17, 700, agent ? C.agent : C.ink2), marginBottom: 6, textAlign: agent ? 'left' : 'right' }}>{agent ? 'Agent' : 'Resident'}</div>
      <div style={{ padding: '14px 20px', borderRadius: 16, background: agent ? 'rgba(95,227,255,0.08)' : 'rgba(238,242,255,0.08)', border: `1px solid ${agent ? 'rgba(95,227,255,0.5)' : C.line}`, ...text(29, 500) }}>
        {l.words.map((w, i) => (
          <span key={i} style={{ opacity: ms >= w.startMs - 30 ? 1 : 0 }}>
            {w.text}{' '}
          </span>
        ))}
      </div>
    </div>
  )
}

function Panel({ title, children, style }: { title: string; children: ReactNode; style?: CSSProperties }) {
  return (
    <div style={{ borderRadius: 18, border: `1px solid ${C.line}`, background: 'rgba(20,30,66,0.9)', padding: '18px 24px', ...style }}>
      <div style={{ ...mono(18, 500, C.ink2), marginBottom: 10 }}>{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>{children}</div>
    </div>
  )
}

function Row({ icon, color, children }: { icon: string; color: string; children: ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <Icon name={icon} size={26} color={color} />
      <span style={text(24, 500)}>{children}</span>
    </div>
  )
}

function Field({ label, at, f, before, after, color = C.ink, icon }: { label: string; at: number; f: number; before: string; after: string; color?: string; icon?: string }) {
  const done = f >= at
  const flash = done && f < at + 12 ? 1 - (f - at) / 12 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '4px 10px', margin: '0 -10px', borderRadius: 10, background: `rgba(95,227,255,${0.25 * flash})` }}>
      <span style={{ width: 120, ...text(21, 500, C.ink2) }}>{label}</span>
      {done && icon && <Icon name={icon} size={26} color={color} />}
      <span style={text(26, done ? 700 : 500, done ? color : C.ink3)}>{done ? after : before}</span>
    </div>
  )
}

// ── 04 The command post ───────────────────────────────────────────────────────

export function Command({ f }: { f: number }) {
  const s = scene('command')
  const voice = beat('command-0', 'voice')
  const vonage = beat('command-0', 'vonage')
  const t = f - s.start
  return (
    <Overlay id="command" f={f}>
      <Grid f={f} />
      <SimulationTag opacity={1} top={36} />
      <div style={{ position: 'absolute', left: 80, top: 170, width: 700, display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div style={pop(t - 2)}>
          <Panel title="Coordinator, by voice">
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 60, height: 60, borderRadius: '50%', border: `2px solid ${C.ink}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="mic" size={30} color={C.ink} />
              </div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', height: 50 }}>
                {Array.from({ length: 22 }, (_, i) => (
                  <div key={i} style={{ width: 6, borderRadius: 3, background: C.ink, height: f < voice + 30 ? 6 + 36 * Math.abs(Math.sin(i * 1.7 + f / 3)) * Math.abs(Math.sin(f / 7 + i)) : 6 }} />
                ))}
              </div>
            </div>
            <div style={{ ...text(30, 600), marginTop: 8 }}>“Which rescues do I have, and in what order?”</div>
          </Panel>
        </div>
        <div style={pop(f - voice - 18)}>
          <Panel title="Agent" style={{ borderColor: 'rgba(95,227,255,0.5)' }}>
            <div style={text(28, 600, C.ink)}>“One: La Atalaya, two people. Crew 1 is on its way, there in ten minutes.”</div>
          </Panel>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 860, top: 150, width: 980, ...pop(f - vonage) }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <span style={{ width: 14, height: 14, borderRadius: '50%', background: C.status.needs_rescue, opacity: 0.5 + 0.5 * Math.abs(Math.sin(f / 8)) }} />
          <span style={text(28, 700)}>Live map, shared from the command post</span>
          <span style={{ ...mono(18, 500, C.ink2), marginLeft: 'auto' }}>Vonage Video</span>
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Crew 1', 'Crew 2'].map((crew, i) => (
            <div key={crew} style={{ ...pop(f - vonage - 6 - i * 6) }}>
              <div style={{ width: 470, height: 560, borderRadius: 30, border: `3px solid ${C.line}`, background: '#050a1c', overflow: 'hidden', position: 'relative' }}>
                <FireMap
                  cam={camAt(-4.47, 40.397, 58)}
                  width={470}
                  height={560}
                  time={2315}
                  f={f}
                  risk={1}
                  labels={0}
                  crewBase={1}
                  wayIn={1}
                  residents={{ n01: 'evacuating', n02: 'no_answer', n03: 'needs_rescue', n04: 'pending', n05: 'pending' }}
                />
                <div style={{ position: 'absolute', left: 16, top: 14, padding: '6px 14px', borderRadius: 999, background: 'rgba(4,8,23,0.85)', ...text(20, 700) }}>{crew}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Overlay>
  )
}

// ── 05 Listening back ─────────────────────────────────────────────────────────

export function Close({ f }: { f: number }) {
  const s = scene('close')
  const listens = beat('close-0', 'listens')
  const card = line('close-1').at - 6
  const t = f - s.start
  const phones = [0, 1, 2, 3, 4]
  const cardK = ease((f - card) / 18)
  return (
    <Overlay id="close" f={f}>
      <Grid f={f} />
      <AbsoluteFill style={{ opacity: 1 - cardK }}>
        <div style={{ position: 'absolute', left: 170, top: 380, textAlign: 'center', ...pop(t - 2) }}>
          <Icon name="tower" size={170} color={C.ink3} stroke={1.4} />
          <div style={mono(22, 700, C.ink3)}>ES-Alert</div>
        </div>
        <div style={{ position: 'absolute', right: 170, top: 380, textAlign: 'center', ...pop(f - listens) }}>
          <Icon name="logo" size={170} color={C.fire[1]} stroke={1.4} />
          <div style={mono(22, 700, C.agent)}>HackFire</div>
        </div>
        <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
          {phones.map((i) => {
            const y = 250 + i * 150
            const out = ease((t - 4 - i * 2) / 14)
            const back = ease((f - listens - i * 3) / 16)
            return (
              <g key={i}>
                <line x1={380} y1={470} x2={380 + (840 - 380) * out} y2={470 + (y + 60 - 470) * out} stroke={C.ink3} strokeWidth={2} strokeDasharray="6 8" />
                <rect x={860} y={y} width={70} height={120} rx={12} fill="#070c22" stroke={back > 0 ? C.agent : C.line} strokeWidth={2} />
                {back > 0 && <line x1={950} y1={y + 60} x2={950 + (1540 - 950) * back} y2={y + 60 + (470 - y - 60) * back} stroke={C.agent} strokeWidth={4} />}
              </g>
            )
          })}
        </svg>
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: cardK, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingBottom: 120 }}>
        <div style={pop(f - card)}>
          <Icon name="logo" size={150} color={C.fire[1]} stroke={1.6} />
        </div>
        <div style={{ ...text(120, 800), letterSpacing: -3, ...pop(f - card - 4) }}>HackFire</div>
        <div style={{ ...mono(30, 500, C.agent), marginTop: 6, ...pop(f - card - 10) }}>Calls every resident. Listens to every answer.</div>
        <div style={{ ...text(26, 500, C.ink2), marginTop: 44, ...pop(f - card - 40) }}>Built at HackBarna 2026 with Deepfire, SLNG and Vonage</div>
        <div style={{ ...mono(19, 500, C.ink3), marginTop: 12, ...pop(f - card - 50) }}>
          About 6 hours of lead time on the replay of the 23 July 2026 fire, from satellite data alone.
        </div>
      </AbsoluteFill>
    </Overlay>
  )
}


// ── 05 What changes ───────────────────────────────────────────────────────────

// The day's figures, each with its source (docs/findings/2026-09-19-press-figures.md).
const THE_DAY: [string, string, string][] = [
  ['37,818 ha', 'burned in Ávila, provisional', 'Junta de Castilla y León'],
  ['1,500', 'people evacuated', 'Tribuna de Ávila'],
  ['5', 'homes destroyed', 'Tribuna de Ávila'],
  ['229', 'homes inside the burned area', "Idealista's estimate"],
]

// What the coordinator knows, and when. Left: the day, sourced. Right: what HackFire does, measured.
const SIDE_BY_SIDE: [string, string, string][] = [
  ['The warning', 'One alert to every phone', 'An order per zone, said to each household'],
  ['Answers', "None: an alert can't hear back", 'Leaving, needs rescue or no answer, per call'],
  ["Who can't leave", 'Not known from the alert', 'On the map within 2 s, queued by the fire'],
  ['The way out', 'The same message for every road', 'A route per home, around the fire and cut roads'],
  ['Time to act', '', 'About 6 h on La Atalaya, from satellites alone'],
]

export function Compare({ f }: { f: number }) {
  const s = scene('compare')
  const cards = [beat('compare-0', 'thirty'), beat('compare-0', 'thirty') + 8, beat('compare-0', 'thirty') + 16, beat('compare-0', 'two')]
  const table = line('compare-1').at + 6
  const k = ease((f - table + 4) / 16)
  const quick = beat('compare-1', 'two')
  return (
    <Overlay id="compare" f={f}>
      <Grid f={f} />
      <div style={{ position: 'absolute', left: 90, right: 90, top: 150 - 20 * k, opacity: 1 - 0.55 * k, transform: `scale(${1 - 0.28 * k})`, transformOrigin: 'top left' }}>
        <div style={{ ...mono(22, 700, C.ink2), marginBottom: 16, ...pop(f - s.start - 4) }}>23 July 2026, what it cost</div>
        <div style={{ display: 'flex', gap: 22 }}>
          {THE_DAY.map(([figure, label], i) => (
            <div key={label} style={{ flex: 1, ...pop(f - cards[i]) }}>
              <div style={{ borderRadius: 18, border: `1px solid ${C.line}`, background: 'rgba(20,30,66,0.9)', padding: '18px 24px' }}>
                <div style={{ ...text(58, 800, i === 3 ? C.fire[0] : C.fire[1]), fontVariantNumeric: 'tabular-nums' }}>{figure}</div>
                <div style={text(22, 500, C.ink2)}>{label}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      {f >= table && (
        <div style={{ position: 'absolute', left: 90, right: 90, top: 330 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr 1fr', columnGap: 22, rowGap: 12, alignItems: 'stretch' }}>
            <div />
            <div style={{ ...mono(22, 700, C.ink3), ...pop(f - table) }}>23 July 2026</div>
            <div style={{ ...mono(22, 700, C.agent), display: 'flex', alignItems: 'center', gap: 8, ...pop(f - table) }}>
              <Icon name="logo" size={24} color={C.fire[1]} />
              With HackFire
            </div>
            {SIDE_BY_SIDE.map(([what, day, ours], i) => {
              const t = f - table - 10 - i * 7
              const lit = i === 2 && f >= quick
              return [
                <div key={`w${i}`} style={{ ...text(24, 700, C.ink2), padding: '14px 0', ...pop(t) }}>{what}</div>,
                <div key={`d${i}`} style={{ ...text(25, 500, C.ink3), padding: '14px 20px', borderRadius: 14, border: `1px solid ${C.line}`, ...pop(t) }}>{day || '—'}</div>,
                <div key={`o${i}`} style={{ ...text(25, 600, C.ink), padding: '14px 20px', borderRadius: 14, border: `1px solid ${lit ? C.agent : 'rgba(95,227,255,0.35)'}`, background: lit ? 'rgba(95,227,255,0.14)' : 'rgba(95,227,255,0.05)', ...pop(t) }}>{ours}</div>,
              ]
            })}
          </div>
        </div>
      )}
    </Overlay>
  )
}

const ROADMAP: [string, string, string, [string, string][]][] = [
  ['Now', 'Built this weekend', C.status.evacuating, [
    ['satellite', 'Forecast from satellite hotspots'],
    ['phone', 'Calls in Spanish, triage, rescue queue'],
    ['fire-truck', 'Crew plan, road closures, live map'],
  ]],
  ['Next', 'Pilot', C.route, [
    ['phone', 'Real phone lines (SIP)'],
    ['mic', 'Handover to a person at the control post'],
    ['home', 'One municipality, voluntary registry'],
  ]],
  ['Then', 'Scale', C.agent, [
    ['route', 'More regions, more languages'],
    ['fire-truck', "Inside 112 and the crews' dispatch"],
    ['flame', 'Devin retrains the forecast on every fire'],
  ]],
]

export function Roadmap({ f }: { f: number }) {
  const s = scene('roadmap')
  const at = [s.start + 4, line('roadmap-0').at, beat('roadmap-1', 'then')]
  return (
    <Overlay id="roadmap" f={f}>
      <Grid f={f} />
      <div style={{ position: 'absolute', left: 90, top: 150, ...mono(22, 700, C.ink2), ...pop(f - s.start) }}>Roadmap</div>
      <div style={{ position: 'absolute', left: 90, right: 90, top: 214, height: 4, borderRadius: 2, background: C.line }}>
        <div style={{ width: `${ease((f - s.start) / (s.end - s.start - 20)) * 100}%`, height: '100%', borderRadius: 2, background: `linear-gradient(90deg, ${C.status.evacuating}, ${C.route}, ${C.agent})` }} />
      </div>
      <div style={{ position: 'absolute', left: 90, right: 90, top: 250, display: 'flex', gap: 26 }}>
        {ROADMAP.map(([when, tag, color, items], i) => (
          <div key={when} style={{ flex: 1, ...pop(f - at[i]) }}>
            <div style={{ borderRadius: 20, border: `2px solid ${color}`, background: 'rgba(20,30,66,0.92)', padding: '22px 26px', height: 470, boxSizing: 'border-box' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 14 }}>
                <span style={text(46, 800, color)}>{when}</span>
                <span style={mono(20, 500, C.ink2)}>{tag}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 22, marginTop: 26 }}>
                {items.map(([icon, label], j) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 14, ...pop(f - at[i] - 6 - j * 5) }}>
                    <Icon name={icon} size={30} color={color} />
                    <span style={text(27, 600)}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Overlay>
  )
}
