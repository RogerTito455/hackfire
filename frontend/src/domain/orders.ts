// Evacuation orders per zone: proposed by the system, approved or changed by the coordinator.
// Mirrors EvacuationOrder, OrderDecision and SafePoint in backend/app/models.py.

export type OrderAction = 'evacuate' | 'shelter'

export interface EvacuationOrder {
  zone: string
  zone_name: string
  residents: number
  minutes_to_impact: number | null
  proposed_action: OrderAction
  proposed_destination_id: string | null
  action: OrderAction
  destination_id: string | null
  destination_name: string | null
  approved: boolean
  /** What the agent tells everyone in the zone once approved. */
  message: string
}

export interface OrderDecision {
  action: OrderAction
  destination_id?: string | null
}

export interface SafePoint {
  id: string
  name: string
  lat: number
  lon: number
  /** Outside the forecast and at least 3 km from the fire at the scenario time. */
  safe: boolean
}

/** A select option's value: a safe point id, or SHELTER. */
export const SHELTER = 'shelter'

export function decisionFromChoice(choice: string): OrderDecision {
  return choice === SHELTER ? { action: 'shelter' } : { action: 'evacuate', destination_id: choice }
}

export function currentChoice(order: EvacuationOrder): string {
  return order.action === 'shelter' ? SHELTER : (order.destination_id ?? SHELTER)
}

export function proposedChoice(order: EvacuationOrder): string {
  return order.proposed_action === 'shelter' ? SHELTER : (order.proposed_destination_id ?? SHELTER)
}
