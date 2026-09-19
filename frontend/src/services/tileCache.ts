// Registers the service worker that caches map tiles for a flaky venue network (#13).
// See public/tile-cache-sw.js. Browsers without service workers just use the network.

export function registerTileCache(): void {
  if (!('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/tile-cache-sw.js').catch(() => {
      // The map still works from the network; the cache is only a safety net.
    })
  })
}
