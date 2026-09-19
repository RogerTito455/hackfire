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

/** The published lead time for one zone, and how it moves with the radius taken as "arrival". */
export interface PublishedLeadTime {
  zoneName: string
  flaggedAt: string
  /** The radius of the published figure. */
  radiusKm: number
  /** Lead time in minutes by the radius within which a hotspot counts as the fire's arrival. */
  byRadius: readonly { radiusKm: number; minutes: number }[]
}

/**
 * The published figure for La Atalaya, for pages that show it without the API (the landing page).
 * The 3 km row is data/lead_time_la-atalaya.json; the others are the radius table in
 * docs/findings/2026-09-19-lead-time.md. If `pnpm data:lead-time` changes them, update both.
 */
export const PUBLISHED_LEAD_TIME: PublishedLeadTime = {
  zoneName: 'La Atalaya',
  flaggedAt: '2026-07-23T13:30:00Z',
  radiusKm: 3,
  byRadius: [
    { radiusKm: 2, minutes: 489 },
    { radiusKm: 3, minutes: 368 },
    { radiusKm: 4, minutes: 358 },
    { radiusKm: 5, minutes: 298 },
  ],
}

/**
 * The lead time as an honest range rather than a precise count: one medium-confidence pixel
 * decides the arrival, and the model's constants were tuned on this same fire.
 */
export interface LeadTimeRange {
  /** The published radius's figure, rounded to the hour. */
  aboutHours: number
  minHours: number
  maxHours: number
  nearKm: number
  farKm: number
  /** Epoch ms: the flag, the published radius's first hotspot, and the first hotspot at the far and near radii. */
  flagged: number
  reached: number
  earliest: number
  latest: number
}

export function leadTimeRange(published: PublishedLeadTime): LeadTimeRange {
  const flagged = Date.parse(published.flaggedAt)
  const rows = [...published.byRadius].sort((a, b) => a.radiusKm - b.radiusKm)
  const main = rows.find((row) => row.radiusKm === published.radiusKm) ?? rows[0]
  const minutes = rows.map((row) => row.minutes)
  const at = (m: number) => flagged + m * 60_000
  return {
    aboutHours: Math.round(main.minutes / 60),
    minHours: Math.round(Math.min(...minutes) / 60),
    maxHours: Math.round(Math.max(...minutes) / 60),
    nearKm: rows[0].radiusKm,
    farKm: rows[rows.length - 1].radiusKm,
    flagged,
    reached: at(main.minutes),
    earliest: at(Math.min(...minutes)),
    latest: at(Math.max(...minutes)),
  }
}
