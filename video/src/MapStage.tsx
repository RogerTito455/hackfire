// One map for the whole story, so the camera flies instead of cutting: the valley on 23 July, the
// rewind to 15:30, the forecast, the lead time, the order, the call's result and the rescue plan.
// Times are the replay's (data/map.json); the order and call moments are the demo autopilot's
// (data/demo_timeline.json): order approved at 15:45, Resident 03 calls in at 16:35.

import type { ReactNode } from 'react'
import { AbsoluteFill } from 'remotion'
import { DATA, FireMap, VIEWS, camAt, lerpCam, toKm, type Camera, type MapProps } from './FireMap'
import { Icon } from './Icon'
import { Clock, SimulationTag, Source } from './Chrome'
import { beat, scene } from './timeline'
import { C, clamp01, clock, ease, easeOut, fade, mono, pop, sp, text, type Status } from './theme'

const L = DATA.leadTime
const ORDER_AT = 2265 // 23 July 13:45 UTC, 15:45 in Spain
const CALL_AT = 2315 // 14:35 UTC, 16:35 in Spain
const ATALAYA: [number, number] = [-4.4603, 40.3831]
const SIDE = 300 // the map's shift right when a panel sits on the left

type Stage = MapProps & { clockLabel: string; simulation: number }

const easeIn = (v: number) => Math.pow(clamp01(v), 2.2)

function stage(f: number): Stage {
  const open = scene('open')
  const forecast = scene('forecast')
  const lead = scene('leadtime')
  const order = scene('order')
  const understood = scene('understood')
  const rescue = scene('rescue')
  const valleyNear: Camera = { ...VIEWS.valley, z: 54 }

  if (f < forecast.start) {
    // The fire runs to the first hotspot within 3 km of La Atalaya as the narrator says "reached",
    // then creeps on for the rest of the evening.
    const reach = beat('open-0', 'reached') + 6
    return {
      cam: lerpCam(VIEWS.valley, valleyNear, ease(f / open.end)),
      time: f < reach ? 660 + (L.reached - 660) * ease(f / reach) : L.reached + 60 * easeOut((f - reach) / (open.end - reach)),
      f,
      clockLabel: 'Replay',
      simulation: 0,
    }
  }
  if (f < lead.start) {
    const t = f - forecast.start
    const grow = beat('forecast-0', 'forecasts')
    return {
      cam: lerpCam(valleyNear, VIEWS.east, ease((f - grow + 10) / 70)),
      time: L.reached - (L.reached - L.flagged) * ease(t / 18),
      forecast: 7 * easeOut((f - grow) / 50),
      risk: fade(f - beat('forecast-1', 'atalaya'), 10),
      f,
      clockLabel: 'Replay',
      simulation: 0,
    }
  }
  if (f < order.start) {
    const t = f - lead.start
    const hit = beat('leadtime-0', 'nine')
    return {
      cam: lerpCam(VIEWS.east, camAt(-4.49, 40.388, 96), ease(t / 50)),
      time: L.flagged + (L.reached - L.flagged) * easeIn(t / (hit - lead.start)),
      forecast: 7 * (1 - ease(t / 24)),
      ring: fade(t - 6, 16),
      risk: 1,
      f,
      clockLabel: 'Replay',
      simulation: 0,
    }
  }
  const overview = camAt(-4.478, 40.399, 150)
  const close = camAt(-4.4585, 40.3829, 250)
  const wide = camAt(-4.452, 40.389, 118)
  const called = f >= understood.start
  const residents: Record<string, Status> = called
    ? { n01: 'evacuating', n02: 'no_answer', n03: 'needs_rescue', n04: 'pending', n05: 'pending' }
    : { n01: 'pending', n02: 'pending', n03: 'pending', n04: 'pending', n05: 'pending' }
  if (f < understood.start) {
    return { cam: overview, offsetX: SIDE, time: ORDER_AT, risk: 1, residents, f, clockLabel: 'Replay', simulation: 1 }
  }
  if (f < rescue.start) {
    const t = f - understood.start
    return {
      cam: lerpCam(overview, close, ease(t / 30)),
      offsetX: SIDE * (1 - ease(t / 30)),
      time: CALL_AT,
      risk: 1,
      residents,
      flash: { id: 'n03', at: understood.start + 14 },
      f,
      clockLabel: 'Replay',
      simulation: 1,
    }
  }
  const t = f - rescue.start
  return {
    cam: lerpCam(close, wide, ease(t / 36)),
    offsetX: SIDE * ease(t / 36),
    time: CALL_AT,
    risk: 1,
    residents,
    crewBase: fade(f - beat('rescue-0', 'crews'), 10),
    wayIn: easeOut((f - beat('rescue-0', 'crews') - 6) / 30),
    wayOut: easeOut((f - beat('rescue-0', 'queued')) / 34),
    labels: 1,
    f,
    clockLabel: 'Replay',
    simulation: 1,
  }
}

