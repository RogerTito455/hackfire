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
import { ORDER_STATE_COLOR, ORDER_STATE_LABEL } from './theme'

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

function residents(count: number): string {
  return `${count} ${count === 1 ? 'resident' : 'residents'}`
}

function campaignText({ placed, refused }: CampaignResult): string {
  if (placed === null || refused === null) return 'Could not start the calls.'
  if (placed === 0 && refused === 0) return 'Nobody to call: every resident already has a status or a call going.'
  const parts = []
  if (placed > 0) parts.push(`Calling ${residents(placed)}; unanswered calls turn into No answer.`)
  if (refused > 0) parts.push(`SLNG refused the calls to ${residents(refused)}: marked No answer.`)
  return parts.join(' ')
}

function impactText(minutes: number | null): string {
  if (minutes === null) return 'not in the forecast'
  if (minutes === 0) return 'fire already there'
  if (minutes < 60) return `fire in ${minutes} min`
  return `fire in ${Math.floor(minutes / 60)} h ${minutes % 60 ? `${minutes % 60} min` : ''}`.trim()
}

// One order per zone: the coordinator confirms the proposal or picks another destination, and the
// agent reads the approved order to everyone in that zone.
export function OrdersPanel({ orders, safePoints, saving, onApprove, phoneCalls, calling, campaign, onCall }: OrdersPanelProps) {
  const [drafts, setDrafts] = useState<Record<string, string>>({})

  if (orders.length === 0) return <p className="empty">No zones with residents in the registry.</p>

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
                {ORDER_STATE_LABEL[state]}
              </span>
            </div>
            <span className="order-meta">
              {order.residents} {order.residents === 1 ? 'resident' : 'residents'} · {impactText(order.minutes_to_impact)}
            </span>
            <label className="order-choice">
              <span className="visually-hidden">Order for {order.zone_name}</span>
              <select
                value={choice}
                onChange={(event) => setDrafts({ ...drafts, [order.zone]: event.target.value })}
              >
                {safePoints
                  .filter((point) => point.name !== order.zone_name)
                  .map((point) => (
                    <option key={point.id} value={point.id}>
                      Leave for {point.name}
                      {point.id === proposedChoice(order) ? ' (proposed)' : point.safe ? '' : ' (not safe now)'}
                    </option>
                  ))}
                <option value={SHELTER}>
                  Stay indoors{proposedChoice(order) === SHELTER ? ' (proposed)' : ''}
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
                {saving === order.zone ? 'Saving…' : order.approved ? 'Change order' : 'Approve order'}
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
                {calling === order.zone ? 'Calling…' : 'Call residents'}
              </button>
            )}
            {order.approved && !changed && !phoneCalls && (
              <p className="empty">No phone line: take each resident's call from their panel.</p>
            )}
            {campaign?.zone === order.zone && <p className="empty">{campaignText(campaign)}</p>}
          </li>
        )
      })}
    </ol>
  )
}
