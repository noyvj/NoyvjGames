// Bump SW_VERSION on any deploy that changes this file's own behaviour or
// the precache list; ordinary content deploys don't need it, because
// same-origin requests are network-first (see the fetch handler below) and
// so always pick up fresh files whenever the player is online.
const SW_VERSION = 61;
const CACHE_NAME = "site-cache-v" + SW_VERSION;
// How long a same-origin network request may take before we give up and
// serve the cached copy instead (a slow/flaky connection shouldn't hang).
const NETWORK_TIMEOUT_MS = 4000;
// The Pyodide runtime (about 14 MB decoded) and other versioned CDN files live in a cache of their
// own, NOT in site-cache-v<N>: a SW_VERSION bump deletes the old site cache, which used to throw the
// runtime away and make every deploy cost everyone a fresh 14 MB download. This name changes only if
// the policy below changes. (hub-offline.js's LIVE_CACHE_RE only matches site-cache-v<N>, so it never
// mistakes this for the live cache; its status check uses caches.match, which sees both.)
const RUNTIME_CACHE = "runtime-cdn-cache-v1";
// Only exact-versioned files from jsDelivr are treated as immutable: Pyodide's own directory and
// npm packages pinned to an exact x.y.z (Three.js). "@latest", "@1", query strings and every other
// cross-origin host (ads, fonts, analytics) stay on the old path or on the network.
const RUNTIME_URL_RE = /^https:\/\/cdn\.jsdelivr\.net\/(?:pyodide\/v\d+(?:\.\d+)+\/full\/[A-Za-z0-9._+-]+|npm\/[a-z0-9._-]+@\d+(?:\.\d+)+\/[A-Za-z0-9._\/-]+)$/;
// Bounds: at most this many files (two Pyodide versions plus Three.js fit comfortably), and no single
// file bigger than this, judged by its Content-Length header when it sends one (the largest real file,
// pyodide.asm.wasm, is about 10 MB). The oldest entries go first.
const RUNTIME_MAX_ENTRIES = 24;
const RUNTIME_MAX_ENTRY_BYTES = 24 * 1024 * 1024;
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
  "./sources.html",
  "./sources.js",
  "./sources.css",
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
  "./hub-nav.js",
  "./map.html",
  "./my-stats.html",
  "./steward.html",
  "./steward.js",
  "./today.json",
  "./offline-manifest.json",
  "./events.html",
  "./events.json",
  "shared/hub-auth.js",
  "shared/space-bg.css",
  "shared/ambient-bg.css",
  "shared/save-widget.js",
  // Z-13 translations of the shared components' words (English needs no file; es/fr load on demand).
  "shared/i18n.js",
  "shared/strings/en.json",
  "shared/strings/es.json",
  "shared/strings/fr.json",
  "shared/layout-pref.js",
  "shared/pc-shell.js",
  "shared/pc-shell.css",
  "shared/info_page.py",
  "shared/info-page.css",
  // Site-wide shared includes (Z-19/21/23/24/25/29/31): in every game page and the hub's.
  "shared/seasonal-events.js",
  "shared/seasonal-events.css",
  "shared/announcer.js",
  "shared/night-mode.js",
  "shared/night-mode.css",
  "shared/calm-mode.js",
  "shared/calm-mode.css",
  "shared/run-code.js",
  "shared/run_code.py",
  "shared/leaderboard.js",
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
  // AU-1: sound made in code (no audio files); games load it, the hub Settings page only writes its keys.
  "shared/sfx.js",
  "shared/sfx.css",
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
  "games/heist-committee/daily.py",
  "games/heist-committee/daily.js",
  "games/heist-committee/bots.py",
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
  "games/pocket-bazaar/market.py",
  "games/pocket-bazaar/marketbot.py",
  "games/pocket-bazaar/market.js",
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
  "games/dead-reckoning/daily.py",
  "games/dead-reckoning/fleet.py",
  "games/dead-reckoning/gentwo.py",
  "games/dead-reckoning/charts_two.py",
  "games/dead-reckoning/daily.js",
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
  "games/logic-gates/index.html",
  "games/logic-gates/style.css",
  "games/logic-gates/game.py",
  "games/logic-gates/app.js",
  "games/logic-gates/settings.js",
  "games/logic-gates/changelog.json",
  "games/logic-gates/achievements.json",
  "games/logic-gates/chips.py",
  "games/logic-gates/net.py",
  "games/logic-gates/sim.py",
  "games/logic-gates/levels_a.py",
  "games/logic-gates/levels_b.py",
  "games/logic-gates/levels_c.py",
  "games/logic-gates/levels.py",
  "games/logic-gates/check.py",
  "games/logic-gates/words.py",
  "games/logic-gates/render.py",
  "games/logic-gates/state.py",
  "games/logic-gates/achievements.py",
  "games/logic-gates/info.py",
  "games/robot-script/index.html",
  "games/robot-script/style.css",
  "games/robot-script/game.py",
  "games/robot-script/app.js",
  "games/robot-script/settings.js",
  "games/robot-script/changelog.json",
  "games/robot-script/achievements.json",
  "games/robot-script/dsl.py",
  "games/robot-script/room.py",
  "games/robot-script/run.py",
  "games/robot-script/editor.py",
  "games/robot-script/render.py",
  "games/robot-script/progress.py",
  "games/robot-script/info.py",
  "games/robot-script/hints.py",
  "games/robot-script/rooms_moving.py",
  "games/robot-script/rooms_turning.py",
  "games/robot-script/rooms_loops.py",
  "games/robot-script/rooms_routines.py",
  "games/robot-script/rooms_branches.py",
  "games/robot-script/rooms_capstone.py",
  "games/robot-script/rooms.py",
  "games/robot-script/companion.py",
  "games/robot-script/achievements.py",
  "games/robot-script/sandbox.py",
  "games/hull-repair/index.html",
  "games/hull-repair/style.css",
  "games/hull-repair/game.py",
  "games/hull-repair/app.js",
  "games/hull-repair/settings.js",
  "games/hull-repair/changelog.json",
  "games/hull-repair/achievements.json",
  "games/hull-repair/rules.py",
  "games/hull-repair/play.py",
  "games/hull-repair/boards_dock.py",
  "games/hull-repair/boards_crew.py",
  "games/hull-repair/boards_engineering.py",
  "games/hull-repair/boards_life.py",
  "games/hull-repair/boards_core.py",
  "games/hull-repair/boards.py",
  "games/hull-repair/progress.py",
  "games/hull-repair/render.py",
  "games/hull-repair/hints.py",
  "games/hull-repair/logbook.py",
  "games/hull-repair/achievements.py",
  "games/hull-repair/info.py",
  "games/station-medic/index.html",
  "games/station-medic/style.css",
  "games/station-medic/game.py",
  "games/station-medic/app.js",
  "games/station-medic/settings.js",
  "games/station-medic/changelog.json",
  "games/station-medic/achievements.json",
  "games/station-medic/lexicon.py",
  "games/station-medic/cast.py",
  "games/station-medic/shift.py",
  "games/station-medic/solver.py",
  "games/station-medic/casekit.py",
  "games/station-medic/cases_1.py",
  "games/station-medic/cases_2.py",
  "games/station-medic/cases_3.py",
  "games/station-medic/cases_4.py",
  "games/station-medic/cases_5.py",
  "games/station-medic/cases_6.py",
  "games/station-medic/cases_7.py",
  "games/station-medic/cases_8.py",
  "games/station-medic/cases.py",
  "games/station-medic/progress.py",
  "games/station-medic/codex.py",
  "games/station-medic/achievements.py",
  "games/station-medic/render.py",
  "games/station-medic/hints.py",
  "games/station-medic/info.py",
  "games/stranded/index.html",
  "games/stranded/style.css",
  "games/stranded/game.py",
  "games/stranded/app.js",
  "games/stranded/settings.js",
  "games/stranded/changelog.json",
  "games/stranded/achievements.json",
  "games/stranded/kit.py",
  "games/stranded/story_1.py",
  "games/stranded/story_2.py",
  "games/stranded/story_3.py",
  "games/stranded/story_4.py",
  "games/stranded/story.py",
  "games/stranded/walker.py",
  "games/stranded/explore.py",
  "games/stranded/lore.py",
  "games/stranded/info.py",
  "games/stranded/achievements.py",
  "games/stranded/render.py",
  "games/evidence-hunt/index.html",
  "games/evidence-hunt/style.css",
  "games/evidence-hunt/game.py",
  "games/evidence-hunt/app.js",
  "games/evidence-hunt/settings.js",
  "games/evidence-hunt/changelog.json",
  "games/evidence-hunt/achievements.json",
  "games/evidence-hunt/lexicon.py",
  "games/evidence-hunt/houses.py",
  "games/evidence-hunt/casework.py",
  "games/evidence-hunt/solver.py",
  "games/evidence-hunt/casekit.py",
  "games/evidence-hunt/cases_1.py",
  "games/evidence-hunt/cases_2.py",
  "games/evidence-hunt/cases_3.py",
  "games/evidence-hunt/cases_4.py",
  "games/evidence-hunt/cases_5.py",
  "games/evidence-hunt/cases.py",
  "games/evidence-hunt/progress.py",
  "games/evidence-hunt/gen.py",
  "games/evidence-hunt/codex.py",
  "games/evidence-hunt/achievements.py",
  "games/evidence-hunt/render.py",
  "games/evidence-hunt/hints.py",
  "games/evidence-hunt/info.py",
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
  "games/logic-gates/pc.html",
  "games/logic-gates/pc.css",
  "games/logic-gates/pc.js",
  "games/robot-script/pc.html",
  "games/robot-script/pc.css",
  "games/robot-script/pc.js",
  "games/hull-repair/pc.html",
  "games/hull-repair/pc.css",
  "games/hull-repair/pc.js",
  "games/station-medic/pc.html",
  "games/station-medic/pc.css",
  "games/station-medic/pc.js",
  "games/stranded/pc.html",
  "games/stranded/pc.css",
  "games/stranded/pc.js",
  "games/evidence-hunt/pc.html",
  "games/evidence-hunt/pc.css",
  "games/evidence-hunt/pc.js",
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
          Promise.all(keys.filter((key) => key !== CACHE_NAME && key !== RUNTIME_CACHE).map((key) => caches.delete(key)))
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
// Versioned jsDelivr files (Pyodide, Three.js) are cache-first in their own bounded cache (see
// runtimeResponse above). Any other cross-origin request (the ad script) stays cache-first with a
// background refresh.
function cacheable(response) {
  return response && (response.ok || response.type === "opaque");
}

