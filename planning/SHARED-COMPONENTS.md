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
