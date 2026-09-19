// The coordinator phones the residents of a zone whose order is approved (#8).

import { useCallback, useState } from 'react'
import { campaignResult, type CampaignResult } from '../domain/voice'
import { startCampaign } from '../services/api'

export interface Campaign {
  /** Zone whose calls are being started, if any. */
  calling: string | null
  result: CampaignResult | null
  call: (zone: string) => Promise<void>
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

  return { calling, result, call }
}
