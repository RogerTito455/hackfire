// Keeps the OpenStreetMap tiles the dashboard has shown, so the demo map survives a flaky venue
// network (#13): open the dashboard once on good Wi-Fi, pan over the demo area, and those tiles
// are served from this cache from then on. Only tile requests are touched; the API, the app and
// everything else go straight to the network.

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
      const response = await fetch(event.request)
      if (response.ok) {
        await cache.put(event.request, response.clone())
        trim(cache)
      }
      return response
    }),
  )
})
