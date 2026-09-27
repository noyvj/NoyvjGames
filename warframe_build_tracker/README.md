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

## Refinery breakdown

Nineteen tracked resources are refined in the Foundry from a raw material (the alloys, Devar/Goblite/Amarast-style gems, Nyth, Thyst and so on). `REFINERY_RECIPES` in `game.py` holds each one's Foundry recipe (output per craft, credits, ingredients), read from that resource's Manufacturing Requirements on the Warframe Wiki on 2026-09-26. For every refined resource you are still short on, its row gets a "refine" line: the number of whole crafts, and what to gather for them. The raw precursor you already hold in the **Raw have** column is subtracted from the primary material to gather. The "What I still need" section adds one combined line for everything. It is copied data: if a number ever looks off, check the in-game Foundry and edit it, then bump `DATA_UPDATED`.

## Route planner and rare flags

- **Farming route planner:** under "What I still need", one line names the single place that would cover the most resources you are still short on (with the runners-up). Places are read from each resource's location text (`ROUTE_PLACES`, `location_places()`); resources refined from another material name no place and are left out.
- **Rare flag:** a small "rare" tag on resources that are hard to come by for this list. There is no price or drop-rate data, so `resource_rarity()` judges from the location text: found in five or more places is common, a single place or a gated source (heist, bounty, fish part, a specific enemy) is rare. It is a prioritising hint, not a market value.

## Farming log

Under "What I still need", a collapsible **Farming log** records every time a resource's total on hand goes up, either because you typed a bigger number or because an import found more (`log_gain()`). Decreases are not logged: spending on a build or fixing a typo is not farming. It shows what you gained today and overall (top five) and the latest entries, keeps the newest 300, saves with your progress (`farm_log`, validated on load) and can be cleared with one button. Times are UTC.

## Syndicate standing layer

None of the 65 tracked resources are Void Relic gated, but every refined resource needs a reusable Foundry blueprint bought with Syndicate standing (Ostron's Old Man Suumbaat, Solaris United's Smokefinger, the Entrati's Otak). `SYNDICATE_SOURCES` records the vendor, faction, standing cost and rank for each of the 19, read from each Wiki page on 2026-09-26 (Auroxium Alloy's page shows both 7,500 and 7,000; the higher one is used). Each refined resource row shows its blueprint source with an "owned" tick (ticked automatically if you already hold some of the resource; your own tick or untick wins), and "What I still need" totals the standing you still have to earn per faction for blueprints you do not own yet.

## Part notes and the build comparison

- **Part notes:** every requested part now shows a one-line description under its name (`PART_NOTES`), read from the Warframe Wiki's Amp, Zaw and Kitgun pages on 2026-09-26: the Wiki's own stat figures for amps and zaw parts, and its relative wording for kitgun parts (no invented numbers).
- **What built parts become:** `KNOWN_COMBOS` holds named builds. The Wiki names exactly one, the "177" Amp (Raplak Prism, Propa Scaffold, Certus Brace); its Zaw and Kitgun pages name no popular combination, so none is invented. **My combos** (name plus comma-separated parts) adds your own, saved with your progress.
- **Build comparison:** the collapsible "Build comparison" ranks every combo by how close it is: parts already built, which are still to build, and how many resource units those are short for one craft each. Finished combos sort last.

## Market prices

Nine tracked resources (the refined gems: Tear Azurite, Star Amarast, Star Crimzian, Marquise Thyst/Veridos, Esher Devar, Goblite Tears, Heart Nyth, Radiant Zodian) are tradeable on Warframe.market; the alloys, plain resources and the zaw/kitgun/amp parts are not. Warframe.market's API sends no CORS headers, so the page cannot call it directly: the site's backend does (`app/market.py`, `GET /market/prices`, a fixed whitelist of slugs, cached ten minutes, spaced requests, any failure just means no price). Each tradeable resource row shows its lowest online sell price, and "What I still need" totals the platinum to buy everything you are short on. If the backend is unreachable the page simply shows no prices.


## Batch A planner features (2026-09-27)

Sixteen small, UI-additive features. None of them changes the need calculations: the resource "still need" figures, the Build button and the refinery plan are computed exactly as before. Every new saved key is written by `get_state()` only when it is not at its default, and `load_state()` validates it (types, bounds, unknown ids dropped), so old saves load unchanged. Real-world figures below were read from the Warframe Wiki on 2026-09-27 and are named where they appear.

