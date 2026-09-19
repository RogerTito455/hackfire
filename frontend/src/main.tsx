import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './ui/theme.css'
import App from './App.tsx'
import { I18nProvider } from './ui/i18n'
import { registerTileCache } from './services/tileCache'

registerTileCache()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>,
)
