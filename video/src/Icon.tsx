// HackFire's own icons (frontend/src/ui/icons), the same paths, so the video speaks the dashboard's
// visual language. Rounded outline, 24 × 24, stroke in the current colour.

import type { ReactNode } from 'react'

const PATHS: Record<string, ReactNode> = {
  logo: (
    <>
      <path d="M12 3l7 2.8v5.7c0 4.6-3 8.2-7 9.5-4-1.3-7-4.9-7-9.5V5.8z" />
      <path d="M12 7c.3 2 3.5 3.5 3.5 7a3.5 3.5 0 0 1-7 0c0-1.6.7-2.8 1.5-3.5.1 1 .6 1.6 1.2 1.9-.2-2 .1-3.8.8-5.4z" />
    </>
  ),
  flame: <path d="M12 3c.5 3.5 6 6 6 12a6 6 0 0 1-12 0c0-2.8 1.2-4.8 2.6-6 .2 1.8 1 2.8 2 3.2-.4-3.4.2-6.6 1.4-9.2z" />,
  satellite: (
    <>
      <path d="M13.5 7.7l2.8 2.8-2.8 2.8-2.8-2.8z" />
      <path d="M9.6 3.1l2.8 2.8-3.5 3.5-2.8-2.8z" />
      <path d="M17.4 17.9l-2.8-2.8 3.5-3.5 2.8 2.8z" />
      <path d="M12.1 9.1l-1.4-1.4M14.9 11.9l1.4 1.4" />
      <path d="M7.9 12.6a6 6 0 0 0 3.6 3.6M4.9 14.5a9.5 9.5 0 0 0 4.6 4.6" />
    </>
  ),
  phone: (
    <>
      <path d="M5 4h2.5L9 8l-2 1.5a11 11 0 0 0 6.5 6.5l1.5-2 4 1.5V18a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2z" />
      <path d="M14.5 3.5a6 6 0 0 1 6 6M14.5 7.5a2 2 0 0 1 2 2" />
    </>
  ),
  'phone-missed': (
    <>
      <path d="M5 4h2.5L9 8l-2 1.5a11 11 0 0 0 6.5 6.5l1.5-2 4 1.5V18a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2z" />
      <path d="M16 4l4 4M20 4l-4 4" />
    </>
  ),
  lifebuoy: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M5.6 5.6l3.6 3.6M18.4 5.6l-3.6 3.6M18.4 18.4l-3.6-3.6M5.6 18.4l3.6-3.6" />
    </>
  ),
  'fire-truck': (
    <>
      <path d="M5 18H4a1 1 0 0 1-1-1v-5a1 1 0 0 1 1-1h10V8a1 1 0 0 1 1-1h2.2a1 1 0 0 1 .8.4l3 4.1V17a1 1 0 0 1-1 1h-1" />
      <path d="M9 18h6M14 11.5h7" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="17" cy="18" r="2" />
      <path d="M3 6.5l10-3M5.5 5.8V11M10 4.4V11" />
    </>
  ),
  exit: (
    <>
      <path d="M14 8V4a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-4" />
      <path d="M9 12h12M18 9l3 3-3 3" />
    </>
  ),
  home: (
    <>
      <path d="M3 11l9-8 9 8" />
      <path d="M5 9v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9" />
      <path d="M10 20v-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5" />
    </>
  ),
  hourglass: (
    <>
      <path d="M5 3h14M5 21h14" />
      <path d="M7 3v3.5l5 5.5 5-5.5V3" />
      <path d="M7 21v-3.5l5-5.5 5 5.5V21" />
    </>
  ),
  route: (
    <>
      <circle cx="6" cy="19" r="2" />
      <circle cx="18" cy="5" r="2" />
      <path d="M6 17C6 9 18 15 18 7" />
    </>
  ),
  bell: (
    <>
      <path d="M6 9a6 6 0 0 1 12 0v4.5l2 2.5H4l2-2.5z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </>
  ),
  flag: (
    <>
      <path d="M5 21V4" />
      <path d="M5 4h13l-3 4.5 3 4.5H5" />
    </>
  ),
  live: (
    <>
      <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7M8.5 15.5a5 5 0 0 1 0-7" />
      <path d="M18.4 5.6a9 9 0 0 1 0 12.8M5.6 18.4a9 9 0 0 1 0-12.8" />
    </>
  ),
  car: (
    <>
      <path d="M5 11l1.6-4.3a2 2 0 0 1 1.9-1.3h7a2 2 0 0 1 1.9 1.3L19 11" />
      <rect x="3" y="11" width="18" height="7" rx="2" />
      <path d="M6 18v2M18 18v2M7 14.5h1M16 14.5h1" />
    </>
  ),
  // The video's own, in the same format: a microphone, a check and a broadcast tower.
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </>
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  tower: (
    <>
      <path d="M12 10l-4 11M12 10l4 11M9.2 17.5h5.6" />
      <circle cx="12" cy="8" r="1.5" />
      <path d="M8.5 4.5a5 5 0 0 0 0 7M15.5 4.5a5 5 0 0 1 0 7" />
    </>
  ),
}

export const STATUS_ICON = { pending: 'hourglass', evacuating: 'exit', no_answer: 'phone-missed', needs_rescue: 'lifebuoy' } as const

export function Icon({ name, size = 24, color = 'currentColor', stroke = 2 }: { name: string; size?: number; color?: string; stroke?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block', flex: 'none', color }}>
      {PATHS[name]}
    </svg>
  )
}
