// The coordinator phones the residents of a zone whose order is approved (#8).

import { useCallback, useState } from 'react'
import { campaignResult, type CampaignResult } from '../domain/voice'
import { callOneResident, startCampaign } from '../services/api'

export interface Campaign {
  /** Zone whose calls are being started, if any. */
  calling: string | null
  result: CampaignResult | null
  call: (zone: string) => Promise<void>
  /** The resident whose own phone is being rung, if any. */
  ringing: string | null
  /** The last single call: who it was for, whether a line was dialled, and why not. */
  rang: { neighborId: string; placed: boolean; status: number | null } | null
  /** Ring one resident's phone, for a rehearsal or for the demo itself. */
  callOne: (neighborId: string) => Promise<void>
}

export function useCampaign(): Campaign {
  const [calling, setCalling] = useState<string | null>(null)
  const [result, setResult] = useState<CampaignResult | null>(null)

  const call = useCallback(async (zone: string) => {
    setCalling(zone)
    setResult(null)
    try {
      setResult(campaignResult(zone, await startCampaign(zone)))
    } catch {
      setResult({ zone, placed: null, refused: null })
    } finally {
      setCalling(null)
    }
  }, [])

  const [ringing, setRinging] = useState<string | null>(null)
  const [rang, setRang] = useState<{ neighborId: string; placed: boolean; status: number | null } | null>(null)

  const callOne = useCallback(async (neighborId: string) => {
    setRinging(neighborId)
    setRang(null)
    try {
      const call = await callOneResident(neighborId)
      setRang({ neighborId, placed: call.call_id !== null, status: null })
    } catch (error) {
      // request() puts the status in its message: the panel says what to do about each one.
      const status = Number(/returned (\d+)/.exec(String(error))?.[1]) || null
      setRang({ neighborId, placed: false, status })
    } finally {
      setRinging(null)
    }
  }, [])

  return { calling, result, call, ringing, rang, callOne }
}
