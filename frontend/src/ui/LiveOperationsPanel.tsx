import { useState } from 'react'
import { dgtClosures, type DgtNear, type DgtRecord } from '../domain/liveDgt'
import {
  geometryCenter,
  placesNearby,
  placesReached,
  roadsToClose,
  type LivePlace,
} from '../domain/liveOperations'
import type { SimulatedFire } from '../domain/liveSpread'
import type { LiveOperationsView } from '../hooks/useLiveOperations'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatAgo, formatMinutesToImpact, formatSpanishTime, spreadModelLabel } from './theme'

interface LiveOperationsPanelProps {
  /** The live fires Deepfire has simulated, which are the ones with places at risk to show. */
  fires: SimulatedFire[]
  view: Pick<LiveOperationsView, 'fireId' | 'status' | 'data' | 'capUrl' | 'focus' | 'focusClosure'>
  onSelect: (fireId: string | null) => void
  onRetry: () => void
}

const VISIBLE_FIRES = 6
const VISIBLE_PLACES = 8

// Live mode: one real fire's places at risk, alert drafts and roads to close. A prediction for the
// coordinator; nothing here is sent to anyone.
export function LiveOperationsPanel({ fires, view, onSelect, onRetry }: LiveOperationsPanelProps) {
  const { t, intl } = useI18n()
  const { fireId, status, data, capUrl, focus, focusClosure } = view
  if (fireId === null) return <FirePicker fires={fires} onSelect={onSelect} />

  const run = fires.find((fire) => fire.fireId === fireId)
  const title = data?.name || run?.name || fireId
  const runAt = data?.runAt ?? run?.runAt
  const model = data?.model ?? run?.model
  return (
    <div className="live-ops">
      <div className="live-ops-head">
        <div>
          <strong className="live-ops-title">{title}</strong>
          {runAt !== undefined && model !== undefined && (
            <p className="live-ops-meta">{t('liveOps.run', { model: spreadModelLabel(model), time: formatSpanishTime(runAt, intl) })}</p>
          )}
        </div>
        <button type="button" className="link live-ops-back" onClick={() => onSelect(null)}>
          {t('liveOps.back')}
        </button>
      </div>
      <p className="live-ops-note" role="note">
        {t('liveOps.note')}
      </p>

      {status === 'no-run' && <p className="empty">{t('liveOps.noRun')}</p>}
      {status === 'loading' && <p className="empty">{t('liveOps.loading')}</p>}
      {status === 'error' && (
        <p className="empty warning">
          {data === null ? t('liveOps.error') : t('liveOps.refreshFailed')}{' '}
          <button type="button" className="link" onClick={onRetry}>
            {t('liveOps.retry')}
          </button>
        </p>
      )}

      {data !== null && (
        <>
          {data.spreadStale && <p className="live-note warn">{t('liveOps.spreadStale')}</p>}
          {data.placesStale && <p className="live-note warn">{t('liveOps.placesStale')}</p>}
          <Places
            reached={placesReached(data)}
            nearby={placesNearby(data)}
            hours={data.durationHours ?? 12}
            metres={data.bufferM}
          />

          <h3 className="subhead icon-button">
            <Icon name="bell" size={16} />
            {t('liveOps.alerts')}
          </h3>
          <p className="live-ops-small">{t('liveOps.alertsNote')}</p>
          {data.alerts.length === 0 ? (
            <p className="empty">{t('liveOps.alertsNone')}</p>
          ) : (
            <ul className="live-drafts">
              {data.alerts.map((alert) => (
                <li key={alert.zoneId}>
                  <span className="draft-badge">{t('liveOps.draft')}</span>
                  <p>{alert.text}</p>
                </li>
              ))}
            </ul>
          )}
          {capUrl !== null && (
            <div className="live-cap">
              <a className="live-cap-button" href={capUrl} download>
                {t('liveOps.cap')}
              </a>
              <p className="live-ops-small">{t('liveOps.capNote')}</p>
            </div>
          )}

          <h3 className="subhead icon-button">
            <Icon name="road-closed" size={16} />
            {t('liveOps.roads')}
            <Count total={roadsToClose(data).length} />
          </h3>
          <p className="live-ops-small">{t('liveOps.roadsNote')}</p>
          <PlaceList
            places={roadsToClose(data)}
            empty={t('liveOps.roadsNone')}
            focus={focus?.kind === 'predicted' ? focus.id : null}
            onFocus={(place) => {
              const center = geometryCenter(place.geometry)
              if (center) focusClosure({ kind: 'predicted', id: place.id, lon: center[0], lat: center[1] })
            }}
          />
          <OfficialDgt
            dgt={data.dgt}
            focus={focus?.kind === 'official' ? focus.id : null}
            onFocus={(record) => focusClosure({ kind: 'official', id: record.id, lon: record.lon, lat: record.lat })}
          />

          <p className="live-ops-small live-ops-calls">{t('liveOps.calls')}</p>
          <p className="live-ops-small">{t('liveOps.source', { time: formatSpanishTime(data.placesFetchedAt, intl) })}</p>
        </>
      )}
    </div>
  )
}

