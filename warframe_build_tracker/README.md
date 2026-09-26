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

## Importing a real inventory snapshot

The "Import lastData.dat / inventory.json" button (near the top of the
page) auto-fills resource **built** counts from a real Warframe inventory
export, instead of typing every number by hand:

1. Run [`warframe-api-helper`](https://github.com/Sainan/warframe-api-helper)
   (or AlecaFrame) while Warframe is open and you're logged in. Either
   produces `lastData.dat`; the helper also writes a plain `inventory.json`
   sibling with the same content.
2. Upload either file. Everything happens in your browser — the file is
   never sent anywhere. `lastData.dat` is AES-128-CBC + PKCS7 encrypted
   with a key/IV that's hardcoded and published in `warframe-api-helper`'s
   own open-source code (not a secret), so it's decrypted client-side with
   the Web Crypto API; a plain `inventory.json` is used as-is.
3. Each of the 65 tracked resources is matched against the file's
   `MiscItems` list by the tail of its internal game path (e.g. anything
   ending in `.../Iradite` matches this tracker's "Iradite" row) — a
   fuzzy, best-effort match, not a hardcoded exact-path table, since this
   project has no verified real sample file to confirm the exact schema
   against. The summary shown after uploading names exactly what matched
   and what didn't, so any gap is visible and fillable by hand rather than
   silently wrong.
4. Only **built** counts are touched. Part-owned counts and the **raw**
   bucket are never touched by an import — neither has a real equivalent
   in Warframe's own data (a built component isn't tracked as a
   standalone countable item once it's part of an equipped Zaw/Kitgun/Amp,
   and "raw precursor" is this tracker's own bookkeeping convenience, not
   a single named inventory entry).

**Honest caveat:** this was built and verified against a synthetic file
encrypted with the real published key/IV, not a real Warframe export —
there was no real sample available to test against. If you try it with
your own file and something looks wrong (a resource you know you have
shows as unmatched, or a count looks off), that's useful signal — the
matching logic can be tightened once there's a real example to check it
against.

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

## Planning and browsing tools (2026-09-21 batch)

- **Overview block** at the top: the single resource currently blocking the
  most unfinished builds, per-category (Amp/Zaw/Kitgun) "X/Y parts complete"
  bars, and how many days ago the recipe data was last updated.
- **"Last updated" is `DATA_UPDATED` in `game.py`** -- an ISO date the
  maintainer bumps by hand whenever `MANUFACTURING_RECIPES`,
  `RESOURCE_LOCATIONS` or `DEFAULT_PARTS` change (there's no `data.json`
  file to stat any more). Bump it in the same commit as the data edit.
- **Search, sort and archive** above the part table: search by name; sort by
  fixed category order, **build priority** (fewest resources short for one
  craft first, finished parts last), name, or most-still-needed; and an
  "Archive completed parts" checkbox. Sort mode and the archive checkbox are
  saved; the search text is not.
- **Notes**: each part has a collapsible "note to self" (saved, max 500
  chars, stored/rendered as plain text only).
- **Shopping list** (section 3): a copyable plain-text list of what's still
  short (built/refined stock is what counts, same as the resource table).
- **Copy** button beside every resource name; each resource's "used in" line
  shows its still-needed total. Build and copy actions show a brief toast.
- **Grindy flag** on resources whose total requirement is at least
  `GRINDY_THRESHOLD` (500) in `game.py`. Wiki links you've clicked this
  session are struck through and dimmed.
- **Reset inventory** now goes through the hub's shared `ConfirmDialog`
  (falls back to the browser's `confirm()` if that script isn't loaded);
  notes and view preferences survive a reset.
- Saved state gained `notes` and `prefs`; old saves without them load fine.

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
the full open-items list — including the recursive-refinery-expansion idea
this tracker's `flatten_recipe()` already supports without needing any
code change, and refining the real-inventory-import matching logic above
once there's a real sample file to check it against.

## Updating the requested parts

Edit `DEFAULT_PARTS` (and `MANUFACTURING_RECIPES` for the new part's recipe)
in `game.py`, bump `DATA_UPDATED`, then just reload the page — no restart, no sync step.

## Phone layout

Below 640px the parts and resources tables stop scrolling sideways: each row reflows into a small card (name on top, Need/Have/Still need/Wiki/Build in a three-column grid) with the column header repeated as a label above every value. Pure CSS over the rows `game.py` already renders.
