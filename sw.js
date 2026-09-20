// Bump SW_VERSION on any deploy that changes this file's own behaviour or
// the precache list; ordinary content deploys don't need it, because
// same-origin requests are network-first (see the fetch handler below) and
// so always pick up fresh files whenever the player is online.
const SW_VERSION = 12;
const CACHE_NAME = "site-cache-v" + SW_VERSION;
// How long a same-origin network request may take before we give up and
// serve the cached copy instead (a slow/flaky connection shouldn't hang).
const NETWORK_TIMEOUT_MS = 4000;
// Every entry here is relative to sw.js's own location (this file, at the
// repo root), never a "/"-rooted absolute path -- GitHub Pages serves this
// repo under /NoyvjGames/, not the domain root, so an absolute path like
// "/manifest.json" resolves to the wrong origin-root URL and silently fails
// to cache. "./" stands in for the hub page itself (a bare "/" is always
// absolute, even in a relative-looking list, so it can't be used here).
const PRECACHE_URLS = [
  "./",
  "./manifest.json",
  "./ad-bar.css",
  "./style.css",
  "./script.js",
  "shared/hub-auth.js",
  "shared/space-bg.css",
  "shared/ambient-bg.css",
  "shared/save-widget.js",
  "shared/info_page.py",
  "shared/info-page.css",
  "games/sol/index.html",
  "games/sol/style.css",
  "games/sol/game.py",
  // Climate quartet + Info Page games (added when the precache list was
  // discovered to have never been extended past SOL) -- Trade Empire and
  // Continuum are excluded since neither is hub-linked yet, so no ordinary
  // player traffic reaches them.
  "games/canopy/index.html",
  "games/canopy/style.css",
  "games/canopy/game.py",
  "games/grid/index.html",
  "games/grid/style.css",
  "games/grid/game.py",
  "games/tide/index.html",
  "games/tide/style.css",
  "games/tide/game.py",
  "games/aftermath/index.html",
  "games/aftermath/style.css",
  "games/aftermath/game.py",
  "games/herd/index.html",
  "games/herd/style.css",
  "games/herd/game.py",
  "games/thaw/index.html",
  "games/thaw/style.css",
  "games/thaw/game.py",
  "games/loop/index.html",
  "games/loop/style.css",
  "games/loop/game.py",
  "games/drift/index.html",
  "games/drift/style.css",
  "games/drift/game.py",
  "games/champ-de-mots/index.html",
  "games/champ-de-mots/style.css",
  "games/champ-de-mots/game.py",
];

self.addEventListener("install", (event) => {
  // Take over from any previously-installed worker immediately, rather than
  // waiting for every open tab to close — otherwise a fixed CACHE_NAME bump
  // alone doesn't help a player who never fully closes their browser.
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

// Same-origin requests are NETWORK-FIRST: try the network (bounded by a
// timeout), refresh the cache with any good response, and fall back to the
// cached copy only when offline / slow / erroring. This is what fixes the
// old "reload twice after a deploy" trap -- the previous stale-while-
// revalidate strategy always served the *old* cached copy first, so a
// returning player saw the previous version until their next load.
// Cross-origin requests (Pyodide's CDN, ad script) stay cache-first with a
// background refresh: they're versioned/immutable-ish and slow to refetch.
function cacheable(response) {
  return response && (response.ok || response.type === "opaque");
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || request.headers.has("range")) return;
  const url = new URL(request.url);
  if (!/^https?:$/.test(url.protocol)) return;
  const sameOrigin = url.origin === self.location.origin;

  if (sameOrigin) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        const fromNetwork = fetch(request).then((response) => {
          if (cacheable(response)) cache.put(request, response.clone());
          return response;
        });
        const timeout = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("timeout")), NETWORK_TIMEOUT_MS)
        );
        return Promise.race([fromNetwork, timeout]).catch(() =>
          cache.match(request).then((cached) => cached || fromNetwork)
        );
      })
    );
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(request).then((cached) => {
        const network = fetch(request)
          .then((response) => {
            if (cacheable(response)) cache.put(request, response.clone());
            return response;
          })
          .catch(() => cached);
        return cached || network;
      })
    )
  );
});
