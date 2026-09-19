// Whether the backend can phone residents and open browser conversations with the agent.

import { useEffect, useState } from 'react'
import type { VoiceCapabilities } from '../domain/voice'
import { fetchVoiceCapabilities } from '../services/api'

const NONE: VoiceCapabilities = { phone_calls: false, web_sessions: false }

export function useVoiceCapabilities(): VoiceCapabilities {
  const [capabilities, setCapabilities] = useState<VoiceCapabilities>(NONE)

  useEffect(() => {
    fetchVoiceCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(NONE))
  }, [])

  return capabilities
}
