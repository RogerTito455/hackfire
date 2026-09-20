import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // The demo phone is a Galaxy S9+ on Chrome 101, which does not understand the media-query range
    // syntax (`(width>=900px)`, Chrome 104). The minifier rewrites every `min-width`/`max-width`
    // query into it unless it is told how old the oldest browser is, and Chrome 101 then drops the
    // whole at-rule: no phone layout, no bottom sheet, labels that should be hidden left to clip.
    cssTarget: 'chrome101',
    // Two pages: the dashboard (index.html, served at /) and the landing page (about.html, served
    // at /about by the backend; Vite's dev server answers /about too).
    rolldownOptions: {
      input: {
        dashboard: fileURLToPath(new URL('./index.html', import.meta.url)),
        about: fileURLToPath(new URL('./about.html', import.meta.url)),
      },
    },
  },
})
