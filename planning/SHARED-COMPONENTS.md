# Shared components (W-1 level select, W-3 skill tree, W-4 seasonal events)

Three drop-in components for the games, built once. None of them stores anything the game did not hand it (apart from two small per-viewer conveniences named below), none needs a backend, and all of them are tested in headless Chromium and in Python (`python3 -m pytest -q shared/tests`).

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

## Which TODO items these unblock

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