/** Where a place lands on screen, with the stage's camera. */
function onScreen(s: Stage, lon: number, lat: number): [number, number] {
  const [x, y] = toKm(lon, lat)
  return [(x - s.cam.x) * s.cam.z + 960 + (s.offsetX ?? 0), (y - s.cam.y) * s.cam.z + 540]
}

export function MapStage({ f }: { f: number }) {
  const s = stage(f)
  const { day, time } = clock(s.time)
  return (
    <AbsoluteFill>
      <FireMap {...s} />
      <Clock day={day} time={time} label={s.clockLabel} opacity={1} />
      <SimulationTag opacity={s.simulation} />
      <OpenOverlay f={f} s={s} />
      <ForecastOverlay f={f} s={s} />
      <LeadTimeOverlay f={f} s={s} />
      <OrderOverlay f={f} s={s} />
      <UnderstoodOverlay f={f} s={s} />
      <RescueOverlay f={f} />
    </AbsoluteFill>
  )
}

/** Fades a scene's own overlay in at its start and out at its end. */
function During({ id, f, children, out = 10 }: { id: string; f: number; children: ReactNode; out?: number }) {
  const s = scene(id)
  if (f < s.start || f >= s.end) return null
  return <AbsoluteFill style={{ opacity: Math.min(fade(f - s.start, 8), fade(s.end - f, out)) }}>{children}</AbsoluteFill>
}

function Card({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: 'rgba(20,30,66,0.92)', border: `1px solid ${C.line}`, borderRadius: 18, padding: '20px 24px', boxShadow: '0 20px 60px rgba(0,0,0,0.45)', ...style }}>{children}</div>
  )
}

function Pulse({ at, f, color, size = 60 }: { at: [number, number]; f: number; color: string; size?: number }) {
  return (
    <>
      {[0, 1, 2].map((i) => {
        const k = ((f + i * 12) % 36) / 36
        return (
          <div key={i} style={{ position: 'absolute', left: at[0] - (size * (0.4 + k)) / 2, top: at[1] - (size * (0.4 + k)) / 2, width: size * (0.4 + k), height: size * (0.4 + k), borderRadius: '50%', border: `3px solid ${color}`, opacity: 1 - k }} />
        )
      })}
    </>
  )
}

function OpenOverlay({ f, s }: { f: number; s: Stage }) {
  const reach = beat('open-0', 'reached')
  const people = beat('open-1', 'thirteen')
  const homes = beat('open-1', 'five')
  const at = onScreen(s, ...ATALAYA)
  return (
    <During id="open" f={f}>
      <div style={{ position: 'absolute', left: 48, top: 140, ...pop(f - 12) }}>
        <div style={text(72, 800)}>Burgohondo fire</div>
        <div style={{ ...mono(22, 500, C.ink2), marginTop: 8 }}>Ávila, Spain. Satellite hotspots, 22 and 23 July 2026</div>
      </div>
      {f >= reach && f < reach + 60 && <Pulse at={at} f={f - reach} color={C.fire[0]} size={90} />}
      <div style={{ position: 'absolute', left: 48, bottom: 200, display: 'flex', gap: 20 }}>
        {[
          [people, '1,300', 'people evacuated from La Atalaya'],
          [homes, '5', 'homes burned'],
        ].map(([t, figure, label]) => (
          <div key={label as string} style={pop(f - (t as number))}>
            <Card style={{ padding: '16px 26px' }}>
              <div style={{ ...text(64, 800, C.fire[1]), fontVariantNumeric: 'tabular-nums' }}>{figure as string}</div>
              <div style={text(22, 500, C.ink2)}>{label as string}</div>
            </Card>
          </div>
        ))}
      </div>
      <Source opacity={fade(f - people, 10)}>Sources: Tribuna de Ávila, Ávilared, 23 July 2026</Source>
    </During>
  )
}

