# Lazy loading report (TODO section LZ: LZ-1, LZ-2, LZ-3 groundwork)

Written 2026-10-11. This is a findings and handover document, not a live task list (the tasks stay in `TODO.md`).
Everything below was measured from the repository as it stood on 2026-10-11; other sessions were editing games at
the time, so single kilobytes will drift. Re-run `python3 scripts/measure-boot-cost.py` for current numbers.

## 1. What now exists

| File | What it is |
|---|---|
| `scripts/measure-boot-cost.py` | LZ-1. Static, read-only boot-cost measurement of every game (no browser, about half a second). `--json`, `--detail`, `--top N`, game names as arguments. |
| `scripts/tests/test_measure_boot_cost.py` | 12 tests (a made-up game tree plus the real repository). |
| `shared/lazy-packs.js` | LZ-2/LZ-3. The loader `window.NoyvjPacks`. |
| `shared/lazy-packs.css` | The loading card (tokens, dark/light, 44 px buttons, no animation). |
| `shared/lazy_packs.py` | The few lines Python needs (`await lazy_packs.require("id")`, `used()`, `import_pack`, `spawn`). Genuinely needed: a Python event handler cannot wait for a JavaScript promise by itself. |
| `shared/tests/test_lazy_packs_browser.py` | 44 tests (40 Playwright, 4 pure Python for the helper). |
| `planning/LAZY-LOAD-REPORT.md` | This file. |

Nothing outside these files was touched. No game, `sw.js`, the offline manifest or its generator, `PERF-BUDGET.md`
or hub file was edited; section 6 lists the edits the main session has to apply.

## 2. Measurement (LZ-1)

Command: `python3 scripts/measure-boot-cost.py` (add `--detail` for the per-game candidate list and the shape of
`game.py`; `--json` for machine-readable output). How it works: it reads each `games/<slug>/index.html` and the
game's own script files, finds every quoted `.py`/`.json`/`.js`/`.css` name that is a real file (game folder first,
then `shared/`), follows a content folder named as a path prefix (`"content/" + name`), and sums bytes, lines and an
estimated compressed size. It counts files that are *referenced*, so a file named only in code that runs later still
counts; the live transfer is `scripts/measure-perf.py`'s job. Whole-line comments are ignored. `zero-g-shift` has no
`index.html` yet and is skipped.

Columns: `total KB` is everything the page pulls in (raw), `wire KB` an estimate of the compressed transfer,
`game.py KB/lines`, `py mods` and `mods KB` the other Python modules the page writes into Pyodide, `json` the data
files fetched at boot, `shared KB` the `shared/` scripts, styles, Python and JSON the page includes, and
`candidates KB` the part of the boot that is a sensible lazy pack (Python modules and JSON files of 6 KB or more,
grouped by family, not counting `game.py`).

```
game             total KB  wire KB  html  game.py KB  game.py lines  py mods  mods KB  json  json KB  own js KB  shared KB  candidates KB
continuum            1689      531    84         258           6378       42      630     3       22        104        503            593
champ-de-mots        1630      407    89         413          10228        2      160     6      476         11        389            609
canopy               1223      370    91         471          10862        0      0.0     5       41         12        516            9.5
aftermath            1010      307    70         314           7326        0      0.0     3       22         30        494            0.0
tide                  969      297    75         333           7613        0      0.0     3       24         38        438            0.0
trade-empire          918      270   106         307           7284        0      0.0     4       36        6.8        403             14
grid                  913      281    69         299           6740        0      0.0     4       21        5.0        461            0.0
sol                   872      253    89         276           6392        0      0.0     3       16         15        418            0.0
drift                 843      256    62         293           6588        0      0.0     4       23         17        381            0.0
herd                  824      253    61         232           5371        0      0.0     4       25         29        414            0.0
loop                  816      249    61         251           5607        0      0.0     4       29         19        377            8.6
thaw                  793      242    65         267           6285        0      0.0     3       19        9.5        377            0.0
chronicle             716      207    22          96           2313        9       89    14       97         91        300            146
lighthouse            702      225    27         8.8            229       17      152     2      3.7         81        406            127
heist-committee       683      207    14          43           1026       10       98    11       93         74        339            166
dead-reckoning        643      208    19          40            887       23      165     2      1.9         55        339            139
evidence-hunt         558      179    18          31            646       18      105     2      1.1         43        338             83
logic-gates           544      176    15          23            650       13       89     2      1.4         36        363             67
station-medic         538      177    16          24            503       20      104     2      1.5         36        338             86
robot-script          534      172    17          27            567       18       81     2      2.9         46        338             63
pocket-bazaar         531      173    17          27            556       16       83     2      1.9         54        323             57
hull-repair           519      169    14          16            375       14       69     2      3.4         36        361             60
signal                500      158    19          56           1623        0      0.0     3      4.2         42        363            0.0
stranded              493      163    15          20            444       12       81     2      1.4         33        322             67
lexis                 476      155    20          17            399       18       57     2      2.0         48        320             17
rule-finder           392      124    15          17            365       13       48     2      1.3         38        251             37
```

