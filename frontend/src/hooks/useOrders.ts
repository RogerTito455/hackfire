// Evacuation orders per zone and the safe points they can send people to. Polled, so a reset or
// another coordinator's approval shows up within a few seconds.

import { useCallback, useEffect, useState } from 'react'
import type { EvacuationOrder, OrderDecision, SafePoint } from '../domain/orders'
import { approveOrder, fetchOrders, fetchSafePoints } from '../services/api'

const POLL_MS = 5000

export interface Orders {
  orders: EvacuationOrder[]
  safePoints: SafePoint[]
  /** Zone whose approval is being saved, if any. */
  saving: string | null
  error: boolean
  approve: (zone: string, decision: OrderDecision) => Promise<void>
}

export function useOrders(): Orders {
  const [orders, setOrders] = useState<EvacuationOrder[]>([])
  const [safePoints, setSafePoints] = useState<SafePoint[]>([])
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setOrders(await fetchOrders())
      setError(false)
    } catch {
      setError(true)
    }
  }, [])

  useEffect(() => {
    fetchSafePoints()
      .then(setSafePoints)
      .catch(() => setError(true))
    const first = setTimeout(refresh, 0)
    const timer = setInterval(refresh, POLL_MS)
    return () => {
      clearTimeout(first)
      clearInterval(timer)
    }
  }, [refresh])

  const approve = useCallback(
    async (zone: string, decision: OrderDecision) => {
      setSaving(zone)
      try {
        await approveOrder(zone, decision)
        await refresh()
      } catch {
        setError(true)
      } finally {
        setSaving(null)
      }
    },
    [refresh],
  )

  return { orders, safePoints, saving, error, approve }
}