function ForecastOverlay({ f, s }: { f: number; s: Stage }) {
  const fs = scene('forecast')
  const sat = beat('forecast-0', 'satellite')
  const grow = beat('forecast-0', 'forecasts')
  const flag = beat('forecast-1', 'atalaya')
  const at = onScreen(s, ...ATALAYA)
  const scan = (f - sat) / 40
  return (
    <During id="forecast" f={f} out={4}>
      {/* The rewind: a colour split for a moment, the clock running back to 15:30. */}
      {f - fs.start < 20 && <AbsoluteFill style={{ background: 'rgba(95,227,255,0.06)', mixBlendMode: 'screen', opacity: 1 - (f - fs.start) / 20 }} />}
      {f - fs.start < 22 && (
        <div style={{ position: 'absolute', left: 48, top: 140, ...mono(40, 700, C.agent), opacity: 1 - fade(f - fs.start - 14, 8) }}>&lt;&lt; back to 15:30</div>
      )}
      {scan > 0 && scan < 1 && (
        <div style={{ position: 'absolute', top: 0, bottom: 0, left: -200 + scan * 2320, width: 200, background: 'linear-gradient(90deg, transparent, rgba(95,227,255,0.18))', borderRight: `2px solid ${C.agent}` }} />
      )}
      <div style={{ position: 'absolute', left: 48, top: 140, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={pop(f - sat)}>
          <Chip icon="satellite" color={C.fire[0]}>
            Deepfire satellite hotspots, up to 15:30
          </Chip>
        </div>
        <div style={pop(f - grow)}>
          <Chip icon="flame" color={C.spread[2]}>
            Forecast: where the front goes, hour by hour
          </Chip>
        </div>
        <div style={{ display: 'flex', gap: 6, marginLeft: 8, ...pop(f - grow - 12) }}>
          {[1, 2, 3, 4, 5, 6].map((h) => (
            <div key={h} style={{ ...mono(17, 500, C.ink2), display: 'flex', alignItems: 'center', gap: 6, opacity: fade(f - grow - h * 6, 6) }}>
              <span style={{ width: 16, height: 16, borderRadius: 4, border: `2px dashed ${C.spread[h]}`, background: `${C.spread[h]}33` }} />+{h} h
            </div>
          ))}
        </div>
      </div>
      {f >= flag && (
        <div style={{ position: 'absolute', left: at[0] + 40, top: at[1] - 150, ...pop(f - flag) }}>
          <Chip icon="flag" color={C.zone}>
            La Atalaya in the path at 15:30
          </Chip>
        </div>
      )}
    </During>
  )
}

function Chip({ icon, color, children }: { icon: string; color: string; children: ReactNode }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, padding: '10px 18px 10px 12px', borderRadius: 999, background: 'rgba(4,8,23,0.86)', border: `1px solid ${color}` }}>
      <Icon name={icon} size={26} color={color} />
      <span style={text(24, 600)}>{children}</span>
    </div>
  )
}

