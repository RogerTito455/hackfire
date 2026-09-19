// Lead time for La Atalaya: how long before hotspots came near it the system flagged it.
// Pure types and functions: no React, no fetch, no styling.

/** As served by GET /api/lead-time; computed by `pnpm data:lead-time` from satellite data only. */
export interface LeadTime {
  zone: string
  zone_name: string
  /** Hotspots within this many km of the zone count as the fire's arrival. */
  radius_km: number
  flagged_at: string
  reached_at: string
  minutes: number
  reached_by: { source: string | null; confidence: string | null; distance_km: number }
  /** How the number was computed, in plain words. */
  definition: string
}

/** Whether the system has flagged the zone by replay time `time` (epoch ms). */
export function isFlagged(leadTime: LeadTime | null, time: number | null): boolean {
  return leadTime !== null && time !== null && time >= Date.parse(leadTime.flagged_at)
}

/**
 * The published figure for La Atalaya, for pages that show it without the API (the landing page).
 * Copied from data/lead_time_la-atalaya.json; how it was computed: docs/findings/2026-09-19-lead-time.md.
 */
export const PUBLISHED_LEAD_TIME = {
  zoneName: 'La Atalaya',
  radiusKm: 3,
  flaggedAt: '2026-07-23T13:30:00Z',
  reachedAt: '2026-07-23T19:38:34Z',
  minutes: 368,
} as const
