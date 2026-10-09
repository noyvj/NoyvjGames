// Bump SW_VERSION on any deploy that changes this file's own behaviour or
// the precache list; ordinary content deploys don't need it, because
// same-origin requests are network-first (see the fetch handler below) and
// so always pick up fresh files whenever the player is online.
const SW_VERSION = 46;
const CACHE_NAME = "site-cache-v" + SW_VERSION;
// How long a same-origin network request may take before we give up and
// serve the cached copy instead (a slow/flaky connection shouldn't hang).
const NETWORK_TIMEOUT_MS = 4000;
// The FastAPI Cloud backend (same host script.js's RATINGS_API_BASE uses).
const API_ORIGIN = "https://noyvjgames.fastapicloud.dev";
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
  "./settings.html",
  "./settings.js",
  "./help.html",
  "./help.js",
  "./help-data.json",
  "./credits.html",
  "./hub-status.js",
  "./hub-shortcuts.js",
  "./hub-prefs.js",
  "./hub-games.js",
  "./game-sessions.json",
  "./terms-meta.json",
  "./whats-new-data.js",
  "./profile.js",
  "./profile.html",
  "./hub-today.js",
  "./hub-foryou.js",
  "./hub-collections.js",
  "./hub-offline.js",
  "./hub-shell.js",
  "./today.json",
  "./offline-manifest.json",
  "./events.html",
  "./events.json",
  "shared/hub-auth.js",
  "shared/space-bg.css",
  "shared/ambient-bg.css",
  "shared/save-widget.js",
  "shared/layout-pref.js",
  "shared/pc-shell.js",
  "shared/pc-shell.css",
  "shared/info_page.py",
  "shared/info-page.css",
  // Site-wide shared includes (Z-19/21/23/24/25/29/31): in every game page and the hub's.
  "shared/seasonal-events.js",
  "shared/seasonal-dates.json",
  "shared/profile.js",
  "shared/report-problem.js",
  "shared/seed.js",
  "shared/seed.py",
  "shared/copy-result.js",
  "shared/achievement-share.js",
  "shared/time-controls.js",
  "shared/time-controls.css",
  "shared/pause-hidden.js",
  "shared/lite-mode.js",
  "shared/lite-mode.css",
  "shared/a11y.css",
  "shared/touch-targets.css",
  "shared/error-boundary.js",
  "shared/perf-mark.js",
  "shared/debug-overlay.js",
  "shared/info-footer.js",
  "games/sol/index.html",
  "games/sol/style.css",
  "games/sol/game.py",
  // Climate quartet + Info Page games (added when the precache list was
  // discovered to have never been extended past SOL).
  "games/canopy/index.html",
  "games/canopy/style.css",
  "games/canopy/game.py",
  "shared/level-select.js",
  "shared/skill-tree.js",
  "shared/skill-tree.css",
  "shared/skill_tree.py",
  "games/canopy/levels.json",
  "games/grid/index.html",
  "games/grid/style.css",
  "games/grid/game.py",
  "games/tide/index.html",
  "games/tide/style.css",
  "games/tide/game.py",
  "games/tide/ui.js",
  "games/aftermath/index.html",
  "games/aftermath/style.css",
  "games/aftermath/game.py",
  "games/aftermath/ui.js",
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
  "games/drift/ui.js",
  "games/champ-de-mots/index.html",
  "games/champ-de-mots/style.css",
  "games/champ-de-mots/game.py",
  "games/signal/index.html",
  "games/signal/style.css",
  "games/signal/game.py",
  "games/signal/app.js",
  "games/lexis/index.html",
  "games/lexis/style.css",
  "games/lexis/game.py",
  "games/lexis/app.js",
  "games/lexis/settings.js",
  "games/lexis/changelog.json",
  "games/lexis/achievements.json",
  "games/lexis/lang.py",
  "games/lexis/pulse.py",
  "games/lexis/parse.py",
  "games/lexis/world.py",
  "games/lexis/scenes.py",
  "games/lexis/deduce.py",
  "games/lexis/notebook.py",
  "games/lexis/compound.py",
  "games/lexis/compound_scenes.py",
  "games/lexis/deduce_compound.py",
  "games/lexis/glyphs.py",
  "games/lexis/achievements.py",
  "games/lexis/bridge.py",
  "games/lexis/bridge_scenes.py",
  "games/lexis/deduce_bridge.py",
  "games/lexis/story.py",
  "games/lexis/report.py",
  "games/lexis/info.py",
  "games/heist-committee/index.html",
  "games/heist-committee/style.css",
  "games/heist-committee/game.py",
  "games/heist-committee/app.js",
  "games/heist-committee/plan.js",
  "games/heist-committee/play.js",
  "games/heist-committee/settings.js",
  "games/heist-committee/changelog.json",
  "games/heist-committee/achievements.json",
  "games/heist-committee/content/tags.json",
  "games/heist-committee/content/actions.json",
  "games/heist-committee/content/traits.json",
  "games/heist-committee/content/crew.json",
  "games/heist-committee/content/gear.json",
  "games/heist-committee/content/complications.json",
  "games/heist-committee/content/targets.json",
  "games/heist-committee/content/lines.json",
  "games/heist-committee/content/writeups.json",
  "games/heist-committee/content.py",
  "games/heist-committee/engine.py",
  "games/heist-committee/plancheck.py",
  "games/heist-committee/planops.py",
  "games/heist-committee/writeup.py",
  "games/heist-committee/info.py",
  "games/heist-committee/achievements.py",
  "games/heist-committee/story.py",
  "games/lighthouse/index.html",
  "games/lighthouse/style.css",
  "games/lighthouse/game.py",
  "games/lighthouse/app.js",
  "games/lighthouse/settings.js",
  "games/lighthouse/changelog.json",
  "games/lighthouse/achievements.json",
  "games/lighthouse/rng.py",
  "games/lighthouse/data.py",
  "games/lighthouse/clock.py",
  "games/lighthouse/weather.py",
  "games/lighthouse/ships.py",
  "games/lighthouse/state.py",
  "games/lighthouse/sim.py",
  "games/lighthouse/day.py",
  "games/lighthouse/achievements.py",
  "games/lighthouse/goals.py",
  "games/lighthouse/lore.py",
  "games/lighthouse/cast.py",
  "games/lighthouse/story.py",
  "games/lighthouse/mysteries.py",
  "games/lighthouse/unease.py",
  "games/lighthouse/info.py",
  "games/lighthouse/view.py",
  "games/pocket-bazaar/index.html",
  "games/pocket-bazaar/style.css",
  "games/pocket-bazaar/game.py",
  "games/pocket-bazaar/app.js",
  "games/pocket-bazaar/settings.js",
  "games/pocket-bazaar/changelog.json",
  "games/pocket-bazaar/achievements.json",
  "games/pocket-bazaar/goods.py",
  "games/pocket-bazaar/rng.py",
  "games/pocket-bazaar/board.py",
  "games/pocket-bazaar/orders.py",
  "games/pocket-bazaar/days.py",
  "games/pocket-bazaar/festival.py",
  "games/pocket-bazaar/renown.py",
  "games/pocket-bazaar/shop.py",
  "games/pocket-bazaar/pledge.py",
  "games/pocket-bazaar/info.py",
  "games/pocket-bazaar/achievements.py",
  "games/pocket-bazaar/decorations.py",
  "games/pocket-bazaar/regulars.py",
  "games/pocket-bazaar/day.py",
  "games/dead-reckoning/index.html",
  "games/dead-reckoning/style.css",
  "games/dead-reckoning/game.py",
  "games/dead-reckoning/app.js",
  "games/dead-reckoning/settings.js",
  "games/dead-reckoning/changelog.json",
  "games/dead-reckoning/achievements.json",
  "games/dead-reckoning/geom.py",
  "games/dead-reckoning/sim.py",
  "games/dead-reckoning/chartkit.py",
  "games/dead-reckoning/charts_open.py",
  "games/dead-reckoning/charts_wind.py",
  "games/dead-reckoning/charts_fixes.py",
  "games/dead-reckoning/charts_fog.py",
  "games/dead-reckoning/charts_tides.py",
  "games/dead-reckoning/charts_compass.py",
  "games/dead-reckoning/gen.py",
  "games/dead-reckoning/info.py",
  "games/dead-reckoning/pars.py",
  "games/dead-reckoning/charts.py",
  "games/dead-reckoning/render.py",
  "games/dead-reckoning/solver.py",
  "games/dead-reckoning/state.py",
  "games/dead-reckoning/progress.py",
  "games/dead-reckoning/achievements.py",
  "games/dead-reckoning/fixes.py",
  // Audit fix 2026-09-27: Trade Empire is hub-linked and has been for a while
  // (see CLAUDE.md's Current games table) -- both were mistakenly left off
  // this list under a stale "not hub-linked yet" comment. Trade Empire has the
  // same single-engine-file shape as every game above; Continuum only gets its
  // shell precached, not its 18 separately-loaded engine modules, so this list
  // doesn't need constant upkeep as that game grows.
  "games/trade-empire/index.html",
  "games/trade-empire/style.css",
  "games/trade-empire/game.py",
  "games/continuum/index.html",
  "games/continuum/style.css",
  "games/continuum/pc.html",
  "games/continuum/pc.css",
  "games/continuum/pc.js",
  "games/canopy/pc.html",
  "games/canopy/pc.css",
  "games/canopy/pc.js",
  "games/tide/pc.html",
  "games/tide/pc.css",
  "games/tide/pc.js",
  "games/grid/pc.html",
  "games/grid/pc.css",
  "games/grid/pc.js",
  "games/herd/pc.html",
  "games/herd/pc.css",
  "games/herd/pc.js",
  "games/thaw/pc.html",
  "games/thaw/pc.css",
  "games/thaw/pc.js",
  "games/aftermath/pc.html",
  "games/aftermath/pc.css",
  "games/aftermath/pc.js",
  "games/drift/pc.html",
  "games/drift/pc.css",
  "games/drift/pc.js",
  "games/loop/pc.html",
  "games/loop/pc.css",
  "games/loop/pc.js",
  "games/sol/pc.html",
  "games/sol/pc.css",
  "games/sol/pc.js",
  "games/lexis/pc.html",
  "games/lexis/pc.css",
  "games/lexis/pc.js",
  "games/heist-committee/pc.html",
  "games/heist-committee/pc.css",
  "games/heist-committee/pc.js",
  "games/lighthouse/pc.html",
  "games/lighthouse/pc.css",
  "games/lighthouse/pc.js",
  "games/pocket-bazaar/pc.html",
  "games/pocket-bazaar/pc.css",
  "games/pocket-bazaar/pc.js",
  "games/dead-reckoning/pc.html",
  "games/dead-reckoning/pc.css",
  "games/dead-reckoning/pc.js",
  "games/signal/pc.html",
  "games/signal/pc.css",
  "games/signal/pc.js",
  "games/trade-empire/pc.html",
  "games/trade-empire/pc.css",
  "games/trade-empire/pc.js",
  "games/champ-de-mots/pc.html",
  "games/champ-de-mots/pc.css",
  "games/champ-de-mots/pc.js",
];