function LeadTimeOverlay({ f, s }: { f: number; s: Stage }) {
  const hit = beat('leadtime-0', 'nine')
  const sign = beat('leadtime-1', 'six')
  const at = onScreen(s, ...ATALAYA)
  const k = sp(f - sign, 16, 160)
  return (
    <During id="leadtime" f={f}>
      <div style={{ position: 'absolute', left: 48, top: 140, ...pop(f - scene('leadtime').start - 6) }}>
        <Chip icon="flag" color={C.fire[0]}>
          3 km around La Atalaya
        </Chip>
      </div>
      {f >= hit && f < hit + 5 && <AbsoluteFill style={{ background: '#fff', opacity: 0.35 * (1 - (f - hit) / 5) }} />}
      {f >= hit && <Pulse at={at} f={f - hit} color={C.fire[1]} size={140} />}
      {f >= hit && f < sign + 8 && (
        <div style={{ position: 'absolute', left: at[0] + 70, top: at[1] + 60, ...pop(f - hit), opacity: 1 - fade(f - sign, 8) }}>
          <Chip icon="flame" color={C.fire[1]}>
            First hotspot within 3 km, 21:38
          </Chip>
        </div>
      )}
      {f >= sign && (
        <>
          <AbsoluteFill style={{ background: 'rgba(4,8,23,0.62)', opacity: fade(f - sign, 10) }} />
          <div style={{ position: 'absolute', left: 0, right: 0, top: 250, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: clamp01(k * 1.5), transform: `scale(${0.85 + 0.15 * Math.min(1.02, k)})` }}>
            <div style={{ ...text(210, 800, C.ink), letterSpacing: -6, fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
              <span style={{ fontSize: 80, color: C.ink2, letterSpacing: 0 }}>about </span>6<span style={{ fontSize: 96, color: C.ink2, letterSpacing: 0 }}> hours</span>
            </div>
            <div style={{ ...text(34, 600, C.ink2), marginTop: 10 }}>lead time for La Atalaya</div>
            <div style={{ ...text(26, 500, C.ink3), marginTop: 6 }}>between 5 and 8 hours, depending on the distance used (2–5 km)</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 34, width: 900 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, ...mono(26, 700, C.ink) }}>
                <Icon name="flag" size={26} color={C.route} />
                15:30
              </span>
              <div style={{ flex: 1, height: 10, borderRadius: 5, background: C.line, overflow: 'hidden' }}>
                <div style={{ width: `${ease((f - sign - 6) / 30) * 100}%`, height: '100%', background: `linear-gradient(90deg, ${C.route}, ${C.route} 85%, ${C.fire[1]})` }} />
              </div>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, ...mono(26, 700, C.ink) }}>
                21:38
                <Icon name="flame" size={26} color={C.fire[1]} />
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', width: 900, marginTop: 8, ...text(20, 500, C.ink3) }}>
              <span>First forecast that puts it in the path</span>
              <span>First hotspot within 3 km</span>
            </div>
          </div>
          <Source opacity={fade(f - sign - 20, 10)}>
            Satellite data only, on the replay of this fire. A range, because one satellite pixel decides the arrival. It says nothing about when anyone was warned.
          </Source>
        </>
      )}
    </During>
  )
}

function OrderOverlay({ f, s }: { f: number; s: Stage }) {
  const approve = beat('order-0', 'approves')
  const calls = beat('order-0', 'calls')
  const pressed = f >= approve && f < approve + 5
  const approved = f >= approve + 4
  return (
    <During id="order" f={f}>
      <div style={{ position: 'absolute', left: 48, top: 170, width: 560, ...pop(f - scene('order').start - 4) }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Icon name="flag" size={28} color={C.zone} />
            <span style={text(32, 700)}>La Atalaya</span>
            <span style={{ ...mono(18, 500, C.ink2), marginLeft: 'auto' }}>Evacuation order</span>
          </div>
          <div style={{ ...text(24, 500, C.ink2), marginTop: 16 }}>Fire expected in about 5 h</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
            <Icon name="exit" size={26} color={C.route} />
            <span style={text(26, 600)}>Leave for San Martín de Valdeiglesias</span>
          </div>
          <div
            style={{
              marginTop: 22,
              height: 64,
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              background: approved ? 'rgba(25,194,138,0.14)' : C.routeDeep,
              border: approved ? `2px solid ${C.status.evacuating}` : 'none',
              transform: `scale(${pressed ? 0.97 : 1})`,
              ...text(26, 700, approved ? C.status.evacuating : '#fff'),
            }}
          >
            {approved && <Icon name="check" size={28} color={C.status.evacuating} stroke={3} />}
            {approved ? 'Approved by the coordinator' : 'Approve'}
          </div>
        </Card>
        <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {['01', '02', '03', '04', '05'].map((n, i) => (
            <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 12, ...pop(f - calls - i * 3) }}>
              <Icon name="phone" size={24} color={C.agent} />
              <span style={text(22, 600)}>Resident {n}</span>
              <span style={{ ...mono(18, 500, C.agent), marginLeft: 'auto', opacity: 0.5 + 0.5 * Math.abs(Math.sin((f - i * 7) / 6)) }}>calling</span>
            </div>
          ))}
        </div>
      </div>
      {f >= calls &&
        DATA.residents.map((n, i) => <Pulse key={n.id} at={onScreen(s, n.lon, n.lat)} f={f - calls + i * 5} color={C.agent} size={80} />)}
    </During>
  )
}

