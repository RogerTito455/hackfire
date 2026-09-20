import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// The Content-Security-Policy in index.html suits the built app. Vite's dev server injects an inline
// script for hot reload, which that policy would block, so `pnpm dev:web` gets the page without it.
const devWithoutCsp: Plugin = {
  name: 'dev-without-csp',
  apply: 'serve',
  transformIndexHtml: (html) => html.replace(/<meta\s+http-equiv="Content-Security-Policy"[^>]*>/s, ''),
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), devWithoutCsp],
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
