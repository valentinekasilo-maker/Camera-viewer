/**
 * ANDRO-Vision Service Worker
 *
 * Enables PWA install prompt in Chrome/Edge and provides a basic
 * app-shell caching strategy:
 *   - Cache-first for static assets (JS, CSS, images, fonts)
 *   - Network-first for API calls and WebSocket upgrades
 *   - Falls back to cached index.html for navigation requests (SPA routing)
 *
 * This worker does NOT cache sensitive data or camera streams.
 */

const CACHE_NAME = "andro-vision-shell-v1";

// Static assets to pre-cache on install
const PRECACHE_URLS = [
  "/",
  "/index.html",
  "/images/android-chrome-192x192.png",
  "/images/android-chrome-512x512.png",
  "/images/maskable-icon.png",
];

// Patterns that should NEVER be cached
const NEVER_CACHE = [
  /^\/api\//,         // backend API
  /^\/ws$/,           // WebSocket endpoint
  /^\/live\//,        // camera streams
  /^\/vod\//,         // video on demand
  /^\/clips\//,       // clip files
  /^\/exports\//,     // export files
  /^\/notifications-worker\.js$/,  // push notification worker
];

function shouldSkipCache(url) {
  const { pathname } = new URL(url);
  return NEVER_CACHE.some((pattern) => pattern.test(pathname));
}

// ---------------------------------------------------------------------------
// Install — pre-cache the app shell
// ---------------------------------------------------------------------------
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

// ---------------------------------------------------------------------------
// Activate — clean up old caches
// ---------------------------------------------------------------------------
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// ---------------------------------------------------------------------------
// Fetch — cache-first for assets, network-first for API/navigation
// ---------------------------------------------------------------------------
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only handle GET requests
  if (request.method !== "GET") return;

  // Never cache these patterns — pass straight through
  if (shouldSkipCache(request.url)) return;

  const url = new URL(request.url);

  // Navigation requests (HTML pages) — network-first with SPA fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .catch(() =>
          caches
            .match("/index.html")
            .then((cached) => cached || fetch("/index.html")),
        ),
    );
    return;
  }

  // Static assets — cache-first strategy
  if (
    url.pathname.startsWith("/images/") ||
    url.pathname.startsWith("/fonts/") ||
    url.pathname.startsWith("/locales/") ||
    url.pathname.match(/\.(js|css|woff2?|ttf|otf|svg|png|ico|webp|jpg)$/)
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            caches
              .open(CACHE_NAME)
              .then((cache) => cache.put(request, responseClone));
          }
          return response;
        });
      }),
    );
    return;
  }

  // Everything else — network only (no caching)
});