### What the numbers say

1. **Our own files are a small part of a first visit.** `PERF-BUDGET.md` puts a game's total first-visit download at
   about 5.8 MB, of which Pyodide is about 5.4 MB. A game's own boot is 120 to 530 KB compressed (about 2% to 9%).
   The cost of the big games is mostly the time to compile and run a 250 to 470 KB `game.py`: first interactive minus
   Pyodide ready is 300 to 440 ms for Canopy, Champ de Mots and Continuum, 250 to 380 ms for Aftermath, Tide and
   Trade Empire, against about 10 ms for the modular newer games. Lazy packs buy back part of that 150 to 400 ms and a
   few tens of KB on the wire, not seconds. The honest case for the work is GN-17's one: bring in the game-mode
   gimmicks slowly, keep the first screen light, and stop the boot growing with every new mode.
2. **The service worker's install is the biggest single lump.** `sw.js` precaches 472 URLs, 10.5 MB raw (about
   3 MB compressed), 9.3 MB of it game files, at the first hub visit. Every module of the eight newer games is in that
   list (and `game.py` and the shell of every other game). Lazy packs only reduce that if the pack files are
   *removed from `PRECACHE_URLS`* (section 6); otherwise they are still all downloaded eagerly, just not parsed.
3. **`shared/` is 250 to 520 KB per page** (about 45 files). The biggest are `save-widget.js` 107 KB, `seed.js`
   29, `level-select.js` 29, `opening-screen.js` 28, `run-code.js` 27, `seasonal-events.js` 25, `sfx.js` 24,
   `skill-tree.js` 23, `report-problem.js` 22, `leaderboard.js` 21. Several are used only when the player opens a feature
   (run codes, skill tree, leaderboard, report form, sound) and would make `script` packs. That is a separate item
   (suggested as LZ-6 below), and it touches files other sessions own.
4. **The big single-file games cannot be cut as cleanly as the headline numbers suggest.** Canopy, Aftermath, Tide,
   Grid, Herd, Thaw, Loop, Drift, Trade Empire and SOL keep everything in one `game.py` of 230 to 470 KB. The mode code
   in them is 10 to 25% of the file (Canopy's expedition is 24 KB, wetland 13, contracts 13, challenge runs 10, seed
   vault 9.5 of 471 KB); the rest is the state class, rendering and loading, which every mode shares. A pack for
   such a game has to be a piece of `game.py` run into the same namespace (`"exec": true`), not an importable module.
5. **Continuum loads Three.js (603 KB, from jsDelivr) with a blocking `<script>` in the head**, plus `render3d.js`
   (56 KB), before the first screen, and imports all 42 of its modules at the top of `game.py`. That is the single
   largest avoidable boot cost on the site. Three.js is cross-origin, so the loader below (same origin only, on
   purpose) does not load it; see 3.1.
