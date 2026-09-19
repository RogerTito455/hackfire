import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
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
