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

// Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: the client no longer carries a
// loopback address. Under `pnpm dev:web` the dashboard asks its own origin and this proxy passes
// /api, /tools and /health to the backend that `pnpm dev:api` starts.
const BACKEND = 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), devWithoutCsp],
  server: {
    proxy: { '/api': BACKEND, '/tools': BACKEND, '/health': BACKEND },
  },
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