- **This week (pins):** star up to three builds (a star under each part's note, or type a part or combo name) and they stay at the top of the page with their status. Saved as `pins`.
- **Foundry timers** (tab): a craft name plus start time and duration (`12h`, `1d 2h`, `90m`), or a ready-at time; shows the ready-at time in local time. An optional notification is requested only when you press "Enable notifications", fires only while the page is open, and does nothing if the browser has no Notification API. Saved as `timers`.
- **Credits and endo budget:** two number boxes beside the refinery plan. The plan's credit total is compared with the credits you enter and the line says whether it is credit-limited, farm-limited, both or neither. Endo is a figure you type; no tracked recipe uses it and no live data is read. Saved as `budget`.
- **Mastery checklist** (tab): your own list of weapons and frames with a tick for "fully ranked", plus the mastery points you already have. Figures from the Wiki's Mastery Rank page (https://wiki.warframe.com/w/Mastery_Rank): weapons give 100 points per rank up to 30 (3,000), Warframes, companions and archwings 200 per rank (6,000), and the total points for rank N is 2,500 x N squared (page table: MR1 2,500, MR2 10,000, MR10 250,000). That page does not list every item, so the list is add-your-own; the readout gives points to the next rank, the equivalent in weapons or frames, and how many of your listed items would do it. Legendary ranks are not modelled. Saved as `mastery`.
- **Recently completed:** the last five builds (parts, or combos whose parts are all built) that became finished, with the UTC date. Recorded when a Build click or an owned-count edit finishes a build. Saved as `completed`.
- **Trader** (tab): a manual watch list, and a "Baro is due back in N days" line counted from a date you enter. The Wiki's Baro Ki'Teer page (https://wiki.warframe.com/w/Baro_Ki'Teer) says he appears every two weeks and trades for up to 48 hours, so the cycle is 14 days and the day after an arrival still reads as "may still be here". Saved as `trader`.
- **Wishlist text:** a copyable two-line summary ("Building: ..." and "Need: ...") for clan chat: parts still to build (pinned first) and resources still short. Long-term goals are never included. Not a saved key.
- **I have enough:** a tick on each resource row. A ticked resource stops counting as a need in the shopping list, wishlist, refinery, route, market, syndicate and budget lines and in the part rows' "short" notes. The table figures themselves are untouched. Saved as `enough`.
- **Colour tags:** presets `daily driver`, `fun`, `sell` plus up to eight of your own short labels, assigned per part (row picker) or per part/combo (tab), with a Tag filter beside the search box. The label name is always shown next to its colour. Saved as `tag_labels` and `tags`. The filter itself is not saved.
- **Long-term goals** (tab): a free-text list kept apart from builds and the shopping list. Saved as `goals`.
- **Keyboard shortcuts:** `/` focus search, `h` toggle Archive completed parts, `s` open the shopping list, `?` show or hide the cheat sheet, `Esc` close it (also a "? Shortcuts" button). Ignored while typing in a field and when Ctrl, Cmd or Alt is held, so browser and save-widget shortcuts are unaffected.
- **My edits and markers:** a count of your own edits ("added 3 builds, edited 12 resource counts") in the "My edits" tab, and a small `typed` or `import` marker beside each resource's built count so you can tell hand-typed counts from imported ones. Saved as `edit_log` and `inv_source`.
- **Daily / weekly checklist** (tab): your own tasks with ticks that clear on their own. Reset times from the Wiki (https://wiki.warframe.com/w/Daily_Reset): daily at 0:00 UTC, weekly every Monday at 0:00 UTC. Each period's tick list is saved with a stamp (today's date, or the Monday's date) and cleared when the stamp is out of date, including for a save loaded days later. A once-a-minute check re-renders only when a reset or a timer becoming ready makes the page stale. Saved as `checklist`.
- **Progress history** (tab): the completion percentage is snapshotted on every import and on demand (last 60 kept), drawn as a small inline SVG line chart with a text summary. Saved as `history`.
- **Share goals** (tab): a code `WFG1.` plus URL-safe base64 of a compact JSON (`{"v":1,"b":[[part,qty]],"n":[[resource,qty]]}`) holding only unfinished parts and short resources: no notes, names or accounts. Pasting a friend's code is validated strictly (prefix, characters, length, exact keys, version, known names, positive integer quantities, no duplicates, size limits) and shows what you could cover from spare stock and which shortfalls you share. An imported code is never saved. Not a saved key.
- **Loadout notes** (tab): your own mod list and playstyle notes (600 characters each, plain text) on a finished build. Saved as `loadouts`.


## Batch B planner features (2026-09-27)

Ten more UI-additive features, all in the new "5. Deeper planners" tab strip (plus one line under each resource). Like batch A, none changes a need calculation: the resource "still need" figures, the Build button and the refinery plan are computed exactly as before. Every new saved key is written by `get_state()` only when it is not at its default and is fully validated by `load_state()` (types, bounds, unknown names dropped), so old saves load unchanged. Real-world figures were read from live pages with WebFetch on 2026-09-27; where a figure could not be verified it was left out and the gap says so.

**Code layout.** The logic lives in small Python modules instead of `game.py`: `wf_util.py` (validation helpers), `wf_relics.py`, `wf_crafting.py` (crafting tracker and pet log), `wf_forma.py`, `wf_plans.py` (meta planner and farm session), `wf_insight.py` (import diff, waste audit, readiness), `wf_tips.py`, `wf_store.py` (defaults, export, load and prune for the six new state keys) and `wf_ui.py` (rendering and events, one `Planner` class handed a `ctx` object by `game.py`, so it never imports `game.py`). `index.html` fetches every `wf_*.py` and writes it into Pyodide's file system before `game.py` runs (the same pattern as `games/continuum`'s `ENGINE_MODULES`); a test checks the list in `index.html` matches the files on disk. The six new saved keys are `relics`, `crafts`, `pets`, `forma`, `imports` and `readiness`.

- **Meta build planner** (tab "Meta build"): pick any named build, the built-in `KNOWN_COMBOS` or one of your own combos, and see the whole chain: parts already built, parts still to farm, the resources those parts still need against your built stock, the refinery crafts and credits for the refined ones, and one completion bar. Only one community build is named by a source the tracker can point at (the "177" Amp on the Wiki's Amp page), so that is the only built-in one; the Zaw and Kitgun pages name none and none is invented. The bar counts each part as an equal share: a built part is worth all of it, a part still to build half of it scaled by how much of its resources you hold (the other half is the Build click). Not saved.
- **Drop-source optimizer** (tab "Farm session"): builds on `route_suggestions()`. It picks up to three places greedily, each adding the most still-short resources not yet covered, and prints "N% of your short resources drop at these places", plus the share of units, plus the resources with no named place (refined ones, farmed at their raw material). Coverage says where things drop, not how many runs are needed. Where a resource has a stored Wiki tip (below) it is shown under the stop. Resources ticked "I have enough" are left out. Not saved.
- **Void relic planner** (tab "Void relics", state `relics`): a manual planner for prime parts. This tracker's own builds (Zaw, Kitgun and Amp parts) are not relic drops, so it does not plan for them. You add a prime part you want; it lists the relics that carry it (with rarity), which are unvaulted, how many of each relic you own (typed), and an order: relics carrying the most wanted parts first, then ones you own, then by summed chance, each with the refinement level that maximises the chance of a wanted part (pure arithmetic on the Wiki's table: commons are best left Intact, an Uncommon or Rare part is best at Radiant). Data read from the Warframe Wiki on 2026-09-27: the unvaulted list on https://wiki.warframe.com/w/Void_Relic (Lith 8, Meso 9, Neo 8, Axi 9; 757 vaulted at that page's latest update, Hotfix 44.0.1 dated 2026-09-24) and each of those 34 relics' own page (e.g. https://wiki.warframe.com/w/Lith_A13), every one reporting "AVAILABLE". The page's drop-chance table is used for the refinement advice (Intact 0 traces 25.33/11/2%, Exceptional 25 traces 23.33/13/4%, Flawless 50 traces 20/17/6%, Radiant 100 traces 16.67/20/10% for a common/uncommon/rare reward). NOT embedded: the 757 vaulted relics (too many, and not farmable), the five Baro Ki'Teer exclusive relics (Neo O1, Axi A2, Axi A5, Axi M5, Axi V8) and the Requiem relic, which carries no prime parts; add any of them, or a newly unvaulted relic, with "Add relic". The source URL and read date are shown on screen. The data goes stale as soon as DE vaults or unvaults a relic, so check the Wiki before spending Void Traces.
- **Crafting tracker** (tab "Crafting", state `crafts`): a manual list of weapons, warframes and companions with their components. A component named like one of the tracker's 65 resources reads its count from your live inventory (built plus raw); any other keeps a count you type. Each item shows a completion bar and "ready to craft" when every component is on hand. **Imported ownership:** the import now also reads the owned-equipment arrays (`Suits`, `LongGuns`, `Pistols`, `Melee`, `Sentinels`, `SentinelWeapons`, `KubrowPets`, `MoaPets`, `OperatorAmps`), whose names come from the open-source SpaceNinjaServer type definitions (https://github.com/SpaceNinjaServer/SpaceNinjaServer, `src/types/inventoryTypes/inventoryTypes.ts`, read 2026-09-27), and marks a crafting item owned when the last part of an `ItemType` path, lower-cased with punctuation removed, equals the item's name the same way ("Excalibur Prime" against `.../ExcaliburPrime`). That is a community server that mirrors the response's shape, not DE's own documentation, and there is still no real export to test against, so it is best-effort: weapon paths often do not end in the Wiki name, so those stay unmatched and you tick them by hand. Your own tick or untick wins over the import mark, and the import summary says how many items it saw and which crafts it marked. Blueprints (`Recipes`) are not treated as owned items.
- **Forma planner** (tab "Forma", state `forma`): for a part, combo or crafting item, type its current slot polarities and the wanted ones (madurai, vazarin, naramon, zenurik, unairu, penjaga, umbra, any, or `-` for an empty slot; the names are from https://wiki.warframe.com/w/Polarity). Each slot that differs needs one Forma; the tab lists them in order, keeps a running total across every active plan against the Forma you hold, and reminds you that a Forma resets the item to Unranked and needs it at max rank (https://wiki.warframe.com/w/Forma, read 2026-09-27). Three Overframe links per plan, all plain external links, never scraped. Verified with WebFetch on 2026-09-27 as real pages: the build lists `/builds/warframes/`, `/builds/primary-weapons/`, `/builds/secondary-weapons/`, `/builds/melee-weapons/`, `/builds/sentinels/` and the item lists `/items/warframe/`, `/items/melee/`, `/items/primary/`, `/items/secondary/`, `/items/pet/`, `/items/all/`. Overframe's item pages need a numeric id (`/items/arsenal/<id>/<name>/`) that cannot be guessed, so the last link per plan is Overframe's search page (`/search/?q=<name>`); that page showed "No Results" to a non-browser fetch, so it may only fill in when opened in a browser, and the page says so. Amps get only two links because no verified Amp list page was found. Forma held and Forma used are typed by you; Forma used feeds the readiness score. The tab also counts how many of the embedded unvaulted relics list a Forma Blueprint.
- **Pet log** (tab "Pets", state `pets`): a manual log of kubrow and kavat with the imprints you have made, your mods and a note. Nothing is assumed from the import (`KubrowPets` is named in the type definitions above, but no real file proves what is in it). A "+1 imprint" button and an "Imprint timer (1.5 h)" button that adds a Foundry timer. Reference facts read from https://wiki.warframe.com/w/Kubrow and https://wiki.warframe.com/w/Kavat on 2026-09-27 and shown with their links: incubation takes 48 hours (24 with an Incubator Upgrade Segment); only 2 imprints can be made per Kubrow and one takes 1.5 hours; a Genetic Code Template raises the chance of imprinted traits but does not guarantee them; a Kavat attempt needs 10 Kavat Genetic Codes and an Incubator Power Core. The Kavat page names no imprint limit, so the log enforces the 2-imprint cap for kubrow only.
- **Farming tips** (tab "Farming tips", plus one line under the resource in the resource table): for the 25 most-needed resources (ranked by how many of the 33 tracked parts use them, ties by total units needed) the resource's own Wiki page was fetched on 2026-09-27 and asked for the sentence that states a drop chance, a quantity or a best place; the stored text is that page sentence, with its section, source link and read date. 16 have a sentence; for the 8 refined ones the page names no drop rate or best node, and Coprite Alloy's drop table was read twice with conflicting chances, so no figure is stored for it. The four riskiest figures (Gyromag Systems, Breath Of The Eidolon, Condroc Wing, Seram Beetle Shell) were re-read with a second fetch and agreed. The other 40 tracked resources have no tip yet: nothing was invented for them.
- **Since last import** (tab, state `imports`): each import stores the built count of every matched resource; the tab compares the last two: new items, counts that ticked forward, counts that went down (spent), crafting items the import newly marked owned. Only the last two snapshots are kept.
- **Waste audit** (tab "Waste audit"): three heuristics, none a verdict. Overstocked: you hold at least twice what unfinished parts still need with at least 10 spare (built plus raw), plus tracked resources you hold 10 or more of that no unfinished part needs. Refinable: a refined resource you are short on while you hold its raw precursor (only the primary raw material is checked, not the recipe's other ingredients). Blueprint idle: a refined resource whose blueprint reads as owned (a ticked box, or holding some of the resource) but that no unfinished part needs any more; "never needed" is read as "from here on", and the line says when no part on your list uses it at all. All 19 refined resources are used by some listed part, so that last note appears only if the list changes.
- **Readiness score** (tab "Readiness", state `readiness`): a playful number out of 100, not a game figure. 40 points for owned parts (owned over target), 20 for Forma you say you have used (full marks at an arbitrary 20) and 40 for the mod ranks you type here (sum of ranks over sum of max ranks), with the breakdown always shown and a light title from the score.

**Known limits.** The relic and tip data are snapshots from 2026-09-27. The Overframe search link is unverified beyond the page existing. Item ownership from an import is a best-effort name match against a structure documented by a community server, not a real export.
