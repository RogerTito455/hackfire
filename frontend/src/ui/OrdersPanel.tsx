import { useState } from 'react'
import {
  currentChoice,
  decisionFromChoice,
  proposedChoice,
  SHELTER,
  type EvacuationOrder,
  type OrderDecision,
  type SafePoint,
} from '../domain/orders'
import type { CampaignResult } from '../domain/voice'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatMinutesToImpact, ORDER_STATE_COLOR } from './theme'

interface OrdersPanelProps {
  orders: EvacuationOrder[]
  safePoints: SafePoint[]
  saving: string | null
  onApprove: (zone: string, decision: OrderDecision) => void
  /** Whether a phone line is set up to call residents (#8). */
  phoneCalls: boolean
  /** Zone whose calls are being started, and the last campaign's result. */
  calling: string | null
  campaign: CampaignResult | null
  onCall: (zone: string) => void
}

type Translate = ReturnType<typeof useI18n>['t']

function campaignText({ placed, refused }: CampaignResult, t: Translate): string {
  if (placed === null || refused === null) return t('orders.callsFailed')
  if (placed === 0 && refused === 0) return t('orders.nobodyToCall')
  const parts = []
  if (placed > 0) parts.push(t('orders.callsPlaced', { count: placed }))
  if (refused > 0) parts.push(t('orders.callsRefused', { count: refused }))
  return parts.join(' ')
}

function impactText(minutes: number | null, t: Translate): string {
  if (minutes === null) return t('orders.impactNone')
  if (minutes === 0) return t('orders.impactNow')
  return t('orders.impactIn', { time: formatMinutesToImpact(minutes, t('time.now')) })
}

// One order per zone: the coordinator confirms the proposal or picks another destination, and the
// agent reads the approved order to everyone in that zone.
export function OrdersPanel({ orders, safePoints, saving, onApprove, phoneCalls, calling, campaign, onCall }: OrdersPanelProps) {
  const { t } = useI18n()
  const [drafts, setDrafts] = useState<Record<string, string>>({})

  if (orders.length === 0) return <p className="empty">{t('orders.empty')}</p>

  return (
    <ol className="orders">
      {orders.map((order) => {
        const state = order.approved ? 'approved' : 'proposed'
        const choice = drafts[order.zone] ?? currentChoice(order)
        const changed = choice !== currentChoice(order)
        return (
          <li key={order.zone} style={{ borderLeftColor: ORDER_STATE_COLOR[state] }}>
            <div className="order-head">
              <strong>{order.zone_name}</strong>
              <span className="order-state" style={{ color: ORDER_STATE_COLOR[state] }}>
                {t(`orders.${state}`)}
              </span>
            </div>
            <span className="order-meta">
              {t('orders.residents', { count: order.residents })}, {impactText(order.minutes_to_impact, t)}
            </span>
            <label className="order-choice">
              <span className="visually-hidden">{t('orders.choice', { zone: order.zone_name })}</span>
              <select
                value={choice}
                onChange={(event) => setDrafts({ ...drafts, [order.zone]: event.target.value })}
              >
                {safePoints
                  .filter((point) => point.name !== order.zone_name)
                  .map((point) => (
                    // Norma js-nested-ternary: the tag after a safe point's name is one value with
                    // three cases, written in the order a reader needs them — proposed, plain, not
                    // safe. A lookup table or a helper would move it away from the option it labels
                    // without making it shorter.
                    <option key={point.id} value={point.id}>
                      {t('orders.leaveFor', { place: point.name })}
                      {point.id === proposedChoice(order) ? t('orders.proposedTag') : point.safe ? '' : t('orders.unsafeTag')}
                    </option>
                  ))}
                <option value={SHELTER}>
                  {t('orders.stayIndoors')}
                  {proposedChoice(order) === SHELTER ? t('orders.proposedTag') : ''}
                </option>
              </select>
            </label>
            {(!order.approved || changed) && (
              <button
                type="button"
                className="order-approve icon-button"
                disabled={saving === order.zone}
                onClick={() => {
                  onApprove(order.zone, decisionFromChoice(choice))
                  setDrafts((current) => {
                    const next = { ...current }
                    delete next[order.zone]
                    return next
                  })
                }}
              >
                <Icon name={choice === SHELTER ? 'home' : 'flag'} size={16} />
                {/* Norma js-nested-ternary: the button's three states in the order they happen —
                    saving, already approved, not approved yet. It is the label, on the button. */}
                {saving === order.zone ? t('orders.saving') : order.approved ? t('orders.change') : t('orders.approve')}
              </button>
            )}
            {order.approved && !changed && <p className="order-message">“{order.message}”</p>}
            {order.approved && !changed && phoneCalls && (
              <button
                type="button"
                className="order-approve icon-button"
                disabled={calling === order.zone}
                onClick={() => onCall(order.zone)}
              >
                <Icon name="live" size={16} />
                {calling === order.zone ? t('orders.calling') : t('orders.call')}
              </button>
            )}
            {order.approved && !changed && !phoneCalls && (
              <p className="empty">{t('orders.noLine')}</p>
            )}
            {campaign?.zone === order.zone && <p className="empty">{campaignText(campaign, t)}</p>}
          </li>
        )
      })}
    </ol>
  )
}
