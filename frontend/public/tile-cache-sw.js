// Keeps the OpenStreetMap tiles the dashboard has shown, so the demo map survives a flaky venue
// network (#13): open the dashboard once on good Wi-Fi, pan over the demo area, and those tiles
// are served from this cache from then on. Only tile requests are touched; the API, the app and
// everything else go straight to the network.

const CACHE = 'hackfire-osm-tiles-v1'
const MAX_TILES = 4000
const TILE_HOST = 'tile.openstreetmap.org'
const NETWORK_TIMEOUT_MS = 20000

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

async function trim(cache) {
  // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: trimming is housekeeping, so a
  // failure is logged and never reaches the tile that triggered it.
  try {
    const keys = await cache.keys()
    for (const key of keys.slice(0, Math.max(0, keys.length - MAX_TILES))) await cache.delete(key)
  } catch (error) {
    console.error('Could not trim the tile cache', error)
  }
}

// The cache is a bonus and the network is the source: if the cache cannot be opened or read, go to the
// network; if the network fails too, answer with a network error, as the browser would have.
async function tile(request) {
  let cache = null
  try {
    cache = await caches.open(CACHE)
    const hit = await cache.match(request)
    if (hit) return hit
  } catch (error) {
    console.error('The tile cache is unavailable; using the network', error)
  }
  // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a stalled tile request gives
  // up. An AbortController rather than AbortSignal.timeout, which iOS before 16 lacks.
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), NETWORK_TIMEOUT_MS)
  try {
    const response = await fetch(request, { signal: controller.signal })
    if (response.ok && cache) {
      try {
        await cache.put(request, response.clone())
        trim(cache)
      } catch (error) {
        // Storage full, for one: the map still gets the tile it asked for.
        console.error('Could not keep a map tile', error)
      }
    }
    return response
  } catch (error) {
    console.error('A map tile could not be fetched', error)
    return Response.error()
  } finally {
    clearTimeout(timer)
  }
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.hostname !== TILE_HOST) return
  event.respondWith(tile(event.request))
})