6. **The newer level-by-level games carry very little level data** (Robot Script's six chapters of rooms are 19 KB
   together, Hull Repair's boards 12 KB, Logic Gates' levels 32 KB, Station Medic's cases 27 KB). Splitting those saves
   10 to 40 KB each. The value there is the pattern (and the future: chapters will grow), not the bytes.

## 3. Recommended pack boundaries (heaviest first)

Sizes are raw bytes on disk. "Index stays in core" means: the screens that list levels, scenarios, achievements or
counts need a small always-loaded index (ids, titles, counts, unlock rules); the packs hold the bodies. Anything
that totals across all packs (number of endings, percent complete, achievement rules) must read that index, never the
pack.

### 3.1 Continuum (1689 KB; 42 modules, all imported at the top of `game.py`)
- **Step 0, biggest and simplest:** load Three.js and `render3d.js` (about 660 KB together) only when the 3D scene is first
  shown. Three.js is a CDN file, so inject a `<script src>` from the game itself (the service worker's runtime cache
  already makes it cache-first); `render3d.js` can be a `script` pack. The 2D fallback is already the default path
  when WebGL is missing, so the failure path exists.
- **Step 1, whole feature modules as `python` packs** (about 345 KB raw in 33 modules, none of which the first
  season needs): challenge runs (`challengerun`, `challenges`, `par`: 38 KB), settlement legacy (`dynasty`,
  `heritage`, `monuments`, `founding`, `archive`, `postmortem`, `rewind`, `timelapse`: 85 KB), other settlements
  (`neighbours`, `peers`, `geography`, `consulting`: 52 KB), people and orders (`advisors`, `citizens`, `hamlet`,
  `orders`: 61 KB), analysis panels (`trajectory`, `forecast`, `statlog`, `explain`, `techdebt`, `summary`,
  `dataexport`: 58 KB), late extras (`beyond`, `banners`, `naming`, `doctrines`, `minutes`, `eastereggs`,
  `sandbox`: 49 KB). Core stays: `sim`, `sustainability`, `research`, `save`, `log`, `transition`, `views`, `visual`,
  `info_content`. The work is replacing each top-level `import x` in `game.py` with an on-demand import at the entry
  point of the feature (`await lazy_packs.require("legacy")` then `lazy_packs.import_pack("dynasty")`).
- **Step 2, later, era content:** `info_content.py` (46 KB: `ERA_INFO_PAGE`, `REAL_WORLD_EXAMPLES`) and the later
  eras' tiers in `research.py` (54 KB, two tiers per era) and `sim.py` (73 KB) are keyed by era. Moving the digital,
  space and relay eras into `era-digital`, `era-space`, `era-relay` packs (roughly 3/8 of each file) is the "eras"
  conversion the TODO names. Needs the index rule above for the research tree (all 16 tiers are listed from turn 1).

### 3.2 Le Champ de Mots (1630 KB)
- `fren_combined_catalog.json` is **440 KB**: 23 weeks, FREN151 (11 weeks, about 30% of the bytes) and FREN152
  (12 weeks, about 70%). Keep a small index (week, chapter, topic ids and titles, sequence) in core and put the
  question bodies and `bonus_sentences` in `catalog-fren151` and `catalog-fren152` JSON packs (about 130 and 310 KB),
  loaded when the first plot of that semester is opened or watered. A new player never downloads FREN152.
- `minigames.py` is 140 KB and holds four arcade games that are already row-unlock-gated (Greetings and Basics Blitz,
  Verb Racer, Boutique Dash, Café Rush: about 9, 8, 11 and 14 KB of functions plus shared helpers). Split into a core
  helper module and four `python` packs loaded on the first open of each.
- In `game.py` (413 KB) the contiguous, self-contained sections are the placement test (23 KB), exam formats (16),
  exam planner (13), conversation simulator (10), listening (7), sentence builder (4), phrasebook (4.5), grammar
  deep-dive (14): 90 KB that can be `exec` packs. `supplementary_notes.json` (9.5 KB) follows the cultural notes toggle.

### 3.3 Canopy (1223 KB; `game.py` 471 KB, 10 862 lines; nothing else but JSON)
`exec` packs cut from `game.py` by the existing section markers: **Expedition** (24 KB, one contiguous block near the
end plus about 70 functions named `expedition_*`), **Wetland Forest** (13 KB) and **Highland Grove** (7 KB, contiguous
blocks), **Ranger contracts** (13 KB), **challenge runs** (10 KB), **Seed Vault** (9.5 KB), **Forest Almanac** (5 KB),
Poacher Patrol / Storm Front / Spirit's Walk (a few KB). About 85 KB in all (18% of `game.py`). These are exactly the
level-select modes, so it lines up with GN-17. The section markers in the file are chronological ("GB batch 1/2/3"),
not by feature, so the cut has to follow function names, not the banners. `story.json` (9.5 KB) is already fetched
separately and can be a `json` pack read when the story panel opens.

### 3.4 Aftermath (1010 KB), Tide (969 KB), Grid (913 KB), Herd, Thaw, Loop, Drift, SOL, Trade Empire
All single-file. Honest cut sizes (name-based search of `game.py`, so approximate):
- **Aftermath:** skill tree (52 KB across `skill_*`, `SkillTreeState`, the map and import/export; the `W-3` shared
  skill tree is already shared code, so this is mostly the game's own glue), Second Founding (15 KB), past-run review and
  "toughest run" (about 20 KB). About 90 KB.
- **Tide:** coastline (16 KB), daily (11), library (9), almanac (7), planner (6), fish (6): about 55 KB. The 72 KB
  `SettlementState` class is core.
- **Grid:** career mode (27 KB) and trend graphs (13 KB): about 40 KB. **Drift:** trend, ledger, neighbour
  panels (about 30 KB). **Herd, Thaw, Loop:** ghost runs, planner, past runs, trade view (about 20 to 30 KB each).
  **Trade Empire:** charters and blueprints (about 22 KB), expedition (8), plus `story.json` (14 KB) as a `json` pack.
  **SOL:** doctrines (13 KB), megaprojects (7), prestige (9). Each is under 10% of the game: do these last, and only
  if the level-select work (W-1/GN-17) makes the packs natural.

### 3.5 The newer games
| Game | Natural packs | KB | Note |
|---|---|---|---|
| Heist Committee | `content/complications.json` (42), `targets.json` (20), `writeups.json` (3); `daily.py` (8) for the Daily Job | about 75 | The other content tables and `engine.py` (46) are core. Check whether the planner needs `complications` before a target is chosen. |
| Chronicle | each set under `sets/<id>/` (68 KB for the sample) plus `setdata.py` (51 KB) | about 120 | A set is a content pack by nature, and more are planned: build the pattern in from the start. |
| Dead Reckoning | one `python` pack per chapter file `charts_open/wind/fixes/fog/tides/compass` (3 to 5 KB each), `charts_two.py` + `fleet.py` (17 KB, "Two ships"), `gen.py` + `gentwo.py` + `daily.py` (28 KB, practice and Daily Chart) | about 75 | `charts.py` (the registry, 4 KB) must list chapters without importing them. `pars.py` is generated and 6 KB: keep in core. |
| Lighthouse | `mysteries.py` + `unease.py` (25 KB, only when the Unease layer is on), `lore.py` (20), `story.py` (14, letters) | about 60 | Players who keep Quiet mode never download the Unease layer. |
| Stranded | `story_1..4` (9, 12, 15, 7 KB), one pack per story part; `lore.py` + `explore.py` (14) | about 57 | `story.py` builds scene tables for the whole graph at import (endings, edges, counts): it needs a small index of ids, titles and counts per part first. A chapter is only reachable after the previous one, so a quiet prefetch of the next part hides the load. |
| Evidence Hunt | `cases_1..5` (5 to 7 KB each), practice mode `gen.py` + `houses.py` (16) | about 45 | `cases.py` is the registry. |
| Station Medic | `cases_1..8` (3 to 4 KB each, one pack per two chapters), `codex.py` (6) | about 33 | |
| Logic Gates | `levels_a/b/c.py` (9, 6, 17 KB) | about 32 | Check how the three files map onto the five chapters; `levels.py` (4 KB) is the registry. |
| Robot Script | `rooms_*` six chapters, 2 to 3 KB each | about 19 | Too small to pay for a loading card chapter by chapter: group as "early" (core) and "later" (one pack). |
| Hull Repair | `boards_*` (5 decks, 1 to 3 KB each) | about 12 | Leave eager until the boards grow. |
| Pocket Bazaar | `regulars`, `decorations`, `festival` | about 11 | Leave eager. |
| Lexis | rung 2 and 3 (`compound*`, `bridge*`, `deduce_*`) | about 15 | Leave eager. |
| Rule Finder | `cases_*` (7 files, 18 KB) | about 18 | Another session is mid-build on this game; add `modules.json` when they finish. |

## 4. The loader (LZ-2)

### 4.1 How a game uses it

`games/<slug>/modules.json`:

```json
{ "version": 1, "game": "canopy", "packs": [
  { "id": "wetland", "label": "Wetland Forest", "kind": "python", "url": "packs/wetland.py", "bytes": 13000,
    "modes": "Wetland Forest level", "needs": ["highland"], "exec": true },
  { "id": "story", "label": "Story", "kind": "json", "url": "story.json", "bytes": 9700, "modes": ["Story panel"] } ] }
```
Fields: `id` (lower-case, digits, `-`, `_`), `label`, `kind` (`python` | `json` | `script` | `css`), `url` (relative to the
page, same origin only), `bytes` (approximate, for the card and the cap), optional `length` (exact decoded length, enforced),
`modes` (text or list: documentation of what needs it), `needs` (list of pack ids loaded first; a plain text note is
ignored), and for python `exec` (also run the source in Pyodide's main namespace, for a piece cut out of `game.py`) and
`path` (file name inside Pyodide's file system).

Page: `<link rel="stylesheet" href="../../shared/lazy-packs.css">` (optional: the script links it itself) and
`<script src="../../shared/lazy-packs.js" data-game-id="canopy" data-manifest="modules.json"></script>`, placed
before the game's own boot script. A `load()` that arrives before `modules.json` has been read waits for it.

JavaScript: `await NoyvjPacks.load("wetland")`, `await NoyvjPacks.requires(ids)`, `NoyvjPacks.has(id)`,
`missing(ids)`, `unknown(ids)`, `used()`, `info(id)`, `list()`, `downloaded()`, `downloadedAll()`, `clearRecord()`.
Python: `result = await lazy_packs.require("wetland")` returns `{ok, loaded, failed, message}` and never raises;
`lazy_packs.import_pack("wetland_mod")` after it; `lazy_packs.spawn(coro)` to start it from a normal DOM handler;
`lazy_packs.used()` for the save.

### 4.2 Saves that mention a pack that is not loaded (the rule)
The game stores `packs_used: NoyvjPacks.used()` (or `lazy_packs.used()`) in its own state. In the `load_state` flow:
`const r = await NoyvjPacks.requires(state.packs_used || [], {soft: true})` (or `lazy_packs.require(*ids)`) **before**
restoring. `soft` never rejects: it returns `{loaded, failed: [{id, code, message}]}`, so the game keeps the save,
restores what it can, tells the player in plain words what is missing (offline, unknown id from a newer or older game
version) and offers retry. The loader never deletes, rewrites or validates a save; an unknown id is reported as
`unknown`, never thrown at the save. Saving while a pack is not loaded must still write the old `packs_used` ids (the
game should merge, not replace, so a failed load does not drop a mode from the save).

### 4.3 Decisions (and why)
- **Same origin only.** The size cap and length check are only meaningful for files we host; a CDN pack (Three.js) is
  injected by the game as an ordinary script and cached by the worker's runtime cache.
- **`script` and `css` packs are fetched, checked and then inserted inline** (`<script data-noyvj-pack>` with the exact
  text that passed the checks, `//# sourceURL` appended), so there is one request, the cap and the length check cover
  them, and they work offline through the same path. The cost: no relative `url()` in pack CSS, no ES modules.
- **Python packs write the file and clear `importlib` caches** (a file created after start-up is invisible to
  `import` otherwise; verified live in Pyodide on the Lexis page: write, import, name resolved). `exec: true` also runs the
  source in `__main__`, for pieces cut from a monolithic `game.py`. `onLoaded(id, text, info)` (in `register` or per
  `load`) is awaited for anything custom; a throw there leaves the pack unloaded and retryable.
- **Return values:** `json` resolves with the parsed object (kept; loading again returns the same object), `python` with the
  source text, `script`/`css` with the inserted element.
- **Failure handling is part of the promise.** With the card on (default) a failed load keeps the promise pending, shows the
  plain message with "Try again" and "Not now", and focus lands on "Try again". "Try again" resumes the *same* promise, so a
  mode opens right after a successful retry; "Not now" rejects (the error carries `code`, `packId`, `dismissed: true`).
  `ui: false` loads silently and rejects at once (use it for prefetching the next chapter). Codes: `offline`, `network`,
  `http`, `too-big`, `length`, `empty`, `parse`, `no-runtime`, `import`, `bad-url`, `unknown`, `dependency`.
- **Integrity by length only:** `length` (exact decoded bytes) when the manifest has it; a decoded body that disagrees with an
  uncompressed `Content-Length`; an empty body; a body more than three times its listed `bytes` plus 32 KB; refusal above
  `maxBytes` (default 6 MB) judged from the listed size, the `Content-Length` header, and the running total while streaming.
- **Concurrency:** one session per pack; two callers (even with different `onProgress`) share one fetch, one card row and
  one promise; a loaded pack returns immediately; a failed one starts fresh next time. Dependency cycles are refused
  (`dependency`).
- **No timers, no animation, text only** (a test greps the source for `setTimeout`, `setInterval`,
  `requestAnimationFrame`, `innerHTML`, `eval`). The card is a `role="status"` `aria-live="polite"` box with the words
  "Loading Wetland Forest (about 13 KB)…", a `<progress>` bar and a percentage when the size is known, and the failure text
  in the same row; it is hidden when nothing is loading.
- **Offline:** see 5.

### 4.4 What is not built (left for the conversions)
- A game-facing "Packs" list in the opening screen or settings (the data is there: `NoyvjPacks.list()`, `downloaded()`).
- A test that every `modules.json` is valid (file exists, `bytes` within a factor of 3 of the real size); section 6 proposes it.
- Cross-origin packs (deliberately).
- `AbortSignal` cancellation of an in-flight download (the card offers none; a failure offers "Not now").

## 5. Service worker and offline (LZ-3, page side)

**Read of `sw.js` (version 61): the existing handler already treats a pack correctly; no handler change is needed.**
A pack is a same-origin GET without a `Range` or `Authorization` header, so the fetch handler's same-origin branch
applies: network first with `cache: "no-cache"` (bounded by a 4 s timeout), every `ok` response is written to
`site-cache-v61` with `cache.put`, and when the network fails or is slow the cached copy is returned. So a pack is cached
the first time it is used, and works offline afterwards. Also checked:
- The activate step carries the entries of the newest older `site-cache-v*` into the new cache, so used packs survive a
  `SW_VERSION` bump (and orphans of removed packs live on; harmless).
- Offline with no cached copy, the worker's `fetch` rejects; the loader reports `offline` when `navigator.onLine` is false,
  `network` otherwise.
- A pack larger than what the 4 s timeout allows still arrives: the race falls through to the same network promise when
  nothing is cached.
- The loader also looks in Cache Storage itself when `fetch` fails (a pack put there by "Download for offline" works even
  where the worker does not control the page yet), and, **only when no worker controls the page**, stores a fresh pack in
  the newest `site-cache-v*` (best effort, never creates a cache).
- A page-side record is kept in `localStorage["packs:<slug>"]` = `{ "<packId>": { "bytes": 12345, "at": "2026-10-11" } }`
  (written after a successful load, ids validated on read, blocked storage ignored). `NoyvjPacks.downloaded(slug)` and
  `downloadedAll()` read it. It is a note that the pack was fetched here, not proof that it is still cached (the hub's offline
  page already checks the cache itself).

## 6. What the main session has to apply

### 6.1 `sw.js`
1. Add the three loader files to the shared precache block (next to `"shared/pause-hidden.js"` etc.) so a game that uses
   them works offline on a first offline visit:
   ```
   "shared/lazy-packs.js",
   "shared/lazy-packs.css",
   "shared/lazy_packs.py",
   ```
   and bump `SW_VERSION` (61 to 62), as the file's own comment says to when the precache list changes. The handler code needs
   no edit.
2. **When a conversion moves code out of a precached file, edit the precache list in the same commit.** Remove the
   pack files from `PRECACHE_URLS` (otherwise the install still downloads them: the 10.5 MB figure above) and, if a file was
   *renamed or deleted*, remove its old line: `cache.addAll` fails the whole install if one URL 404s. For the eight newer games
   whose modules are listed one by one, the pack modules are the ones to drop (for example `games/stranded/story_1.py` ...
   `story_4.py`, `games/dead-reckoning/charts_*.py`). Do not add `modules.json` or the pack files; "Download for offline" and
   first use cache them.
3. Optional, not needed: `modules.json` of a game could be precached (1 to 3 KB) so the registry is there on a first offline
   visit; the first online visit caches it anyway.

### 6.2 `scripts/generate-offline-manifest.py`
Today `walk_game()` already lists every file under `games/<slug>/` (any depth, `.py`, `.json`, ...), so packs that live
inside the game folder, and the `modules.json` itself, are **already** part of the game's file list and of "Download for
offline". What is missing: packs whose `url` points outside the game folder (`../../shared/skill-tree.js`), a failure when a
listed pack file does not exist, and a marker so the hub can show "N optional packs". The patch (prototyped against a
throwaway tree: packs in the game folder and in `shared/` are found, each entry gets `"pack": "<id>"`, a missing file stops
the build with a clear message):

```python
def pack_files(slug: str):
    """LZ-3: every pack listed in games/<slug>/modules.json (shared/lazy-packs.js). Returns {file path: pack id}.
    A pack whose file is missing, or lies outside the repo, is a build error: 'Download for offline' must not
    silently skip content the game will ask for."""
    manifest = ROOT / "games" / slug / "modules.json"
    if not manifest.is_file():
        return {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    out = {}
    for pack in data.get("packs", []):
        target = (manifest.parent / pack["url"].split("?")[0].split("#")[0]).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            raise SystemExit(f"{slug}: pack {pack.get('id')} points outside the repository: {pack['url']}")
        if not target.is_file():
            raise SystemExit(f"{slug}: pack {pack.get('id')} points at a missing file: {pack['url']}")
        out[target] = pack["id"]
    return out
```
placed above `rel()`; in `build()`, right after `for extra in list(files): files |= shared_followups(extra)`:
```python
        packs = pack_files(slug)        # LZ-3
        files |= set(packs)
        pack_ids = {rel(p): pid for p, pid in packs.items()}
```
and after `entry = {"path": r, "bytes": ..., "precached": ...}`:
```python
            if r in pack_ids:
                entry["pack"] = pack_ids[r]
```
`--check` compares shapes after popping `bytes`, so the new `pack` key is compared (good: a changed `modules.json` makes
`--check` fail until the manifest is regenerated). Regenerate `offline-manifest.json` after the first conversion.

### 6.3 `hub-offline.js` (optional, small)
The hub page does not load the loader. To show "optional packs fetched" next to a game, read the record directly:
`JSON.parse(localStorage.getItem("packs:" + slug) || "{}")` (ids to `{bytes, at}`), and have "Remove" delete that key
(`localStorage.removeItem("packs:" + slug)`), since removing the cache entries makes the record stale.

### 6.4 Tests worth adding with the first conversion
- `modules.json` validity for every game that has one: each `url` exists, ids unique and valid, `kind` known, `bytes`
  within a factor of 3 of the real size (the same ratio the loader enforces), every `needs` id exists, no cycles, no pack file
  appears in `sw.js`'s `PRECACHE_URLS`.
- A per-game test that the game still boots with every pack missing (the core alone), and that opening each mode with
  the pack present works.
- `scripts/measure-boot-cost.py` already subtracts deferred packs: its `deferred KB` column should become non-zero for a
  converted game, which is a one-line check that the conversion really removed the file from the boot.

I did not run the full suite (the owner's computer was busy); run `python3 -m pytest -q shared/tests scripts/tests`
before committing. I ran only the new tests plus `shared/tests/test_site_includes.py` (169 passed) and
`shared/tests/test_hidden_attribute_rule.py` (1 passed).

## 7. Proposed order for LZ-4 and LZ-5

Ordered by (value) x (risk), with a pilot first because the first conversion will find the rough edges (index versus
body, saves, precache, the Python-side async call) cheaply on a small game.

0. **Pilot, a small modular game, in the LZ-5 style.** Dead Reckoning: a registry (`charts.py`) already exists, its
   chapters are an ordered sequence in a chooser, and the practice generator and Two ships are optional. Packs: one per
   chapter file (6), `two-ships` (`fleet.py`, `charts_two.py`), `practice` (`gen.py`, `gentwo.py`, `daily.py`). Proves
   `modules.json`, the card, `packs_used` in saves, the precache edit and the offline manifest edit end to end. Second small
   one: Stranded (4 story parts), which also proves the "index in core" rule.
1. **Continuum step 0** (Three.js and `render3d.js` on first 3D view): about 660 KB off the first screen for one change.
2. **Continuum step 1** (the 33 feature modules in six packs). Already separate files, so mostly moving `import` lines.
3. **Le Champ de Mots:** the catalogue split by semester (310 KB for FREN152), then the four arcade minigames, then the
   `game.py` sections (placement, exams, conversation, listening). The catalogue is the biggest data win in the site.
4. **Canopy:** Expedition, Wetland, Highland, contracts, challenge runs, Seed Vault as `exec` packs (the GN-17
   level-select modes), then `story.json`.
5. **Heist Committee, Lighthouse (Unease layer), Chronicle (sets), Stranded, Dead Reckoning remainder** (the rest of the
   LZ-5 list that has real content).
6. **Aftermath, Tide, Grid, Trade Empire, then Herd, Thaw, Loop, Drift, SOL:** only the optional modes listed in 3.4, and
   only where a level-select or mode menu makes the load a natural moment.
7. **Leave eager until their content grows:** Robot Script, Hull Repair, Pocket Bazaar, Lexis, Logic Gates (revisit when a
   sixth chapter lands).
8. **Suggested new item LZ-6 (for the user to confirm):** the optional shared components (`seed.js`, `run-code.js`,
   `leaderboard.js`, `report-problem.js`, `skill-tree.js`, `sfx.js`, `seasonal-events.js`: about 170 KB raw on every page)
   as `script` packs loaded on first use. Touches files other sessions own, so it needs its own claim.

And the new-game template (LZ-5's last clause): a `modules.json` with an empty `packs` array, the two includes, a
`require()` call in the level chooser, and the rule "a chapter's bodies are a pack once the chapter has more than about 10 KB
of data; the registry and the counts stay in core".

## 8. Open points for the main session
- **Where `game.py` pieces come from.** An `exec` pack is plain Python run in `__main__`: it can define functions and
  constants and register handlers, but a function in `game.py` that already calls the missing name by then must be guarded
  (`lazy_packs.has("wetland")`) or the call moved behind the require.
- **Async handlers in Python.** Events that open a mode must go through `lazy_packs.spawn(async_handler(event))`
  (Pyodide's loop). A synchronous handler that needs the pack immediately cannot wait; make the button's handler the
  async one.
- **`desktop (pc.html)` pages** are generated from `index.html`: include the loader once in `index.html` and regenerate;
  `shared/tests/test_pc_games.py` should keep passing as no ids are added.
- **Recording `packs_used`** needs a save-format addition per game; the save widget stores whatever `get_state` returns, so
  no widget change is needed, but each game's `CLAUDE.md` should note the field.
