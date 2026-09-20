# Warframe Build Resource Tracker

Tracks progress toward the 33 zaw/kitgun/amp parts you're farming, and the
raw/refined resources each one still needs.

**Rearchitected 2026-09-20** from a Flask app (server-rendered, single
machine, `data.json` on disk) into a static Python-via-Pyodide page — the
same no-build-step stack every game on the NoyvjGames hub already uses.
This is committed to the hub's own `bcm206` repo now (previously
gitignored/local-only) and reuses the hub's existing account + save-code
system unmodified: `shared/hub-auth.js` + `shared/save-widget.js`, the same
two files every hub game drops in, pointed at `game_id="warframe-tracker"`.
No new backend code was needed — the FastAPI Cloud `/saves` endpoints are
already game-agnostic (a plain string id + a JSON blob).

It's deliberately **not linked from the hub's own nav** — same
committed-but-unlisted pattern as `admin.html` — since it isn't a game.

## Running it

Just open `index.html` through any static file server (the hub's own dev
server works fine — `python3 -m http.server` from the repo root, then
visit `/warframe_build_tracker/index.html`). No install step, no Python
environment to set up — Pyodide runs `game.py` entirely in the browser,
identical to every other page on the site.

## Saving your progress

- **Signed in:** sign in with the same account system the rest of the hub
  uses (top of the page), then use the Save/Load panel — your progress
  follows your account across devices/browsers.
- **Anonymous:** just use the Save/Load panel without signing in — you get
  a save code (e.g. `ADHA-H47B`) remembered in this browser, and can claim
  it to an account later from the same panel.
- Your real farming progress from the old Flask version's `data.json` was
  migrated into `game.py`'s `_MIGRATED_FROM_DATA_JSON` constant as the
  starting state for a fresh page load — nothing was lost in the
  rearchitect. That constant stops mattering the moment you save once (or
  sign in with an account that already has a save).

## What the tracker does

- Starts with the exact 33 parts and quantities you asked for, grouped into
  Amp / Zaw / Kitgun sections with a short note on what each build's
  Prism/Scaffold/Brace (Amp), Strike/Grip/Link (Zaw), or Chamber/Grip/Loader
  (Kitgun) slots actually control — not a "current meta" claim, since a
  balance patch can make that stale and this tracker has no way to verify it
  against the live game.
- Tracks how many of each component you already own.
- Highlights a component green with a "ready" badge the moment your current
  resource inventory covers everything its recipe needs, and a **Build**
  button lets you commit that: it subtracts the recipe's resources from your
  "have" counts (built stock first, then raw) and bumps the part's owned
  count by one, all in one click instead of doing the subtraction by hand.
- Tracks raw resources and refined/built resources separately.
- Shows which requested part(s) use each resource, and where that resource
  is actually found (planet/location, or — for a handful that are refined
  from a different raw material rather than picked up directly — which raw
  material to go look up instead), in a small expandable tab under the
  resource's name.
- Every part/resource has a direct link to its real WARFRAME Wiki page.

## Why recipe data is hand-curated, not fetched live

The original version of this tracker tried to fetch recipes live from the
WARFRAME Wiki's API. Two real, separate problems made that unreliable enough
to abandon rather than patch:

1. **The Wiki's bot protection blocks it.** Confirmed directly: even a
   single plain HTTP request from a script gets a `403` after a handful of
   requests in the same session — this isn't a rate-limit tweak away, it's
   the kind of protection meant to stop exactly this kind of automated
   fetching. Working around it isn't something this project does.
2. **The page structure the old scraper looked for doesn't exist.** It
   searched for a `<h2>/<h3>/<h4>` heading containing "Manufacturing
   Requirements" followed by a table. The real Wiki page has no such
   heading — "Manufacturing Requirements" is a row *inside* the same
   infobox table, so the old scraper would have found nothing even if the
   network calls had worked.

So instead, `game.py`'s `MANUFACTURING_RECIPES` dict holds all 33 parts'
requirements, read by hand off each part's real Wiki page (using a real
browser, which the Wiki's bot protection doesn't block). Since recipes are
static reference data (never saved/loaded as part of player state), any
hand-edit to `MANUFACTURING_RECIPES` takes effect the instant the page is
next loaded — no separate "reload/sync" step exists anymore, unlike the old
Flask version.

**A few parts aren't documented under their obvious page name** — Zaw
Strikes/Grips/Links and Kitgun Chambers are Wiki'd under just the
component's proper noun ("Balla", not "Balla Strike"). `WIKI_PAGE_OVERRIDES`
in `game.py` maps each of those to the real page so the "Wiki ↗" links work;
the tracker's own display names are unaffected.

The `RESOURCE_LOCATIONS` dict (where each of the 65 resources is actually
found) was researched the same hand way, off each resource's own Wiki page.
A handful of resources aren't found in the field at all — they're refined
from a different raw material (e.g. Tear Azurite is cut from a raw Azurite
gem at a Bin). For those, the entry names the raw material rather than
asserting a specific planet for it, since that raw material's own Wiki page
is the honest place to look up where *it* drops.

## Important note about raw vs refined resources

The tracker intentionally does NOT assume that a raw ore/gem is automatically
the same thing as its refined product. A refined item you own counts directly
toward the refined requirement. Raw ore is recorded separately so you can see
what you have available to refine.

## What's next

See the hub's `planning/TODO2.md`, "X. Warframe Build Tracker" section, for
the full open-items list — including the planned `lastData.dat` import
(auto-filling inventory from a real game-session snapshot, via the
open-source `warframe-api-helper`/AlecaFrame tools, parsed entirely
client-side) and the recursive-refinery-expansion idea this tracker's
`flatten_recipe()` already supports without needing any code change.

## Updating the requested parts

Edit `DEFAULT_PARTS` (and `MANUFACTURING_RECIPES` for the new part's recipe)
in `game.py`, then just reload the page — no restart, no sync step.
