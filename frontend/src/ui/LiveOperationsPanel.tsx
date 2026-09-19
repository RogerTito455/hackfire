import { useState } from 'react'
import { placesNearby, placesReached, roadsToClose, type LivePlace } from '../domain/liveOperations'
import type { SimulatedFire } from '../domain/liveSpread'
import type { LiveOperationsView } from '../hooks/useLiveOperations'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatMinutesToImpact, formatSpanishTime, spreadModelLabel } from './theme'

interface LiveOperationsPanelProps {
  /** The live fires Deepfire has simulated, which are the ones with places at risk to show. */
  fires: SimulatedFire[]
  view: Pick<LiveOperationsView, 'fireId' | 'status' | 'data'>
  onSelect: (fireId: string | null) => void
  onRetry: () => void
}

const VISIBLE_FIRES = 6
const VISIBLE_PLACES = 8

// Live mode: one real fire's places at risk, alert drafts and roads to close. A prediction for the
// coordinator; nothing here is sent to anyone.
export function LiveOperationsPanel({ fires, view, onSelect, onRetry }: LiveOperationsPanelProps) {
  const { t, intl } = useI18n()
  const { fireId, status, data } = view
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

          <h3 className="subhead icon-button">
            <Icon name="road-closed" size={16} />
            {t('liveOps.roads')}
          </h3>
          <p className="live-ops-small">{t('liveOps.roadsNote')}</p>
          <PlaceList places={roadsToClose(data)} empty={t('liveOps.roadsNone')} />

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

function PlaceList({ places, empty }: { places: LivePlace[]; empty: string }) {
  const { t, intl } = useI18n()
  const [expanded, setExpanded] = useState(false)
  if (places.length === 0) return empty ? <p className="empty">{empty}</p> : null
  const shown = expanded ? places : places.slice(0, VISIBLE_PLACES)
  return (
    <>
      <ul className="zones">
        {shown.map((place) => (
          <li key={place.id} className={place.minutes === 0 ? 'zone now' : 'zone'}>
            <span className="zone-name">{place.name ?? t(`liveOps.kind.${place.kind}`)}</span>
            <span className="zone-kind">
              {t(`liveOps.kind.${place.kind}`)}
              {place.reachesAt !== null && `, ${t('liveOps.at', { time: formatSpanishTime(place.reachesAt, intl) })}`}
            </span>
            {place.minutes !== null && (
              <strong className="zone-time">{formatMinutesToImpact(place.minutes, t('liveOps.due'))}</strong>
            )}
          </li>
        ))}
      </ul>
      {places.length > VISIBLE_PLACES && (
        <button type="button" className="link" onClick={() => setExpanded(!expanded)}>
          {expanded ? t('liveOps.showFewer') : t('liveOps.showMore', { count: places.length - VISIBLE_PLACES })}
        </button>
      )}
    </>
  )
}