function runtimeUrl(url) {
  // Look at origin + path only, so a query string or hash never matches ("?x=1" is not the file).
  return !url.search && RUNTIME_URL_RE.test(url.origin + url.pathname);
}

// Keep the runtime cache bounded: drop the oldest entries (the cache lists keys in insertion order).
function trimRuntimeCache(cache) {
  return cache.keys().then((requests) =>
    Promise.all(requests.slice(0, Math.max(0, requests.length - RUNTIME_MAX_ENTRIES)).map((r) => cache.delete(r)))
  );
}

// Cache-first for the versioned CDN files: a hit is served without touching the network (the URL
// carries the version, so the bytes can never change); a miss is fetched once, stored, and served.
// Offline with nothing stored fails like the browser would without a worker. Files that "Download
// for offline" put in the live site cache are found there too.
function runtimeResponse(event) {
  const request = event.request;
  return caches.open(RUNTIME_CACHE).then((cache) =>
    cache.match(request.url).then((hit) => {
      if (hit) return hit;
      return caches.open(CACHE_NAME).then((live) => live.match(request.url)).then((held) => {
        if (held) return held;
        // A script tag asks in no-cors mode and would get an opaque response (not storable at its
        // true size, and quota-padded). jsDelivr sends CORS headers, so ask for a readable one; the
        // browser accepts that for a no-cors request. If that fails, the plain request still gets its go.
        return fetch(request.url, { mode: "cors", credentials: "omit" })
          .catch(() => fetch(request))
          .then((response) => {
            const size = Number(response.headers.get("content-length"));
            if (response.ok && response.status === 200 && response.type !== "opaque" && !(size > RUNTIME_MAX_ENTRY_BYTES)) {
              event.waitUntil(
                cache.put(request.url, response.clone()).then(() => trimRuntimeCache(cache)).catch(() => null)
              );
            }
            return response;
          });
      });
    })
  );
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

  if (!sameOrigin && runtimeUrl(url)) {
    event.respondWith(runtimeResponse(event));
    return;
  }

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