function UnderstoodOverlay({ f, s }: { f: number; s: Stage }) {
  const u = scene('understood')
  const n03 = DATA.residents.find((n) => n.id === 'n03')!
  const at = onScreen(s, n03.lon, n03.lat)
  const keyword = beat('understood-0', 'keyword')
  return (
    <During id="understood" f={f}>
      <div style={{ position: 'absolute', left: Math.min(at[0] + 60, 1100), top: at[1] - 230, ...pop(f - u.start - 18) }}>
        <Card style={{ width: 620 }}>
          <div style={text(34, 600)}>“Mi madre no puede andar.”</div>
          <div style={{ ...text(22, 500, C.ink2), marginTop: 4 }}>My mother can't walk.</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 18 }}>
            <span style={mono(20, 500, C.agent)}>understood as</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 16px 6px 10px', borderRadius: 999, background: C.status.needs_rescue, ...text(24, 700, '#fff') }}>
              <Icon name="lifebuoy" size={24} color="#fff" />
              Needs rescue
            </span>
          </div>
          <div style={{ ...mono(18, 500, C.ink3), marginTop: 14, opacity: fade(f - keyword, 8) }}>no keyword in it: the meaning is enough</div>
        </Card>
      </div>
    </During>
  )
}

function RescueOverlay({ f }: { f: number }) {
  const queued = beat('rescue-0', 'queued')
  const crews = beat('rescue-0', 'crews')
  return (
    <During id="rescue" f={f}>
      <div style={{ position: 'absolute', left: 48, top: 170, width: 590, display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div style={pop(f - queued)}>
          <Card>
            <div style={{ ...mono(18, 500, C.ink2), marginBottom: 12 }}>Rescue queue, soonest fire first</div>
            <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
              <span style={{ ...mono(28, 700, C.status.needs_rescue) }}>1</span>
              <Icon name="lifebuoy" size={30} color={C.status.needs_rescue} />
              <div>
                <div style={text(26, 700)}>Resident 03, La Atalaya</div>
                <div style={text(21, 500, C.ink2)}>2 people, madre no puede andar</div>
                <div style={{ ...text(21, 600, C.fire[1]), marginTop: 4 }}>Fire expected in about 3 h</div>
              </div>
            </div>
          </Card>
        </div>
        <div style={pop(f - crews)}>
          <Card>
            <div style={{ ...mono(18, 500, C.ink2), marginBottom: 12 }}>Crew plan, 2 crews</div>
            <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
              <Icon name="fire-truck" size={30} color={C.route} />
              <div style={{ flex: 1 }}>
                <div style={text(24, 700)}>Crew 1 to Resident 03</div>
                <div style={text(21, 500, C.ink2)}>Leaves now, there in {DATA.routes.wayIn.minutes} min</div>
              </div>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 999, border: `2px solid ${C.status.evacuating}`, ...text(20, 700, C.status.evacuating) }}>
                <Icon name="check" size={20} color={C.status.evacuating} stroke={3} />
                In time
              </span>
            </div>
            <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginTop: 14, opacity: 0.6 }}>
              <Icon name="fire-truck" size={30} color={C.ink3} />
              <div style={text(22, 600, C.ink2)}>Crew 2 free</div>
            </div>
          </Card>
        </div>
        <div style={pop(f - queued - 16)}>
          <Card style={{ padding: '14px 20px' }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <Icon name="exit" size={26} color={C.route} />
              <div style={text(21, 500, C.ink2)}>
                Residents who can leave: <span style={{ color: C.ink }}>{DATA.routes.wayOut.to}</span>, {DATA.routes.wayOut.minutes} min by car
              </div>
            </div>
          </Card>
        </div>
      </div>
    </During>
  )
}

