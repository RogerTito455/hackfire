import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './ui/theme.css'
import App from './App.tsx'
import { I18nProvider } from './ui/i18n'
import ResidentApp from './ResidentApp.tsx'
import { registerTileCache } from './services/tileCache'

registerTileCache()

// A resident's video link (#18) opens the camera page; everything else is the coordinator's dashboard.
const videoLink = /^\/v\/([^/]+)/.exec(window.location.pathname)?.[1]

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>{videoLink ? <ResidentApp linkId={videoLink} /> : <App />}</I18nProvider>
  </StrictMode>,
)
