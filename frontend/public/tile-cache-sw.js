// Keeps the OpenStreetMap tiles the dashboard has shown, so the demo map survives a flaky venue
// network (#13): open the dashboard once on good Wi-Fi, pan over the demo area, and those tiles
// are served from this cache from then on. Only tile requests are touched; the API, the app and
// everything else go straight to the network.

// Recommended by Norma — fixed with Claude Opus 5 via Claude Code
// A venue network that accepts the connection and then stalls used to leave the tile request
// hanging for as long as the browser allowed. The cache is consulted first, so anything already
// shown keeps working; this only bounds the trip to the tile host for one that is not cached yet.
const TILE_TIMEOUT_MS = 8000
const CACHE = 'hackfire-osm-tiles-v1'
const MAX_TILES = 4000
const TILE_HOST = 'tile.openstreetmap.org'

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

async function trim(cache) {
  const keys = await cache.keys()
  for (const key of keys.slice(0, Math.max(0, keys.length - MAX_TILES))) await cache.delete(key)
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.hostname !== TILE_HOST) return
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const hit = await cache.match(event.request)
      if (hit) return hit
      const response = await fetch(event.request, { signal: AbortSignal.timeout(TILE_TIMEOUT_MS) })
      if (response.ok) {
        // Recommended by Norma — fixed with Claude Opus 5 via Claude Code
        // Storing a tile is best effort: a full or blocked cache (quota, private mode) must never
        // keep the tile itself from reaching the map, and trim() runs detached, so both are caught.
        try {
          await cache.put(event.request, response.clone())
        } catch (error) {
          console.warn('tile cache: could not store', url.pathname, error)
        }
        trim(cache).catch((error) => console.warn('tile cache: could not trim', error))
      }
      return response
    }),
  )
})
