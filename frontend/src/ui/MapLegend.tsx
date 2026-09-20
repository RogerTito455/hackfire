import { useState, type ReactNode } from 'react'
import type { MapMode } from '../hooks/useMapMode'
import { TRIAGE_STATUSES } from '../domain/triage'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { useWideScreen } from './useWideScreen'
import {
  DGT_CLOSURE_COLOR,
  HOTSPOT_AGE_COLORS,
  LIVE_RECENCY_COLORS,
  ROAD_CLOSED_COLOR,
  ROUTE_COLOR,
  SPREAD_HOUR_COLORS,
  STATUS_COLOR,
  STATUS_ICON,
  ZONE_URGENCY_COLORS,
} from './theme'

// What every colour and symbol on the map means, on the map itself. It used to be spread between a
// legend inside the fire section and nothing at all, so a road drawn in red and a road drawn in grey
// were the same thing to anyone who had not built this. Open on a laptop, folded away on a phone.

function ramp(colors: readonly (readonly [number, string])[]) {
  return `linear-gradient(to right, ${colors.map(([, color]) => color).join(', ')})`
}

function Row({ swatch, name, from, to }: { swatch: ReactNode; name: string; from?: string; to?: string }) {
  return (
    <li className="legend-row">
      {swatch}
      <span className="legend-name">
        {name}
        {from !== undefined && to !== undefined && (
          <small className="legend-scale">
            {from} – {to}
          </small>
        )}
      </span>
    </li>
  )
}

/** Whether the map is wide enough for the open key: false once the console has taken the room. */
export function MapLegend({ mode, room = true }: { mode: MapMode; room?: boolean }) {
  const { t } = useI18n()
  const wide = useWideScreen()
  const roomy = wide && room
  const [open, setOpen] = useState(roomy)
  // Crossing the breakpoint, or the divider leaving the map too narrow, decides it again: open
  // where there is room, folded where it would cover the map. Adjusted during render, not in an effect.
  const [lastRoomy, setLastRoomy] = useState(roomy)
  if (roomy !== lastRoomy) {
    setLastRoomy(roomy)
    setOpen(roomy)
  }
  return (
    <details className="map-legend" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>{t('legend.title')}</summary>
      <ul>
        {mode === 'replay' ? (
          <>
            <Row
              swatch={<span className="legend-ramp" style={{ background: ramp(HOTSPOT_AGE_COLORS) }} />}
              name={t('legend.hotspots')}
              from={t('replay.fresh')}
              to={t('replay.old')}
            />
            <Row
              swatch={<span className="legend-ramp" style={{ background: ramp(SPREAD_HOUR_COLORS) }} />}
              name={t('legend.forecast')}
              from={t('fire.legendNow')}
              to={t('fire.legendAhead')}
            />
            <Row
              swatch={<span className="legend-zone" style={{ background: ZONE_URGENCY_COLORS[1][1] }} />}
              name={t('legend.zone')}
            />
            <Row swatch={<span className="legend-line" style={{ background: ROUTE_COLOR }} />} name={t('section.wayOut')} />
            <Row
              swatch={
                <span
                  className="legend-line dashed"
                  style={{ background: `repeating-linear-gradient(to right, ${ROAD_CLOSED_COLOR} 0 5px, transparent 5px 9px)` }}
                />
              }
              name={t('legend.fireRoad')}
            />
            <Row
              swatch={
                <span className="legend-marker" aria-hidden="true">
                  <Icon name="road-closed" size={14} />
                </span>
              }
              name={t('legend.closed')}
            />
            <li className="legend-row states">
              <span className="legend-states">
                {TRIAGE_STATUSES.map((status) => (
                  <span key={status} style={{ color: STATUS_COLOR[status] }}>
                    <Icon name={STATUS_ICON[status]} size={14} />
                  </span>
                ))}
              </span>
              <span className="legend-name">{t('legend.residents')}</span>
            </li>
          </>
        ) : (
          <>
            <Row
              swatch={<span className="legend-dot" style={{ background: LIVE_RECENCY_COLORS[0][1] }} />}
              name={t('legend.fires')}
            />
            <Row
              swatch={<span className="legend-ramp" style={{ background: ramp(SPREAD_HOUR_COLORS) }} />}
              name={t('legend.forecast')}
              from={t('fire.legendNow')}
              to={t('fire.legendAhead')}
            />
            <Row swatch={<span className="legend-triangle" aria-hidden="true" />} name={t('legend.dgt')} />
            <Row
              swatch={
                <span
                  className="legend-line dashed"
                  style={{ background: `repeating-linear-gradient(to right, ${DGT_CLOSURE_COLOR} 0 5px, transparent 5px 9px)` }}
                />
              }
              name={t('legend.dgtClosed')}
            />
            <Row
              swatch={
                <span
                  className="legend-line dashed"
                  style={{ background: `repeating-linear-gradient(to right, ${ROAD_CLOSED_COLOR} 0 5px, transparent 5px 9px)` }}
                />
              }
              name={t('legend.predictedClosed')}
            />
          </>
        )}
      </ul>
    </details>
  )
}
