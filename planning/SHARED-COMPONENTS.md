# Shared components (W-1 level select, W-3 skill tree, W-4 seasonal events, W-5 leaderboards)

Three drop-in components for the games, built once (section 4, the general leaderboards, adds a backend and is described on its own). None of the first three stores anything the game did not hand it (apart from two small per-viewer conveniences named below), none needs a backend, and all of them are tested in headless Chromium and in Python (`python3 -m pytest -q shared/tests`).

Common rules, true for all three:

- **Text is written with `textContent` only.** Titles, blurbs and flavour from a data file can never inject markup.
- **State is never colour alone.** Every state has a glyph, a word and a border style.
- **Theme.** Colours are tokens that follow `html[data-theme="light"]` (the site's switch in `shared/theme.js`) and, when no theme attribute is set, the OS preference.
- **Reduced motion.** Transitions only run when neither `prefers-reduced-motion: reduce` nor `html[data-reduced-motion="true"]` (the attribute the games' `settings.js` sets) is on.
- **Keyboard and screen reader.** Described per component below. Tap targets are at least 44 px high.
- **Desktop boot.** These are plain scripts with no layout assumptions, so `pc.html` includes them the same way `index.html` does (the generic test `shared/tests/test_pc_games.py` still needs any element id the game's own code uses to exist in both pages).

Files: `shared/level-select.js`; `shared/skill-tree.js`, `shared/skill-tree.css`, `shared/skill_tree.py`; `shared/seasonal-events.js`, `shared/seasonal-events.css`, `shared/seasonal_events.py` (existing, two functions added), `shared/seasonal-dates.json` (unchanged). Not yet in `sw.js`'s precache list: add the ones a game uses.

---

## 1. Level select (`shared/level-select.js`, TODO W-1)

A modal "choose a level" screen where **levels are data**. Every fifth level (5, 10, 15 ...) is by convention a game mode or a new mechanic (Canopy's poachers and storm fronts, GB-13, GB-15, GB-16). The first version of this file already existed with a smaller API; every call it had still works unchanged.

### Data shape (a `levels.json` next to the game, or an array passed in)

```json
{ "title": "Canopy levels",
  "levels": [
    { "id": "wren_hollow", "title": "Wren Hollow", "kind": "level", "blurb": "The standard forest." },
    { "id": "fern_glade",  "title": "Fern Glade",  "blurb": "A damper start.", "requires": ["wren_hollow"],
      "better": "lower", "unit": "seasons" },
    { "id": "birch_flats", "title": "Birch Flats", "requires_count": 2 },
    { "id": "poachers",    "title": "Poacher Patrol", "kind": "mode", "blurb": "Whack-a-mole poachers.",
      "requires": ["birch_flats"], "unlock_text": "Finish Birch Flats first" }
  ] }
```

| field | meaning |
|---|---|
| `id`, `title` | required, ids unique |
| `kind` | `"level"` (default), `"mode"` or `"mechanic"`; `"mode": true` is shorthand for kind mode |
| `blurb` | one line of description |
| `requires` | ids that must all be completed first |
| `requires_count` | alternatively N other levels completed (both rules may be used together) |
| `unlock_text` | overrides the generated "Complete X first" wording |
| `better`, `unit` | which result is best (`"higher"` default, `"lower"`) and the unit shown after a numeric best |

State (the only thing that persists), owned by the game: `{ "done": ["wren_hollow"], "best": { "wren_hollow": { "value": 12, "text": "12 seasons" } } }`. A bare list of ids (the first version's localStorage format) is still read.

### Adopting it

Simplest, exactly as before:

```html
<button id="levels-open-button" type="button">Levels</button>
<script src="../../shared/level-select.js" data-game-id="canopy" data-levels="levels.json" data-open="#levels-open-button"></script>
```

then, from the game (for a Python game, through `js` or a proxy in Pyodide):

```js
NoyvjLevels.configure({
  state: savedLevelState,                       // from get_state()/load_state()
  onChange: (state) => game.saveLevelState(state), // after this the component stores NOTHING itself
  onStart: (id, level) => startLevel(id),          // (window.NoyvjLevelStart(id) is still called too)
  canPlay: (level) => level.id !== "poachers" || vault.has("poacher_pass") || "Needs the Poacher Pass",
});
// when the player finishes a level:
NoyvjLevels.complete("fern_glade", { value: 14, text: "14 seasons" }); // or a number, or a string
```

Without `onChange` the done ids fall back to `localStorage["levels:<game>"]`, as the first version did. A second, independent screen (no script tag needed): `NoyvjLevels.create({ levels, title, state, onChange, onStart, canPlay, trigger: "#open" })`.

API (`NoyvjLevels`): `open() close() refresh() complete(id, result?) isDone(id) done() best(id) getState() setState(state) configure({state,onChange,onStart,canPlay}) start(id) ready() levels() create(options)`; pure helpers in `NoyvjLevels.logic` (`lockReason, isUnlocked, recordResult, sanitizeState, progress, nextUp, audit`). `complete` returns false when nothing changed; a worse result never replaces a best (text-only results never replace a numeric one). `logic.audit(levels)` warns when a fifth entry is a plain level or a `requires` id does not exist: run it once in the game's tests.

### Accessibility

- A modal `role="dialog"` with `aria-modal`, labelled by its heading. Focus moves to the next level to play when it opens, Tab and Shift+Tab stay inside, Escape closes, and focus returns to the opener.
- The levels are an ordered list with **one tab stop** (roving focus): arrows move by card and by row (rows of five on a wide screen, so Up/Down hop five), Home/End go to the start or end of the row, Shift+Home/End to the first or last level. Enter or Space plays.
- A locked level stays focusable (`aria-disabled`) so a screen reader hears "Locked: Complete Birch Flats first"; activating it announces that in a polite live region instead of doing nothing silently.
- Cues beyond colour: glyph + word (`✓ Completed`, `▶ Ready`, `⊘ Locked: reason`), border style (thick solid done, thin solid ready, dashed locked), and a `★ Game mode` / `✦ New mechanic` tag with a double border for every fifth level.

---

## 2. Skill tree (`shared/skill-tree.js` + `.css`, Python mirror `shared/skill_tree.py`, TODO W-3)

For meta-progression: Canopy's Seed Vault (GB-10), ranger crews (GB-26), later Trade Empire's charter tree (O-1, which already has this exact shape in `CHARTER_PERKS`). **State is only a list of owned node ids plus `earned`**, the total points ever given; the balance is `earned - spent`, so it cannot drift. Everything is deterministic, with no randomness, and nothing mutates its arguments.

### Data shape

```json
{ "id": "seed_vault", "title": "Seed Vault", "currency": "seed points",
  "branches": [ { "id": "growth", "title": "Growth", "blurb": "Plots mature faster." } ],
  "nodes": [
    { "id": "quick_start", "branch": "growth", "cost": 1, "label": "Quick Start",
      "description": "Plots begin one season older.", "effect": "plot_head_start" },
    { "id": "deep_roots", "branch": "growth", "cost": 2, "label": "Deep Roots",
      "description": "Soil recovers 20% faster.", "requires": ["quick_start"] }
  ] }
```

`requires` means **all** of the listed nodes (Trade Empire's `standing_convoy` needs two). `tier` is optional (default: 1 + the deepest prerequisite). `effect` is the id a game switches on (default: the node id). `branches` is optional (derived from the nodes' `branch`); a node with no branch lands in "Perks". `description` is the effect text shown on the card. Costs are integers >= 1. `validate(tree)` returns a list of problems (duplicate ids, bad costs, unknown or self prerequisites, cycles): call it in the game's tests.

### Rules (same names in JS camelCase and Python snake_case, pinned together by `test_skill_tree_browser.py`)

| function | returns |
|---|---|
| `status(tree, owned, id, earned)` | `"owned"`, `"available"`, `"unaffordable"` (prerequisites met, not enough points) or `"locked"` |
| `can_buy / canBuy`, `buy(tree, owned, id, earned)` | `buy` gives `{ok, owned (new list), spent, points_left, reason}`; reasons `locked`, `points`, `owned`, `unknown` |
| `can_refund`, `refund(tree, owned, id)` | a node can be refunded alone only if no other owned node needs it; reasons `needed`, `not-owned`, `unknown` |
| `refund_all(tree, owned)` | `{ok, owned: [], refunded: <whole spend>}` |
| `totals(tree, owned, earned)` | owned/node counts, spent, total and remaining cost, points left, `complete`, per-branch counts |
| `effects(tree, owned)`, `has_effect` | effect ids of the owned nodes, in tree order |
| `sanitize_owned(tree, owned, earned, overspend)` | clean a loaded save: known string ids only, no duplicates, nodes whose prerequisites are missing dropped; if it costs more than `earned`, `"clear"` (default, what Trade Empire does) returns `[]`, `"trim"` drops the latest nodes until it fits |
| `spent`, `points_left`, `tier_of`, `missing_requirements`, `validate` | as named |

`earned=None` / `null` means unlimited points (sandbox, tests). Persist `owned` (a list of strings) and `earned` however the game already saves; run `sanitize_owned` on load.

### Renderer

```html
<link rel="stylesheet" href="../../shared/skill-tree.css"> <!-- optional: the script links it itself if missing -->
<script src="../../shared/skill-tree.js"></script>
```

```js
const view = NoyvjSkillTree.render(document.getElementById("vault"), {
  tree, owned, earned,
  refundNodes: false,                 // true adds a Refund button per owned node (R key)
  onBuy: (id, node) => { /* game confirms (ConfirmDialog), buys with NoyvjSkillTree.buy(), saves, applies effects */ view.update({ owned: newOwned }); },
  onRefund: (id) => { ... }, onRefundAll: () => { ... },   // game confirms, then update()
});
view.update({ owned, earned });   // cheap, in place: focus and scroll are kept, so call it every render if you like
```

The renderer never changes state itself. It also offers `view.focus(id)`, `view.announce(text)`, `view.destroy()`. After an `update` that adds or removes exactly one node it announces "Bought X. 3 seed points left." in a live region (`announceChanges: false` to skip).

Accessibility: one `role="group"` labelled by the title and described by the key help; each branch is a heading plus an ordered list, labelled by its heading, with a count "(1/3)". Roving focus, **one tab stop**: Up/Down within a branch, Left/Right between branches, Home/End within a branch, Ctrl+Home/End first and last. Each perk button is described by its effect text, its prerequisites and its state. A perk that cannot be bought stays focusable (`aria-disabled`); pressing it announces why ("Locked: needs Waystation and Standing Orders" / "Not enough points: 1 more seed point needed"). Cues: glyph (`✓` owned in a filled circle, `◆` available, `◇` not enough points, `▪` locked), border (thick solid, solid, dashed, dotted), a state sentence, `Tier N · Cost C points`, and `Needs: A, B (owned)`.

---

## 3. Seasonal events (`shared/seasonal-events.js` + `.css`, TODO W-4)

The browser front end of `shared/seasonal_events.py` (date rules in `planning/SEASONAL-EVENTS.md`): which event is on today, flavour a game overrides, a dismissible banner, and a badge grant. **No new backend.** The JavaScript date rules were checked against the Python engine on every day from 2025 to 2032 (`test_seasonal_events_browser.py`), so a Pyodide game and a JS caller always agree.

### Adopting it (a few lines)

```html
<script src="../../shared/seasonal-events.js"></script>
```

```js
const events = NoyvjSeasonal.init({
  game: "aftermath",
  events: {                                   // the event ids THIS game hosts, with its own flavour
    halloween: { title: "Night of Storms", text: "The storms are loud tonight.",
                 task: "Survive one run with resources left", goal: 1, unit: "run" },
  },
  progress: (eventId) => stormRunsSurvived,   // number, or { count, goal }; omit to show no progress line
  // qualifies: (eventId) => true,            // or decide completion yourself
  onGrant: (badge, allBadges) => { state.event_badges = allBadges; },   // optional: mirror into the save
});
events.refresh();   // after each state change; cheap, updates in place, grants once the task is done
```

Flavour keys per event: `title`, `text` (banner line), `task` (what to do), `goal` + `unit` (for the progress line and meter), `icon` (decorative), `badge_label`. Defaults exist for all of them (the name from the event table, a neutral line, no task), so a bare `{}` works. Wording should stay hemisphere-neutral ("harvest", "long days").

Options: `today` (a `Date`, a `"YYYY-MM-DD"` string or a function), `calendar` (a custom event array in the `seasonal_events.DEFAULT_EVENTS` schema), `dates` (a moving-holiday table object) or `datesUrl` (default: `shared/seasonal-dates.json` next to the script, fetched once), `container` (selector or element: put the banner in the page flow instead of the fixed strip), `reserveSpace` (default true), `autoGrant` (default true), `banner: false` (grant only), `rememberDismiss`, `localBadges`, `toastMs`.

**Dates are never hardcoded.** Today is, in order: the `today` option, the URL parameter `?event-date=2026-10-31` (so every event can be tested any day), then the browser's local date. A year the moving-holiday tables do not cover is never active.

### Badges (the existing path)

Badge shape is the hub contract R2-Z23b (`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md` section 8): `{ id: "halloween-2026", label: "Halloween 2026", earned_at: "2026-10-31" }`, id `/^[a-z0-9-]{1,64}$/`. **Use the JavaScript `badgeId` / Python `hub_badge_id`, not Python's older `badge_id`**: the engine's own ids contain underscores (`new_year-2027`) which the hub's sanitiser rejects; the hub-safe forms are `new-year-2027` (the existing `badge_id` is unchanged and still tested).

A grant is (1) merged into `localStorage["event_badges_v1"]` as `{version: 1, badges: [...]}`, which `script.js` already unions into the hub's "Event badges" block, and (2) handed to `onGrant(badge, allBadges)` so a game can also keep the list in `save_data.event_badges`, which travels with the account. On load, pass saved badges back in with `init({ badges })` or `events.adoptBadges(list)` (malformed entries and duplicates are ignored). A Python game builds the same entry with `seasonal_events.badge_entry(event, today.isoformat())`. Grants happen once per badge id however often `refresh()` runs.

Other methods: `active()` (events live today and hosted here), `grant(eventId)`, `badges()`, `hasBadge(id)`, `dismiss(id)`, `setToday(x)`, `setDates(obj)`, `today()`, `todaySource()` (`"option"`, `"url"` or `"clock"`), `destroy()`. Pure helpers on `NoyvjSeasonal`: `activeEvents(today, {events, dates})`, `eventWindow`, `easterSunday`, `nthWeekday`, `badgeId`, `badgeEntry`, `resolveToday`, `DEFAULT_EVENTS`.

### Banner behaviour and accessibility

A `role="region"` labelled "Seasonal event: <title>" with the title, flavour line, task, a progress sentence and a meter (the sentence is the real information, the meter is `aria-hidden`), the end date ("Open until 1 Nov") and the badge name, and a Dismiss button. State without colour: open is a dashed border with the words "Open until ...", earned is a solid border, a check and "Badge earned: ..." text. A dismissed banner stays dismissed on reload (`localStorage["seasonal-dismissed:<game>:<badge id>"]`, a per-viewer convenience; `rememberDismiss: false` to skip) but the badge is still granted when the task completes. A grant also shows a toast in a polite live region. By default the banner is a **fixed strip** at the top (below a "What's new" banner if one is showing) so it cannot break a flex or grid page shell, and it reserves its own height as `html` padding so it never covers the game's header; the space is given back when it is dismissed or the window closes.

---

## 4. General opt-in leaderboards (`app/boards.py`, `shared/leaderboard.js`, TODO W-5 and Z-4)

One game-agnostic board system beside the four original boards (SOL, Signal, Aftermath, Herd keep their `/leaderboards/...` routes, public usernames and one-script-tag form, unchanged). A game adds a board by registering it on the server once and calling two functions in the browser. Backend code is `app/boards.py` plus the "General opt-in boards" section of `app/main.py`; tests are `app/tests/test_boards.py` and `shared/tests/test_leaderboard_browser.py`.

### What a board is

Registered in `app/boards.py` with one call (a typo raises at import, not at a player's first score):

```python
register_board("last-line", "endless_best_wave",
               label="Endless: best wave reached", order="desc",   # "desc" higher is better, "asc" lower is better
               low=1, high=10_000,                                  # accepted range: anything outside is refused (422)
               windows=("weekly", "alltime"),                       # any of daily / weekly / alltime
               integer=True, unit="waves")                          # whole numbers only; unit is display text
```

Three boards are already registered for games that are planned (`canopy/community_investment`, `last-line/endless_best_wave`, `thaw/hold_the_line`). Their bounds are generous guesses: **tighten each one when its game is wired in.** Ids are lowercase letters, digits, `_` and `-`.

Windows are UTC: **daily** is the UTC date, **weekly** is the ISO week (starts Monday, `2026-W41`), **alltime** is one row. The server picks the current day and week itself, so a client cannot post into a past period. One best score is kept per account per window. Old daily rows (90 days) and weekly rows (about a year) are deleted when anyone posts to that board; all-time is kept.

### Privacy tier

- **Anonymous by default.** Rows read `Player 7F2Q`: four characters of an HMAC of the account id and the game id (no look-alike characters). It is per game, so the same account has a different handle on each game and cannot be linked across them, and it cannot be turned back into a username. Two anonymous players that would share a handle both get an eight-character one. Set `LEADERBOARD_SALT` on the server to change the handles (optional; there is a default).
- **One account setting.** `PUT /users/me/leaderboard-privacy {"show_username": true}` (and `GET`) switches every board row of that account to its username. Off until the player turns it on. The shared widget has the checkbox.
- **Opt-in is enforced on the server.** `POST /scores` needs a signed-in account **and** `"opt_in": true` in the body, or it answers 400 and stores nothing. Test accounts are accepted and ignored. Opting out is `DELETE /scores/{game}/{board}` (one board) or `DELETE /users/me/scores` (everything).
- **Small-group suppression.** A board window lists no rows until at least 3 visible players are on it (`boards.MIN_VISIBLE`, the same number the aggregate stats use). The response says `suppressed: true`; the player still sees their own entry (`mine`). Hidden rows and test accounts do not count towards the 3.
- Responses never contain an account id or username except when that account chose to show it. Admin sees real usernames.

### Routes

| Route | Who | What |
|---|---|---|
| `GET /leaderboard` | anyone | The registry (game, board, label, order, windows, unit, default window) for pickers. |
| `GET /leaderboard/{game}/{board}?window=&period=` | anyone (a bearer token adds `you` and `mine`) | Top 10 for the current period of the window, or a past `period` (`2026-10-07`, `2026-W40`). Default window is all-time if the board has it. |
| `POST /scores` | signed in | `{game, board, score, detail?, opt_in: true, windows?}`. `windows` limits which windows are updated (used when re-sending a stored best). Answers 422 for out-of-range, non-numeric, non-finite or fractional-on-an-integer-board scores, 429 when throttled. |
| `DELETE /scores/{game}/{board}`, `DELETE /users/me/scores` | signed in | Opt out. |
| `GET /users/me/scores` | signed in | The caller's current-day, current-week and all-time rows with ranks. |
| `GET` / `PUT /users/me/leaderboard-privacy` | signed in | The username switch. |
| `GET /admin/scores`, `PATCH /admin/scores/{id}` | admin token or the owner account | List rows with the real username, filter by game/board/window/period; `{"is_hidden": true}` hides a test row (same pattern as hiding feedback). A hidden row leaves the public board, the ranks and the suppression count, and stays hidden if the player improves it. |

Throttling reuses `throttle.FailureLimiter` as a sliding counter: 60 accepted submits an hour per account, 200 an hour per address, and 10 refused submits per 15 minutes per account (probing the bounds earns a 429 even for a good score). In-process, like the login limiter, so it resets on a restart.

### In a game: two calls

```html
<div id="leaderboard-mount"></div>
<script src="../../shared/hub-auth.js"></script>       <!-- already on every game page via the save widget -->
<script src="../../shared/leaderboard.js"></script>
<script>
  NoyvjLeaderboard.addBoard({
    game: "last-line", board: "endless_best_wave",
    title: "Endless: best wave", unit: "waves", order: "desc",     // order must match the server's registration
    windows: ["weekly", "alltime"],                                 // a subset of the registered windows
    mount: "#leaderboard-mount",                                    // optional: omit for no panel, report() still works
  });
</script>
```

At the end of a run, one line (a number, plus an optional short detail such as a seed):

```js
NoyvjLeaderboard.report("last-line", "endless_best_wave", wave, "seed 4821");
```

The declarative form is the same script tag the old boards use plus `data-api="scores"` and `data-windows="weekly,alltime"`. The panel has a tab per window (a tick and `aria-pressed` mark the current one, 44 px high), the rows, the player's own line, an opt-in checkbox and the username checkbox (both only when signed in), and a note that days and weeks are UTC. Text from the server is only ever written with `textContent`. Nothing is sent until the box is ticked; ticking it sends what the player already earned on this device (one request per window, never an old day's best as today's); `report()` sends only the windows where the score improved on the best remembered here, so calling it every run is cheap. It fails soft: a network error never touches gameplay.

Notes for the wiring step: a game that is already an original-form board (SOL, Signal, Aftermath, Herd) does not need to move. To get daily boards for Signal, register a new `signal` board in `boards.py` and call `addBoard`; the old streak board can stay. `shared/leaderboard.js` is not in `sw.js`'s precache list today (the four games load it from the network when online); add it (and bump `SW_VERSION`) if a game should show its board offline-first. The hub page `leaderboards.html` reads `GET /leaderboard` and lists every registered board (TODO Y-3).

### Deploy note (owner)

Two **new** tables, `score_entries` and `score_profiles`, are created by `Base.metadata.create_all` on the next start of the backend. No `patch_schema()` statement is needed (no existing table gains a column). The routes go live with the usual push (FastAPI Cloud redeploys within about five minutes).

---

## Which TODO items these unblock

- W-5 and Z-4 are built (this section). GB-19 (Canopy community plot board), T-2 (Last Line), GG-2 (Thaw's Hold the Line), GD-5 / GH-7 / GC-29 / GF-6 (daily and weekly boards) and Signal's daily board only need their `register_board` line and an `addBoard` call.

- GB-13, GB-15, GB-16 (Canopy poacher, storm front, spirit story levels): `levels.json` with three modes/mechanics at positions 5, 10, 15 plus `onStart`.
- GB-10, GB-26 (Canopy Seed Vault, ranger crews): one tree each (or one tree with a `crews` branch), `earned` from the game's Seed Vault currency.
- O-1 (Trade Empire charter tree): can adopt the renderer later without changing its `CHARTER_PERKS` data (it already uses `branch`, `cost`, `label`, `requires`, `description`).
- N-2 (first event end to end): `NoyvjSeasonal.init` plus the game's task predicate; the first host game is the main session's choice.

---

## Site-wide includes (Z-19, Z-21, Z-23, Z-24, Z-25, Z-29, Z-31)

Seven small shared pieces that every game page (Classic `index.html` and the generated Desktop `pc.html`) carries, with lite mode and the a11y stylesheet also on the hub pages. They are wired by `python3 scripts/wire-shared-includes.py` (idempotent, `--check` to verify); run `python3 scripts/generate-pc-pages.py` afterwards. `shared/tests/test_site_includes.py` is the source of truth for which pages need what and in which order. A **new game** only needs a `shared/theme.js` tag and `</head>`, then that script.

| File | What | Notes |
|---|---|---|
| `lite-mode.js` / `lite-mode.css` (Z-31) | Slow-computer switch: `<html data-lite="true\|false">` before first paint, `localStorage["lite-mode"]` = `"true"`/`"false"` (absent = not chosen). | On by default, with a visible note and Keep/Turn-off buttons, when `navigator.deviceMemory <= 2`, `hardwareConcurrency <= 2` or data-saver is on, and the player has not chosen. `NoyvjLite.on()/set()/reset()/auto()/chosen()/onChange()` and the `noyvj-lite-change` document event. Any `[data-lite-toggle]` element (checkbox or button) is wired automatically and `[data-lite-status]` gets a sentence. Synced to the account as `lite_mode` by `site-settings.js` (the backend whitelists it). The CSS ends every animation and transition (0.01 ms, so end states still apply), removes backdrop blur, hides the nebula/aurora/blob layers and removes big shadows from panels, cards and dialogs (never from `.selected` or focused things). A game with its own costs reads `NoyvjLite.on()` (Continuum's 3D scene does). It sits beside each game's own "reduce motion" switch, which keeps working. |
| `a11y.css` (Z-19) | `prefers-reduced-motion` and `prefers-contrast: more`. | Reduced motion also follows `html[data-reduced-motion="true"]`, `html.reduce-motion` and the hub's `data-hub-reduced-motion`; `data-motion-essential` opts an element out. Contrast: 2px control borders, underlined links, full-strength secondary text, a 3px focus ring, dimmed decorative backgrounds. |
| `touch-targets.css` (Z-23) | `touch-action: manipulation` everywhere; 44px minimum height for buttons, selects, fields, summaries and checkbox rows on touch screens or windows up to 640px. | Deliberately not a min-width (it would change how wrapping toolbars pack). The round "i" buttons and the back link keep their look and get an invisible 44px hit area. `data-touch-exempt` opts an element out (Signal's board cells). Hub pages do not include it. |
| `error-boundary.js` (Z-25) | One friendly panel for uncaught errors, rejections and PythonErrors, with Copy details, Reload and Dismiss. | Reads only; never touches storage; the report has no save codes or tokens. Ignores cross-origin "Script error.", ResizeObserver, ad-script and fetch/abort noise. `NoyvjErrors.report(err)` shows a caught error too. |
| `perf-mark.js` (Z-21) | `performance.mark("noyvj:<name>")` for script-start, dom-ready, pyodide-loaded, game-setup-done (`get_state` defined) and first-interactive, plus a `noyvj:boot` measure. | Console format `[noyvj-perf] <game> <mark> <ms>ms` and one `... boot` summary line. `NoyvjPerf.marks()/summary()`. |
| `debug-overlay.js` (Z-24) | `?debug=1` corner box: fps, `get_state()` size in bytes, last `/saves` body length, heap, lite, error count, boot marks. | Without the flag it does nothing (no element, no timer, `fetch` not patched). |
| `info-footer.js` (Z-29) | Footer in `#howto-panel` and `#info-page-panel`: `NoyvjGames · <game> · updated <newest changelog date> · [seed] · <site URL>`. | Re-added if the game rewrites the panel. Shows a seed once a game exposes `window.NoyvjSeed.current()` or `window.NOYVJ_SEED` (Z-1). |

Not yet wired: Le Champ de Mots (another session edits `games/champ-de-mots/index.html`). The test lists its two pages as an expected failure until `scripts/wire-shared-includes.py` and a Desktop regeneration have been run for it.

---

## 5. Seeded runs and the daily seed (`shared/seed.py`, `shared/seed.js`, TODO Z-1 and Z-5)

One short seed string drives a whole run, the same in Python (Pyodide or CPython) and in JavaScript. Tests: `shared/tests/test_seed.py` (pinned values, ranges, parsing) and `shared/tests/test_seed_browser.py` (the two languages agree on 247 seeds across every draw type, on a daily seed for every day of 2026 and 2027, and on 900+ parsing cases; plus the UI helpers). **A deliberate change to the algorithm must bump `ALGORITHM_VERSION` and re-pin the values in both tests**, because every shared seed would otherwise change meaning.

### The seed string

`TIDE-K7F2Q`: a prefix, a dash, five characters. The prefix is the game slug upper-cased with everything that is not a letter or digit removed (`trade-empire` becomes `TRADEEMPIRE`, 2 to 12 characters). The five characters come from `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (31 symbols, no `0 1 I L O`), so a seed read aloud or copied by eye is hard to get wrong. `normalize(text, game?)` forgives case, spaces, odd dashes and underscores, a missing dash (`tidek7f2q`) and, when a game is named, a bare code (`k7f2q`). `validate(text, game?)` returns `{ok, seed, error, message}` with `error` one of `""`, `"empty"`, `"format"`, `"wrong-game"`; the messages are ready to show.

### The generator

splitmix64 started from the FNV-1a 64 hash of the seed text (the same construction as `games/chronicle/puzzle.py`). JavaScript uses BigInt so it is exact. Nothing uses `random`, the clock or the platform.

| Python (`seed.Rng(seed)`) | JavaScript (`NoyvjSeed.rng(seed)`) | notes |
|---|---|---|
| `next()` | `next()` | 64-bit unsigned (a JS BigInt) |
| `below(n)` | `below(n)` | unbiased integer in `[0, n)` |
| `random()` | `random()` | float in `[0, 1)` with 53 bits, identical in both |
| `randint(a, b)` | `randint(a, b)` | both ends included |
| `uniform(a, b)`, `chance(p)` | same | |
| `choice(items)` | `choice(items)` | empty list raises |
| `shuffle(items)` / `shuffled(items)` | same | `shuffle` works in place and returns the list; `shuffled` copies |
| `sample(items, k)` | `sample(items, k)` | without replacement, in draw order |
| `weighted_choice(items, weights)` | `weightedChoice(items, weights)` | |
| `fork(label)` | `fork(label)` | an independent stream that depends only on seed and label, so adding a draw in one place does not shift another system |
| `get_state()` / `set_state(s)` | `getState()` / `setState(s)` | the position as a decimal string, for saving a run mid-way |

Module functions: `new_seed(game, entropy=None)` / `newSeed(game, entropy?)` (OS or `crypto` randomness; `entropy` is a function `n -> int below n`, or any object with `below(n)`, so a test can fix it), `daily_seed(game, date)` / `dailySeed(game, date)`, `prefix_for`, `example`, `normalize`, `validate`, `is_valid`. The JavaScript object also has the snake_case aliases `new_seed` and `daily_seed`.

### Using it in a game

**Python game (the usual case):** write the module into Pyodide's file system the way the games already do for `info_page.py`, then route every draw through one `Rng`:

```js
const seedSource = await (await fetch("../../shared/seed.py")).text();
pyodide.FS.writeFile("seed.py", seedSource, { encoding: "utf8" });
```

```python
import seed as noyvj_seed
run_seed = noyvj_seed.new_seed("tide")            # or the seed the player typed, or a daily seed
rng = noyvj_seed.Rng(run_seed)
weather = rng.fork("weather")                     # one stream per system
storms = [rng.randint(1, 6) for _ in range(5)]
state["seed"] = run_seed                          # keep it in the save so a resumed run can say it
state["rng_state"] = rng.get_state()              # optional: resume the stream exactly where it was
```

Tell the page which seed is live so the info footer shows it: `window.NoyvjSeed.set(run_seed)` (from Python: `from js import window; window.NoyvjSeed.set(run_seed)`). `window.NoyvjSeed.current()` returns it and is what `shared/info-footer.js` reads; it emits a `noyvj-seed-change` event on `document`. Nothing is stored by the module: the game keeps the seed in its own save.

**Run-end screen, "copy seed" (a few lines):**

```html
<div id="run-end-seed"></div>
<script src="../../shared/seed.js"></script>
```

```js
const copyBox = NoyvjSeed.mountCopy("#run-end-seed", { seed: runSeed });   // later: copyBox.update(nextSeed)
```

**New-game screen, "start from seed" field:**

```js
NoyvjSeed.mountStart("#new-game-seed", { game: "tide", onStart: (seed) => startRun(seed) });
```

`mountStart` validates (a bad seed is explained in text with a leading "!" and a dashed border, and focus returns to the field), accepts a loose entry such as `k7f2q`, sets `NoyvjSeed.current()` and calls `onStart(seed, {fromUser: true})`. A "Random seed" button fills the box (`random: false` hides it). `NoyvjSeed.fromUrl(game)` returns a valid `?seed=` from the address, for a shared link (Z-2 builds on that).

Both helpers: a labelled group or form, a live status region (`role="status"` / `role="alert"`), buttons and the field at least 44 px high, glyph plus words for every state (`✓ Copied TIDE-K7F2Q`, `! That is not a seed...`), `--ns-*` colour tokens that follow `html[data-theme="light"]` and the OS preference, no transitions under reduced motion (`prefers-reduced-motion` or `html[data-reduced-motion="true"]`), and when the clipboard is refused a selected read-only box with "press Ctrl+C". All text is written with `textContent`.

### Daily seed and "Today's run" (Z-5)

`daily_seed(game, "2026-10-08")` is the one seed everybody gets that UTC day, derived only from the date string and the game (`TIDE-X54PB` for Tide on 2026-10-08), so it needs no server. It is an ordinary seed: it validates, goes into `Rng`, and can be copied.

```js
const daily = NoyvjSeed.daily.mountButton("#start-screen-daily", {
  game: "tide", onStart: (seed, info) => startRun(seed, { daily: true }),   // info = {daily: true, date}
});
// when a run ends: if (NoyvjSeed.daily.isDaily("tide", runSeed)) NoyvjSeed.daily.markCompleted("tide", { score: 4210, text: "4,210 pts" });
```

The button reads "Play today's run" and, once done, "↻ Play today's run again" with "✓ Today's run done" (solid border versus dashed when open), the seed, the UTC date, and a kind streak line ("3 days in a row, best 5" or "Best streak 5: a new one starts whenever you like": nothing is ever described as lost).

**Storage the hub will read:** `localStorage["noyvj-daily-v1"]`, per browser:

```json
{ "version": 1,
  "date": "2026-10-08",
  "runs":    { "tide": { "seed": "TIDE-X54PB", "completed_at": "2026-10-08T14:03:00.000Z", "score": 4210, "text": "4,210 pts" } },
  "streaks": { "tide": { "count": 3, "best": 5, "last": "2026-10-08" } } }
```

`date` is the UTC date the `runs` belong to: a reader on a later day must treat `runs` as empty (`NoyvjSeed.daily.read()` does, and the next write replaces it). `streaks[game].last` is the most recent UTC date a daily was completed; the streak is alive while `last` is today or yesterday, and `daily.streak(game)` returns `{count, best, last, doneToday}` with `count` 0 once it lapsed. A completion counts once per day (`markCompleted` returns the stored run, or `null` when already recorded or storage is blocked) and fires `noyvj-daily-change` on `document`. Game ids are the slugs (`/^[a-z0-9-]{1,40}$/`); anything malformed in storage is ignored. A hub Today strip only needs `JSON.parse(localStorage.getItem("noyvj-daily-v1"))`, the date check above and the slug list. The helper never calls the network; a leaderboard post (`NoyvjLeaderboard.report`) is the game's separate choice.

Not built here: the hub strip itself, the per-game wiring, and Z-2 challenge links.

---

## 6. Rarity labels and hidden achievements (`shared/achievement-stats.js`, TODO Z-15)

The existing "Earned by N% of players" line is unchanged. Added, with no change to any game's markup:

- **Rarity label** under the percentage: `★ Gold · rare`, `◆ Silver · uncommon`, `● Bronze · common` (rarer is better). Text, a shape and a border style (double, dashed, dotted) carry the meaning, never colour alone; the label has its own opaque background and text colour, so it stays legible on any game's panel in light and dark.
- **Thresholds are in one place**: `RARITY_THRESHOLDS = { gold: 10, silver: 35 }` at the top of the file's script (a label applies when `earned_pct` is at or below the number, rarest first; above 35 is Bronze). `NoyvjAchievementStats.setRarityThresholds({gold, silver})` changes them at runtime (returns false for nonsense such as `silver <= gold`). The percentages are live, so the labels move as players arrive.
- **Suppressed when the percentage is**: no label while the game's response is `suppressed`, or when an achievement id is missing from the response (too few players), or when the fetch failed. Never a guess, never 0%.
- **Hidden achievements.** A row counts as hidden when its element has `data-achievement-hidden="true"` or its id was registered with `NoyvjAchievementStats.registerCatalog(list)` (an `achievements.json` array whose entries may carry `"hidden": true`). While it is not earned (a class ending in `earned`, such as `achievement-card--earned` or Le Champ de Mots' `achievement-earned`, or `data-achievement-earned="true"`), its `.achievement-card-description` (or `[data-achievement-description]`) shows `???`; the label stays visible. Masking runs synchronously inside `applyAchievementStats()`, before the first paint and whether or not stats load; after a row is earned the next `applyAchievementStats()` (or `NoyvjAchievementStats.maskHidden(panel)`) restores the real text. No game has a hidden achievement yet: to add one, set `"hidden": true` in that game's `achievements.json` and have its achievements panel write `data-achievement-hidden="true"` on the row (or call `registerCatalog` once after loading the json).

Other exports on `window.NoyvjAchievementStats`: `rarityFor(pct)`, `RARITY_INFO`, `getStats(gameId)` (per-game cache, 60 s), `peek(gameId)`, `earnedPct(data, id)`, `statTextFor`, `isHiddenRow`, `isEarnedRow`. Every existing consumer is unchanged: every game that includes the script still calls `window.applyAchievementStats()` from their own panel code, and the `.achievement-earn-rate` line, its text and its once-per-row guard are the same. Tests: `shared/tests/test_achievement_stats_browser.py` (mocked endpoint).

---

## 7. Copy result (`shared/copy-result.js`, TODO Z-20)

One helper formats a Wordle-style result and copies it. Signal keeps its own share text and does not use this. Tests: `shared/tests/test_copy_result_browser.py`.

```html
<div id="run-end-copy"></div>
<script src="../../shared/copy-result.js" data-game-id="tide"></script>
```

```js
NoyvjCopyResult.mountButton("#run-end-copy", {
  getResult: () => ({                       // called on every click, so it can read the finished run
    game: "Tide", score: finalScore, unit: "pts",
    stats: [{ n: stormsSurvived, one: "storm survived", many: "storms survived" }],
    seed: runSeed,                          // optional: the "(seed ...)" tail appears only when this is a non-empty string
  }),
});
// -> "Tide, 4,210 pts, 3 storms survived (seed TIDE-K7F2Q)"
```

Fields: `game`, `score` (a number gets thousands separators; a string is used as is), `unit`, `stats` (strings, numbers, or `{n, one, many}` for the singular/plural), `seed`, `withSeed: true` (use `NoyvjSeed.current()` when `shared/seed.js` is loaded), `link: true` (adds a second line with the game's address, from `data-game-id` on the script tag) or a string. The line is flattened to one line, capped at 240 characters and is plain text. Also `NoyvjCopyResult.format(fields)`, `plural(n, one, many)`, `copy(text)`; `mountButton` returns `{update(fields), copy(), destroy()}`. The button is 44 px high, announces `✓ Copied: <line>` in a polite live region, and if the clipboard refuses shows the text in a selected read-only box with "press Ctrl+C". `label` and `onCopy` are options. Wiring each game's end screen is a later step: one `mountButton` call plus the three or four fields each game already has on that screen (every practice or minigame result should still feed a visible stat).

---

## 8. Achievement share (`shared/achievement-share.js`, TODO Z-27)

Copies `I earned Cleanup Crew in Tide, 12.5% of players have it` and, on the next line, the game's link, using the live `earned_pct`. While the game is suppressed, the achievement has too few earners, or the request failed, the percentage is left out (`I earned Cleanup Crew in Tide`): never a guess, never 0%. Tests: `shared/tests/test_achievement_share_browser.py` (mocked endpoint).

```html
<script src="../../shared/achievement-stats.js" data-game-id="tide"></script>   <!-- optional: shares its cache -->
<script src="../../shared/achievement-share.js" data-game-id="tide" data-game-name="Tide"></script>
```

With `data-game-id` present nothing else is needed: a Share button is added to every **earned** row of `#achievements-panel` (rows with `data-achievement-id` and an earned class, as the games already render them), and kept there when the game rebuilds the panel. Without it, call `NoyvjAchievementShare.mountButton(container, {game, gameName, achievementId, label})`, or `share(opts)` (copies now, resolves `{ok, text}`) or the pure `text({label, gameName, game, earnedPct, url})`. The stats are prefetched when a button mounts, so the click copies immediately inside the user gesture; a click made before they arrive waits at most 1.5 s. The link comes from where the script was loaded (`../games/<game>/`). If the clipboard refuses, a selected read-only box appears. Buttons are 44 px high, labelled `Share: <achievement>`, with a polite status line, light and dark tokens and no transitions under reduced motion. Not yet added to any game page (the game pages need the one extra script tag; `sw.js` precache and `SW_VERSION` are the main session's call).

---

## 9. Report a problem (`shared/report-problem.js`, backend `bug_reports`, TODO Z-17)

A "Report a problem" button and dialog for every game. **Adopting it is two lines** in the game's `index.html` (the Desktop page picks them up when `pc.html` is regenerated), after the other shared includes:

```html
<script src="../../shared/report-problem.js" data-game-id="canopy" data-schema-version="3"></script>
```

(That is line one; `data-schema-version` is optional and should be the save's `schema_version` from `shared/migrate.py` if the game has one. Line two is only needed when the game wants a menu entry instead of the small floating button: add `data-button="none"` to the tag and call `NoyvjReport.open()` from the game's own button; `data-mount="#some-container"` puts the built-in button inside an element instead of floating it.) Not yet in `sw.js`'s precache list.

- **Preview.** The dialog has one box ("What happened?") and a plain-text box headed "Exactly what will be sent". The request body and the preview are built from the same object (`NoyvjReport.payload` and `NoyvjReport.previewText`), and a test checks that every posted value appears in the preview.
- **Always sent:** game id, the page's path (no query string, no hash), the note, the save-schema version if the game gave one. **Off until ticked:** the save code (read from `localStorage["savecode:<game>"]`, or `NoyvjReport.configure({getSaveCode})`), the browser and window size, the last 20 console lines, and (signed in only) "link this report to my account" so it is deleted with the account. Nothing is sent until Send is pressed.
- **Console capture.** A ring buffer of the last 20 lines (`console.log/info/warn/error/debug`, uncaught errors, unhandled rejections), started when the script loads, memory only, lines cut at 300 characters, bearer tokens, `token=`/`key=`/`password=` values, save codes and emails replaced with `[removed]` as they are captured (the server scrubs again).
- **Accessibility and layout.** Native modal `<dialog>` (focus stays inside, Escape closes, focus returns to the opener), labelled controls, 44 px targets, Ctrl/Cmd+Enter sends, light and dark tokens following `html[data-theme]` and the OS, no animation, works at 360 px, prints as nothing.
- **Backend.** `POST /bug-reports` (public; 15 per address per hour; note 2000 characters, console 20 lines of 300, page 300; `attachment` accepts only `{"save_code": "XXXX-XXXX"}`; 413 above 5 MB; `link_account` links the row to the bearer token's account only when true) and the admin-only `GET /admin/bug-reports` (filters `game_id`, `resolved`, `fixed`, `limit`) and `PATCH /admin/bug-reports/{id}` (`resolved`, `fixed`, `note`, like the answer reports), shown in the "Problem reports" panel of `admin.html`. Linked rows are in `GET /users/me/export` and deleted with the account. Table `bug_reports` is new, so `create_all` builds it and `patch_schema()` needs nothing.
- Tests: `shared/tests/test_report_problem_browser.py`, `shared/tests/test_admin_bug_reports_browser.py`, `app/tests/test_bug_reports.py`.

---

## 10. Player profile (`shared/profile.js`, `profile.html`, backend `user_profiles`, TODO Z-7 and Y-1)

**Games feed it, one call at save time.** Adopting it is two lines:

```html
<script src="../../shared/profile.js" data-game-id="canopy"></script>
<!-- in the save path, after a successful save: -->
<script>NoyvjProfile.update({ achievements: earnedIds.length, streaks: { daily: dailyStreak } });</script>
```

(In practice the second line lives in the game's own code or, better, once in `shared/save-widget.js` after a successful save so no game needs it.) Every field is optional: `game` (defaults to the tag's `data-game-id`), `seconds` (time played since the last call; leave it out and the helper counts the seconds the page was open and visible), `achievements` (a count or an array of ids; only ever raises the stored count), `streaks` (`{label: value}`, lowercase letters, digits and `_`; the server keeps the longest). It never blocks or breaks saving (returns at once, swallows every error), posts only for a signed-in player (signed out it keeps and sends nothing), is throttled to one post per game every 5 minutes (a hiding page may send what is waiting at most every 30 seconds), keeps unsent work in `localStorage["profile-sync:<game>"]`, retries after a failure and backs off 15 minutes after a 429. It sends numbers and ids only (plus the seasonal badge ids from `localStorage["event_badges_v1"]`). One post credits at most four hours.

- **Data model** (table `user_profiles`, one row per account, defaults when absent): `is_public` (**off by default**), `favourite_game`, per-game `{seconds, achievements}`, streaks (`"<game>:<label>"` -> longest), seasonal badge ids. Member-since is the account's creation date. Milestone badges (`first-steps`, `achiever-10/50/100`, `explorer-3/8/14`, `time-1h/10h/100h`, `streak-7/30`) are computed from those numbers by `app/profiles.py`, so there is one definition; seasonal badge labels are derived from the id on the server, never taken from the client.
- **Routes.** `GET /users/me/profile` (the owner's view), `PUT /users/me/profile` (merge: `is_public`, `favourite_game` (null clears), `event_badges`, `progress`), public `GET /profiles/{username}` which answers 404 **identically** for "no such player" and "profile is off", never returns an email, save, save code, token or internal id, and is rate limited per address. The profile is in `GET /users/me/export` and deleted with the account.
- **`profile.html?u=name`.** Public view: badges (with a glyph and the word "Seasonal" for event badges, never colour alone), achievements per game, favourite game, member since, total time, longest streaks, honest empty and not-public states. For the signed-in owner: the "Make my profile public" switch, a share link with a Copy button, a favourite-game picker, and a preview of what others would see. No tracking of any kind. `noindex`. Not in `sw.js`, `sitemap.xml` or the hub's phone app bar yet (main session); `scripts/wire-shared-includes.py`'s `HUB_PAGES` and `shared/tests/test_site_includes.py` do not list it either, but its head follows the same include order.
- Tests: `app/tests/test_profiles.py`, `shared/tests/test_profile_helper_browser.py`, `shared/tests/test_profile_page_browser.py`.

---

## Time controls and pause-when-hidden (W-2, Z-28)

Files: `shared/time-controls.js`, `shared/time-controls.css`, `shared/pause-hidden.js`. Tests: `shared/tests/test_time_controls_browser.py`, `shared/tests/test_pause_hidden_browser.py`, plus `tests/test_time_controls.py` in SOL, Canopy and Trade Empire and `tests/test_pause_hidden.py` in Continuum. Not yet in `sw.js`'s precache: add the three files.

### Audit of the 14 games (2026-10-08)

| Game | Real-time tick? | Pause and speed today | How the tick is driven | Done |
|---|---|---|---|---|
| SOL | yes, 100 ms | none | Python `setInterval(tick, 100)` in `setup()` | time controls + pause-hidden |
| Canopy | yes, 1 s | none | Python `setInterval(tick, 1000)` | time controls + pause-hidden |
| Trade Empire | yes, 1 s | none | Python `setInterval(tick, 1000)` | time controls + pause-hidden |
| Continuum | yes, season clock | already has Pause/1x/2x/4x (U1) | JS `setInterval` 250 ms in `index.html` calling Python `tick_clock(dt)`, steps clamped to 1 s, skipped while hidden | pause-hidden only (hooks); its own buttons kept |
| Tide | no (turn based, Advance Season) | n/a | one-shot UI timeouts only | audited, left alone |
| Aftermath, Grid, Herd, Thaw, Loop, Drift | no (turn based) | n/a | one-shot `setTimeout` toasts; Aftermath has a cosmetic 40 ms count-up | left alone |
| Le Champ de Mots | only the timed arcade minigames: a 1 s JS `setInterval` calling `blitz_tick`, `sprint_tick`, `racer_tick`, `boutique_tick`, `cafe_tick` (no-ops outside a running minigame) | none | JS `setInterval` 1000 in `index.html` | not touched (another session's folder). Fast-forward makes no sense for a timed quiz; pause-when-hidden would (candidate for a later pass, hooks mode) |
| Signal | no (the "next puzzle" countdown is a wall-clock label) | n/a | none | left alone |
| Chronicle, Lexis | no | n/a | none (announce timeouts only) | left alone |

Other timers that are NOT simulation ticks and were left alone: SOL's hold-to-repeat button timer (`hold-repeat.js`, already stops on `visibilitychange`), Continuum's 3D screensaver `requestAnimationFrame` loop (visual only, already skips when hidden).

### `NoyvjTime` (time-controls.js)

Mount: `<div id="time-controls"></div>`, `<link rel="stylesheet" href="../../shared/time-controls.css">` after the game's own stylesheet and before `a11y.css`, and `<script src="../../shared/time-controls.js" data-game-id="sol" data-container="#time-controls"></script>`. Options as data attributes: `data-speeds="1,2,4"`, `data-keys="off"`, `data-start-paused="true"`, `data-modal-selector`. The game then hands over its tick instead of calling `setInterval`:

```python
from js import window
window.NoyvjTime.start("sol", create_proxy(tick), TICK_INTERVAL_MS)   # keep a setInterval fallback for tests / old pages
```

or `NoyvjTime.start(gameId, fn, baseMs)` from JS. Calling `start` again replaces the tick (never a second timer). API: `create(opts)`, `start`, `controller(id)`, `get(id)`, `intervalFor(baseMs, speed)`; controller: `setSpeed(n)`, `pause()`, `resume()`, `toggle()`, `hold(reason)`, `release(reason)`, `isRunning()`, `snapshot()`, `subscribe(fn)`, `handleKey(event)`, `stop()`, `destroy()`. A change also fires `document` event `noyvj-time-change` (detail = snapshot) and sets `<html data-time-state="running|paused|held">`.

Rules (the "never change tick math" contract):
- Speed n calls the tick every `baseMs / n` ms (floor 20 ms). The tick itself is untouched and must not read the speed; a game test should pin that only the small start helper mentions `NoyvjTime`.
- Paused or held: no timer exists, so no tick; there is no stored time debt, so resuming never fires a burst, and the time spent paused gives no progress. 4x is "four times as many ordinary ticks", never a skipped rule; if a slow computer cannot keep up, the game just runs slower than 4x.
- Choosing a speed while paused resumes at that speed. A "hold" (used for the hidden tab) sits beside the player's pause and speed and never overwrites them.
- Player actions (clicks, buying, planting, selling) are not ticks and still work while paused.
- The speed is never saved (not in saves, not in localStorage); a reload starts at 1x, running.
- Away or offline handling is per game and documented in each game's `CLAUDE.md`: none of SOL, Canopy or Trade Empire advances anything from wall-clock time while closed or hidden; a game's own away report must count ticks, not wall time (SOL's does).

Keys (documented defaults; only active with no text box, dialog, tutorial, level select or opening screen in front): Space pause or resume, but only when nothing interactive has the focus (a focused button, link or Canopy plot keeps Space); `[` slower; `]` faster. `keys: false` turns the built-in handler off and a game's own key handler can call `controller.handleKey(event)` (returns true when it acted). Games list them in their `?` help (`KeyboardShortcuts.init({extra: [...]})`) and the Desktop hint bar (`["Space", "Pause / resume"], ["[ ]", "Slower / faster"]` in `pc-config.json`).

Accessibility: a `role="group"` named "Game speed" of four real buttons (44 px minimum), `aria-pressed` on the current choice, a `role="status"` line saying "Paused", "Paused (tab hidden)" or "Running at 2x". The current choice is marked by a check mark, a heavier border and bold text; Pause is a dashed border; none depends on colour. Light/dark tokens like the other shared pieces, transitions only without `prefers-reduced-motion` and `html[data-reduced-motion="true"]`.

### `NoyvjPauseHidden` (pause-hidden.js)

Page Visibility API only. When the tab becomes hidden it holds the game (`controller.hold("hidden")`); when visible again it releases and, only if a running game was really paused, shows a one-line note "Paused while the tab was hidden" for 5 s (fixed pill, click to dismiss, `role="status"`). A tab opened in the background starts held. Nothing about the hidden time is stored, so nothing is caught up.

Setting: one on/off per game in `localStorage` as `<gameId>-pause-hidden` ("on"/"off", default on), the same on/off shape the games' `settings.js` toggles use. The game's settings panel carries `<label class="settings-checkbox-label" for="pause-hidden-checkbox"><input type="checkbox" id="pause-hidden-checkbox" checked> ...</label>`; the script wires the checkbox and the panel's `#settings-reset-button`. Off restores the old behaviour exactly (the browser throttles the timer of a hidden tab but it keeps running).

Wiring: games on `time-controls.js` need only `<script src="../../shared/pause-hidden.js" data-game-id="sol"></script>` after it. A game with its own clock uses `data-manual` and `NoyvjPauseHidden.init({gameId, hooks: {pause() {...; return true}, resume() {...}}})`; `pause()` returns whether it stopped something that was running (Continuum does this with `set_speed(0)` and restores the speed).

Interplay with away reports: a report that counts game ticks is unaffected (no ticks run while hidden or paused), so hidden time adds nothing to it; SOL's A5 report is tested for exactly this.

### Per game (what was wired)

SOL, Canopy, Trade Empire: both scripts, the stylesheet, `#time-controls`, the settings checkbox, `_start_tick_loop()` in `game.py`, the stage-bar zone and hints in `pc-config.json` (Desktop page regenerated). Continuum: `pause-hidden.js` in manual mode and the settings checkbox. Tide: nothing (turn based).

---

## 11. Run codes (`shared/run_code.py`, `shared/run-code.js`, TODO FY-7)

One short text a player can send a friend: "this seed, this mode, this result". Built once here for Loop GH-28 and H-7, Tide D-3, Grid C-29 and the friend ties of FY-55; nothing is wired into a game yet. The Python and JavaScript sides are the **same algorithm**, pinned together by `shared/tests/test_run_code.py` (pinned codes, byte layout, every refusal) and `shared/tests/test_run_code_browser.py` (300 encodes, 1,500+ decodes of valid, mangled, foreign and forged codes, and 1,000+ describe lines agree exactly; plus both UIs). **A deliberate change to the format must bump `FORMAT_VERSION` and re-pin both tests**, because shared codes would otherwise change meaning.

### The code

`RUN-TIDE-7G0F4-1JE0H-M62WK-4Y8G0-630-EPX`: the word `RUN`, the game's seed prefix (`prefix_for`: `trade-empire` becomes `TRADEEMPIRE`), the packed body in groups of five, and a three-character checksum. Body characters are Crockford base 32 (`0-9 A-Z` without `I L O U`). The body is bit-packed bytes:

| bytes | meaning |
|---|---|
| 1 | `version<<5 | has_seed<<4 | has_result<<3 | stat_count<<1 | 0` (version 1, 0 to 2 stats; the last bit is reserved and must be 0) |
| 4 (if seed) | the seed's five characters as a base-31 number (`seed.py`'s alphabet), big-endian |
| 1 + n | mode length 0 to 8, then the mode: lower-case `a-z0-9` |
| varint (if result) | the score, then each stat, LEB128 little-endian, canonical (no trailing zero group), each 0 to `MAX_VALUE` (2^48 - 1) |

The checksum is 15 bits of FNV-1a 64 over `run-code-v1|PREFIX|BODY`. It exists to catch **typing mistakes**, not to prove anything: every single-character slip in the pinned code is caught, and anyone can still write a code with any score. Longest possible code: 74 characters without dashes (`MAX_COMPACT_LEN` is 80); pasted text over 400 characters is refused without being read.

**What can be in a code:** the game, a seed, a mode token, a score and up to two whole numbers. Nothing a player typed, no name, account, address or id. A game with decimal scores stores them scaled (tenths as integers); what each of the two stats means is the game's own fixed order (for example storms survived, then calm days).

**Scores are client-trusted.** A decoded code is data to *display*. It is never executed, never saved as the viewer's own progress, never ranked, and every decoded result says `verified: false`. Both UIs say so in words ("Run codes are not checked against a server: anyone can write one with any result, so treat it as a friendly challenge, not proof."). There is no comparison or "you did worse" wording anywhere: it shows their run, nothing else (PLAYER-PROFILE: optional social, never worst-score shaming, never pressure).

### API (same names; Python snake_case, JavaScript camelCase)

| Python (`run_code`) | JavaScript (`NoyvjRunCode`) | notes |
|---|---|---|
| `encode(fields)` | `encode(fields)` | `fields`: `game` (required), `seed`, `mode`, `score`, `stats`. Returns the code; raises `RunCodeError` (a `ValueError`) in Python and a `RangeError` named `RunCodeError` in JavaScript, both with `.reason`: `game`, `seed`, `wrong-game` (seed of another game), `mode`, `score`, `stats`. A seed may be typed loosely (`k7f2q`), the mode in any case |
| `decode(text, game=None)` | `decode(text, game?)` | never raises. `{ok, error, message, code, game, seed, mode, score, stats, has_result / hasResult, verified: False}`. `error` is `""`, `empty`, `too-long`, `format`, `version` (made by a newer game), `checksum` (typing mistake) or `wrong-game` (only when `game` is passed); `message` is ready to show |
| `validate(text, game=None)`, `is_valid`, `normalize` | `validate`, `isValid`, `normalize` | like `seed.validate`: `{ok, code, error, message}`, a bool, the canonical spelling or `""` |
| `describe(decoded, options)` | `describe(decoded, options)` | the display line: `Their run: 4,210 pts, 3 storms, 12 calm days, Hard mode`. Options: `prefix`, `unit`, `stats` (one entry per stat: a label string, or `{one, many}`), `modes` (token to display name) |

`decode` forgives case, spaces, line breaks, odd dashes and underscores, **missing dashes when `game` is given** (the prefix is then known), and the look-alikes `O` for 0 and `I`/`L` for 1. The returned `code` is always the canonical spelling, so `normalize(normalize(x)) == normalize(x)`.

### In a game

The Pyodide games write the module next to `seed.py` (it needs it for the alphabet, prefix rule and hash), exactly as for the seed:

```js
for (const f of ["seed.py", "run_code.py"]) {
  const src = await (await fetch("../../shared/" + f)).text();
  pyodide.FS.writeFile(f, src, { encoding: "utf8" });
}
```
```python
import run_code
code = run_code.encode({"game": "tide", "seed": state["seed"], "mode": state["difficulty"],
                        "score": final_score, "stats": [storms_survived, calm_days]})
ghost = run_code.decode(pasted_text, "tide")        # ok / error / message, then ghost["score"], ghost["stats"] ...
```

Run-end screen and new-game or friends screen (JavaScript; the file stands alone, no `seed.js` needed):

```html
<div id="run-end-code"></div>  <div id="friends-ghost"></div>
<script src="../../shared/run-code.js"></script>
```
```js
const ghostLine = { unit: "pts", stats: [{ one: "storm", many: "storms" }, "calm days"], modes: { hard: "Hard" } };
NoyvjRunCode.mountCopy("#run-end-code", {
  game: "tide", describe: ghostLine,
  getRun: () => ({ seed: runSeed, mode: difficulty, score: finalScore, stats: [storms, calmDays] }),   // read on mount, update() and every click
});
NoyvjRunCode.mountPaste("#friends-ghost", {
  game: "tide", describe: ghostLine,
  onView: (ghost) => { /* optional: remember it for a later "ghost" overlay; it is only data */ },
  onPlaySeed: (seed, ghost) => startRun(seed),     // optional: the "Play this seed" button exists only when the code has a seed AND this is given
});
```

`mountCopy` returns `{update(run), destroy(), element}`: a `role="group"` with the code in a selectable box, a 44 px "Copy run code" button, a "A friend will see: ..." line (so the player sees exactly what is shared), the not-verified note and a polite live status (`✓ Copied RUN-...`; if the browser refuses the clipboard, a selected read-only box and "press Ctrl+C"). A run that cannot be encoded (a negative score, three stats) disables the button and says why with a leading `!`. `mountPaste` returns `{setValue, focus, clear, destroy, element}`: a labelled field (placeholder `RUN-TIDE-...`), a bad code is explained in text with a leading `!`, a dashed 3 px border, `aria-invalid`, a `role="alert"` message and focus back on the field; a good one shows a "Ghost run" card (`role="status"` region: the describe line, the seed, the not-verified note, Clear). Everything is written with `textContent`. Light and dark tokens (`--nrc-*`, following `html[data-theme="light"]` and the OS preference), no transitions under reduced motion (`prefers-reduced-motion` or `html[data-reduced-motion="true"]`), every control at least 44 px, fits 360 px without sideways scrolling. Nothing touches the network or storage. Wiring each game's end screen and friends screen is a later step.

---

## 12. Goals panel (`shared/goals-panel.js` + `.css`, TODO FY-53)

"Three goals at all times" (PLAYER-PROFILE: get X to level N to unlock Z, always visible, never pressure) for the idle and tycoon games. The **game owns every rule**: it supplies a queue of goals and says how far along each is and whether it is done; the panel shows at most three, with a progress bar plus text, and promotes the next when one finishes. Tests: `shared/tests/test_goals_panel_browser.py`. Nothing is wired into a game yet (SOL, Trade Empire, Continuum and Loop come next).

### Goal data (a function returning a list, or a plain list)

```js
{ id: "smelters",                     // string, unique, stable
  label: "Reach 5 Smelters",
  current: 3, target: 5,              // or progress: {current, target}; no target = a plain tick (no bar)
  reward: "Unlocks the Foundry",      // optional text; shown as "Reward: ..."
  done: false }                       // optional; if absent, derived from current >= target
```

The visible goals are the **first three that are not done, in the order given**, so the game orders its own queue (the "next thing to unlock" first). `current` is clamped to `target` for display. Unusable entries (no id or label) and duplicate ids are skipped; if `getGoals()` throws or returns something that is not a list, the panel hides rather than breaking the game. A goal the game never lists is never shown; the panel never invents, reorders or completes anything.

### Mounting

```html
<link rel="stylesheet" href="../../shared/goals-panel.css">   <!-- optional: the script links it itself -->
<div id="goals"></div>
<script src="../../shared/goals-panel.js"></script>
```
```js
const goals = NoyvjGoals.mount("#goals", {
  game: "sol",
  getGoals: () => currentGoals(),            // or goals: [...]; called on every refresh()
  title: "Goals",                             // optional
  onChange: (visible) => {},                  // optional, only when what is shown really changed
});
goals.refresh();                              // after the game's state changes: cheap, updates in place
```

`mount` returns `{refresh(), setEnabled(on, {persist}), isEnabled(), focus(), visibleIds(), destroy(), element}`. `refresh()` is safe to call every tick: it updates the existing list items in place (a screen reader's position and any animation survive) and calls `onChange` only when the visible goals or the done count changed. Code that cannot hold the handle can fire `document.dispatchEvent(new CustomEvent("noyvj-goals-change", {detail: {game: "sol"}}))` (the `game` is optional) or call `NoyvjGoals.refreshAll()`.

**Settings switch.** `goals.setEnabled(false)` hides the panel; the choice is remembered per game in `localStorage["noyvj-goals:<game>"]` (`"on"`/`"off"`, default on, blocked storage tolerated; `{persist: false}` skips it, and `opts.enabled` overrides the stored value at mount). `onEnabledChange(on)` fires on a real change. Goals that finish while it is off are not announced when it comes back. For the settings panel: `NoyvjGoals.bindCheckbox(goals, "#goals-checkbox")` sets the checkbox from the panel and keeps them in step (it returns an unbind function), the same on/off shape as the pause-when-hidden switch.

**When it hides.** No goals at all, or switched off: the whole panel is `hidden`. All goals done: it stays with "✓ Every goal is done. Nice work." and "N of N done".

### Behaviour and accessibility

- A `<section>` named by its title; the goals are a real `<ul>` of `<li>`, each reading as one sentence: `Reach 5 Smelters: 3 of 5` then `Reward: Unlocks the Foundry`. The bar is `aria-hidden` (the numbers are already text) and has a visible outline; each goal has a marker glyph (`▸`); nothing is conveyed by colour alone.
- **Completion.** The first paint is silent. When a goal that was not done becomes done, one visually hidden `role="status"` `aria-live="polite"` region says "Goal complete: Reach 5 Smelters. Reward: Unlocks the Foundry. New goal: Reach 10 Furnaces." (several at once are joined; the last one says "Every goal is done."), and a visible, non-live note "✓ Done: ..." stays under the list until the 44 px dismiss button is pressed or another goal finishes. The announcement is made whether or not motion is reduced.
- **Motion** only when neither `prefers-reduced-motion` nor `html[data-reduced-motion="true"]` asks for none: the bar eases to its width and a newly promoted goal does a 0.4 s fade-in. No timers, countdowns, intervals or frame loops anywhere (the test counts them: zero), and no urgency wording.
- The only interactive control is the dismiss button (44 px). The section has `tabindex="-1"` and `goals.focus()` so a game can move focus to it from a help or shortcut. Light and dark tokens `--ng-*` on `:root` (following `html[data-theme="light"]` and the OS preference), a blanket `[hidden]` rule, fits 360 px, about 60 px per goal. Text is always written with `textContent`.

### Adoption: a Python game exposes a function, a few JavaScript lines mount it

Pyodide games (SOL, Trade Empire, Continuum, Loop) keep the rules in Python. Add one function that returns the **whole ordered queue** from the game's own state (the panel picks the first three open ones):

```python
import json

def goals_json():
    s = state()                                           # the game's own state accessor
    return json.dumps([
        {"id": "smelters", "label": "Reach 5 Smelters", "current": s.smelters, "target": 5,
         "reward": "Unlocks the Foundry", "done": s.foundry_unlocked},
        # ... the queue, ordered by what the game wants the player to do next
    ])
```
```js
const panel = NoyvjGoals.mount("#goals", {
  game: "sol",
  getGoals: () => JSON.parse(pyodide.runPython("goals_json()")),
});
// in the game's existing "state changed" or render hook:
panel.refresh();
// settings panel: NoyvjGoals.bindCheckbox(panel, "#goals-checkbox")  (add the checkbox next to the game's other toggles)
```

Per game, the later wiring step only has to decide the queue (examples, not decisions: SOL, the next building or research tier; Trade Empire, the next route, post or charter perk; Continuum, the next era requirement or civic target; Loop, the next unlock), put `<div id="goals">` where it is always visible (the stage bar or HUD), add the include lines, a settings checkbox and, for the Desktop boot, the new element id in both `index.html` and `pc.html` (`shared/tests/test_pc_games.py` checks that). Every goal should map to something the game already measures, so what the player sees always counts toward a visible stat.

## Warm night colours (`shared/night-mode.js` + `.css`, TODO QI-52)

Opt-in, off by default. "Warm night colours after 10pm: the hub and games shift to a dimmer, warmer palette automatically." One fixed, `aria-hidden`, click-through overlay multiplies the whole page by a warm amber (`mix-blend-mode: multiply`), so a game needs no CSS and no game colour is edited. Modes: `off`, `auto` (on between 22:00 and 06:00 by the device clock; the window wraps midnight and can be changed) and `on`; strengths `soft`, `medium` (default), `deep`. The tint is switched off for `prefers-contrast: more` and forced colours. Stored per browser in `localStorage["noyvj-night:mode"]` and `["noyvj-night:level"]`. The clock is read on load, when the tab becomes visible, on `pageshow` and on focus; there are **no timers** (a page left open through 10pm shifts when you come back to it). Tests: `shared/tests/test_night_mode_browser.py` (14). Not wired into the hub or any game yet.

```html
<link rel="stylesheet" href="../../shared/night-mode.css">   <!-- optional: the script links it itself -->
<script src="../../shared/night-mode.js"></script>
<div id="night-settings"></div>
<script>NoyvjNight.mount("#night-settings");</script>        <!-- or NoyvjNight.bindSelect("#my-select") -->
```

`window.NoyvjNight`: `getMode()/setMode(m)`, `getLevel()/setLevel(l)`, `isActive()`, `isNight(date?)`, `configure({start, end, now})`, `apply()`, `mount(container, {title})` (two selects plus a polite status sentence, 44 px controls), `bindSelect(select, {level})`, `onChange(fn)` (returns an unsubscribe function). `html[data-night="on|off"]` and `html[data-night-level]` are set, and a `noyvj-night-change` event fires on `document` once per real change. Text is written with `textContent` only.

## Half-asleep ("calm") mode (`shared/calm-mode.js` + `.css`, TODO QI-51)

Opt-in, off by default (`localStorage["noyvj-calm"]`). "Large buttons, dimmed screen, calm games only, one-handed layout." While on, `html[data-calm="true"]` makes buttons and controls at least 56 px tall with slightly bigger text, stops all motion, dims the screen with a fixed click-through black layer (never a CSS `filter`, which would break fixed children) and offers a thumb dock and a calm-only list filter. Tests: `shared/tests/test_calm_mode_browser.py` (16). Not wired into the hub or any game yet.

`window.NoyvjCalm`: `isOn()/setOn(b)/toggle()`, `getHand()/setHand("right"|"left")`, `setDock([{id, label, onClick}])` (a fixed bottom bar of up to four 64 px buttons, shown only while calm is on; the game passes its main actions; `clearDock()`), `filter(container, {itemSelector, getTags, calmTags, note})` (hides items that are not calm while on: an item is calm when its tags include one of `calmTags`, default `["calm"]`, read from `data-tags` or `getTags(node)`, or it has `data-calm="true"`; it only un-hides what it hid; returns `{refresh, shown, total, destroy}` and shows "Calm games only: showing N of M."), `CALM_GAMES` (a suggested starting list of calm slugs for the hub), `mount(container, {title})` (labelled switch, hand select, a plain list of what changes), `bindCheckbox(checkbox)`, `onChange(fn)` (returns an unsubscribe function), and a `noyvj-calm-change` event. Contrast-more users get no dim. Adoption notes: a game's dock needs only `NoyvjCalm.setDock([...])` once; the hub marks cards with `data-tags` and calls `NoyvjCalm.filter("#game-grid", {itemSelector: ".title-card"})`. Both new files still need adding to `sw.js`'s precache list when whoever owns that file next edits it (until then they load from the network, which fails soft offline).