function FirePicker({ fires, onSelect }: { fires: SimulatedFire[]; onSelect: (fireId: string) => void }) {
  const { t, intl } = useI18n()
  const [expanded, setExpanded] = useState(false)
  if (fires.length === 0) return <p className="empty">{t('liveOps.noSimulated')}</p>
  const shown = expanded ? fires : fires.slice(0, VISIBLE_FIRES)
  return (
    <>
      <p className="live-ops-small">{t('liveOps.pick')}</p>
      <ul className="live-fires">
        {shown.map((fire) => (
          <li key={fire.fireId}>
            <button type="button" onClick={() => onSelect(fire.fireId)}>
              <span className="zone-name">{fire.name || fire.fireId}</span>
              <span className="zone-kind">
                {t('liveOps.run', { model: spreadModelLabel(fire.model), time: formatSpanishTime(fire.runAt, intl) })}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {fires.length > VISIBLE_FIRES && (
        <button type="button" className="link" onClick={() => setExpanded(!expanded)}>
          {expanded ? t('liveOps.showFewer') : t('liveOps.showMore', { count: fires.length - VISIBLE_FIRES })}
        </button>
      )}
    </>
  )
}

function Places({ reached, nearby, hours, metres }: { reached: LivePlace[]; nearby: LivePlace[]; hours: number; metres: number }) {
  const { t } = useI18n()
  return (
    <>
      <h3 className="subhead icon-button">
        <Icon name="flame" size={16} />
        {t('liveOps.places')}
      </h3>
      <PlaceList places={reached} empty={t('liveOps.placesNone', { hours })} />
      {nearby.length > 0 && (
        <details className="backup">
          <summary>{t('liveOps.nearby', { count: nearby.length, metres, hours })}</summary>
          <PlaceList places={nearby} empty="" />
        </details>
      )}
    </>
  )
}

/** How many there are, next to a heading, so a truncated list still says its size. */
function Count({ total }: { total: number }) {
  return <span className="subhead-count">{total}</span>
}

function PlaceList({
  places,
  empty,
  focus = null,
  onFocus,
}: {
  places: LivePlace[]
  empty: string
  /** The id of the row the map is showing, when these places are closed roads. */
  focus?: string | null
  onFocus?: (place: LivePlace) => void
}) {
  const { t, intl } = useI18n()
  const [expanded, setExpanded] = useState(false)
  if (places.length === 0) return empty ? <p className="empty">{empty}</p> : null
  // A row the map has picked is worth more than a short list: open the list to show it.
  const open = expanded || places.findIndex((place) => place.id === focus) >= VISIBLE_PLACES
  const shown = open ? places : places.slice(0, VISIBLE_PLACES)
  return (
    <>
      <ul className="zones">
        {shown.map((place) => {
          const body = (
            <>
              <span className="zone-name">{place.name ?? t(`liveOps.kind.${place.kind}`)}</span>
              <span className="zone-kind">
                {t(`liveOps.kind.${place.kind}`)}
                {place.reachesAt !== null && `, ${t('liveOps.at', { time: formatSpanishTime(place.reachesAt, intl) })}`}
              </span>
              {place.minutes !== null && (
                <strong className="zone-time">{formatMinutesToImpact(place.minutes, t('liveOps.due'))}</strong>
              )}
            </>
          )
          const classes = [place.minutes === 0 ? 'zone now' : 'zone']
          if (onFocus) classes.push('tappable')
          if (place.id === focus) classes.push('picked')
          return (
            <li key={place.id} className={classes.join(' ')}>
              {onFocus ? (
                <button type="button" onClick={() => onFocus(place)} aria-label={t('liveOps.showOnMap')}>
                  {body}
                </button>
              ) : (
                body
              )}
            </li>
          )
        })}
      </ul>
      {places.length > VISIBLE_PLACES && (
        <button type="button" className="link" onClick={() => setExpanded(!open)}>
          {open ? t('liveOps.showFewer') : t('liveOps.showMore', { count: places.length - VISIBLE_PLACES })}
        </button>
      )}
    </>
  )
}

// Official data from the DGT, kept apart from HackFire's suggestions above: what the traffic authority
// itself publishes near this fire (forest-fire incidents, roads and carriageways closed).
function OfficialDgt({
  dgt,
  focus,
  onFocus,
}: {
  dgt: DgtNear
  /** The id of the record the map is showing. */
  focus: string | null
  onFocus: (record: DgtRecord) => void
}) {
  const { t, intl } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const open = expanded || dgt.records.findIndex((record) => record.id === focus) >= VISIBLE_PLACES
  const shown = open ? dgt.records : dgt.records.slice(0, VISIBLE_PLACES)
  return (
    <section className="live-dgt" aria-label={t('liveOps.dgt')}>
      <h3 className="subhead icon-button">
        <Icon name="road-closed" size={16} />
        {t('liveOps.dgt')}
        <span className="official-badge">{t('liveOps.official')}</span>
        {dgt.available && <Count total={dgt.records.length} />}
      </h3>
      <p className="live-ops-small">{t('liveOps.dgtNote', { km: Math.round((dgt.nearM ?? 5000) / 1000) })}</p>
      {!dgt.available && <p className="empty warning">{t('liveOps.dgtUnavailable')}</p>}
      {dgt.available && dgt.stale && dgt.fetchedAt !== null && (
        <p className="live-note warn">{t('liveOps.dgtStale', { time: formatSpanishTime(dgt.fetchedAt, intl) })}</p>
      )}
      {dgt.available && dgt.records.length === 0 && <p className="empty">{t('liveOps.dgtNone')}</p>}
      {dgt.records.length > 0 && (
        <ul className="zones">
          {shown.map((record) => {
            const classes = ['zone', 'dgt', 'tappable']
            if (record.kind === 'forestFire') classes.push('fire')
            if (record.id === focus) classes.push('picked')
            return (
              <li key={record.id} className={classes.join(' ')}>
                <button type="button" onClick={() => onFocus(record)} aria-label={t('liveOps.showOnMap')}>
                  <span className="zone-name">
                    {record.road ?? t('liveOps.dgtNoRoad')}
                    {record.km !== null && `, ${t('liveOps.dgtKm', { km: record.km })}`}
                  </span>
                  <span className="zone-kind">
                    {record.kind === 'forestFire'
                      ? `${t('liveOps.dgtType.forestFire')}, ${t(`liveOps.dgtType.${record.management}`)}`
                      : `${t(`liveOps.dgtType.${record.kind}`)}, ${t(`liveOps.dgtCause.${record.cause}`)}`}
                    {record.municipality !== null && `, ${record.municipality}`}
                  </span>
                  {record.since !== null && (
                    <span className="zone-kind dgt-since">
                      {t('liveOps.dgtSince', { time: formatSpanishTime(record.since, intl) })}
                      {dgt.fetchedAt !== null &&
                        `, ${t('liveOps.dgtFor', { age: formatAgo(dgt.fetchedAt - record.since) })}`}
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {dgt.records.length > VISIBLE_PLACES && (
        <button type="button" className="link" onClick={() => setExpanded(!open)}>
          {open ? t('liveOps.showFewer') : t('liveOps.showMore', { count: dgt.records.length - VISIBLE_PLACES })}
        </button>
      )}
      {dgtClosures(dgt.records).length > 0 && <p className="live-ops-small">{t('liveOps.dgtOnMap')}</p>}
      <p className="live-ops-small">{t('liveOps.dgtSource')}</p>
    </section>
  )
}
