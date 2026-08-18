const CACHE_NAME = "site-cache-v5";
const PRECACHE_URLS = [
  "/",
  "/manifest.json",
  "/ad-bar.css",
  "/style.css",
  "/script.js",
  "/games/sol/index.html",
  "/games/sol/style.css",
  "/games/sol/game.py",
  // Climate quartet + Info Page games (added when the precache list was
  // discovered to have never been extended past SOL) -- Trade Empire is
  // excluded since it isn't hub-linked yet, so no ordinary player traffic
  // reaches it.
  "/games/canopy/index.html",
  "/games/canopy/style.css",
  "/games/canopy/game.py",
  "/games/grid/index.html",
  "/games/grid/style.css",
  "/games/grid/game.py",
  "/games/tide/index.html",
  "/games/tide/style.css",
  "/games/tide/game.py",
  "/games/aftermath/index.html",
  "/games/aftermath/style.css",
  "/games/aftermath/game.py",
  "/games/herd/index.html",
  "/games/herd/style.css",
  "/games/herd/game.py",
  "/games/thaw/index.html",
  "/games/thaw/style.css",
  "/games/thaw/game.py",
  "/games/loop/index.html",
  "/games/loop/style.css",
  "/games/loop/game.py",
  "/games/drift/index.html",
  "/games/drift/style.css",
  "/games/drift/game.py",
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

// Stale-while-revalidate: serve the cached copy immediately when there is
// one (keeps the app fast and usable offline), but every request also
// kicks off a real network fetch in the background and overwrites the
// cache with whatever comes back. This load may still be stale, but the
// very next load already has it — no one needs to remember to bump
// CACHE_NAME by hand for a deploy to eventually reach returning players.
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(event.request).then((cached) => {
        const network = fetch(event.request)
          .then((response) => {
            cache.put(event.request, response.clone());
            return response;
          })
          .catch(() => cached); // offline with nothing cached: this just fails through
        return cached || network;
      })
    )
  );
});