self.addEventListener("install", (event) => {
  // Take over from any previously-installed worker immediately, rather than
  // waiting for every open tab to close — otherwise a fixed CACHE_NAME bump
  // alone doesn't help a player who never fully closes their browser.
  self.skipWaiting();
  event.waitUntil(
    // cache: "reload" skips the browser's own HTTP cache, so a deploy can never precache a
    // copy GitHub Pages' max-age=600 would otherwise have kept for up to ten minutes.
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(PRECACHE_URLS.map((url) => new Request(url, { cache: "reload" })))
    )
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => {
        // A version bump creates a new cache, which used to throw away everything the player had
        // chosen to "Download for offline" (those files sit in the live site-cache-v<N>). Carry the
        // newest older cache's entries over first, skipping anything the new install already holds,
        // so downloaded games survive an update.
        const older = keys
          .filter((key) => key !== CACHE_NAME && /^site-cache-v\d+$/.test(key))
          .sort((a, b) => Number(b.slice(12)) - Number(a.slice(12)));
        const carry = older.length
          ? Promise.all([caches.open(older[0]), caches.open(CACHE_NAME)]).then(([from, into]) =>
              from.keys().then((requests) =>
                Promise.all(requests.map((request) =>
                  into.match(request).then((have) =>
                    have ? null : from.match(request).then((response) => response && into.put(request, response))
                  )
                ))
              )
            ).catch(() => null)
          : Promise.resolve();
        return carry.then(() =>
          Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Same-origin requests are NETWORK-FIRST (and bypass the browser's own HTTP cache, see the
// fetch below): try the network (bounded by a
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

  // Backend API calls (saves, achievements, ratings, stats, accounts) are
  // live per-user data, never "versioned/immutable-ish" like a CDN script.
  // The cache-first strategy below used to serve the PREVIOUS response for
  // these and only refresh it in the background, so a player who saved or
  // earned something and then went back to the hub saw the old numbers
  // until a manual reload (and, worse, an account's authenticated response
  // sat in the browser cache). Leave them entirely to the network.
  if (url.origin === API_ORIGIN || request.headers.has("authorization")) return;

  if (sameOrigin) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        // cache: "no-cache" = always revalidate with the server (a cheap 304 when nothing
        // changed). Without it the browser's HTTP cache answered first: GitHub Pages sends
        // max-age=600, so a fresh deploy could stay invisible for ten minutes even though this
        // worker is "network-first" (and a local dev server's heuristic caching did the same).
        const fromNetwork = fetch(request, { cache: "no-cache" }).then((response) => {
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
