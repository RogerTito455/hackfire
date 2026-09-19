// The landing page at /about: what HackFire is, for judges and visitors, and the way into the
// dashboard at /. Composition root only: static content in, UI out.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './ui/theme.css'
import { leadTimeRange, PUBLISHED_LEAD_TIME } from './domain/leadTime'
import { I18nProvider } from './ui/i18n'
import { Landing } from './ui/landing/Landing'

// The dashboard is served from the same deployment, at the root.
const DEMO_URL = '/'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <Landing demoUrl={DEMO_URL} leadTime={PUBLISHED_LEAD_TIME} leadTimeRange={leadTimeRange(PUBLISHED_LEAD_TIME)} />
    </I18nProvider>
  </StrictMode>,
)
