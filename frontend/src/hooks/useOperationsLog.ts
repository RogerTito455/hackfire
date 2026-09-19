// The activity log (polled, since the agent and the autopilot write to it too) and the provider
// status (polled once a minute; the backend caches its checks for about as long).

import { useCallback, useEffect, useState } from 'react'
import type { AuditEvent, ProviderStatus } from '../domain/operations'
import { auditDownloadUrl, fetchAudit, fetchProviderStatus } from '../services/api'

const AUDIT_POLL_MS = 3000
const AUDIT_LIMIT = 15
const STATUS_POLL_MS = 60_000

export interface ActivityLog {
  events: AuditEvent[]
  /** false until the first answer; true if the last poll failed. */
  loaded: boolean
  failed: boolean
  downloadUrl: string
}

export interface ServiceStatus {
  providers: ProviderStatus[]
  loaded: boolean
  failed: boolean
}

function usePolling<T>(load: () => Promise<T>, everyMs: number, initial: T) {
  const [data, setData] = useState<T>(initial)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setData(await load())
      setFailed(false)
      setLoaded(true)
    } catch {
      // Keep the last answer; the next poll tries again.
      setFailed(true)
    }
  }, [load])

  useEffect(() => {
    const first = setTimeout(refresh, 0)
    const timer = setInterval(refresh, everyMs)
    return () => {
      clearTimeout(first)
      clearInterval(timer)
    }
  }, [refresh, everyMs])

  return { data, loaded, failed }
}

const loadAudit = () => fetchAudit(AUDIT_LIMIT)

export function useActivityLog(locale: string): ActivityLog {
  const { data, loaded, failed } = usePolling(loadAudit, AUDIT_POLL_MS, [] as AuditEvent[])
  return { events: data, loaded, failed, downloadUrl: auditDownloadUrl(locale) }
}

export function useServiceStatus(): ServiceStatus {
  const { data, loaded, failed } = usePolling(fetchProviderStatus, STATUS_POLL_MS, [] as ProviderStatus[])
  return { providers: data, loaded, failed }
}
