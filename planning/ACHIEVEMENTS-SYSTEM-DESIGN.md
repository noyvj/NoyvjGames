# Achievements System Design — Game Hub

Design doc for a hub-wide achievements framework: 5-30 achievements per game, a per-game in-game panel, and a hub-level dashboard aggregating progress across every game that has them. Written against the existing stack (Neon/Postgres via FastAPI Cloud, static GitHub Pages front end, Pyodide-run Python games, the existing save-code + accounts system).

Status: **Framework designed and built, SOL is the reference integration — 2026-09-14.** SOL ships 18 real achievements, its own in-game panel, and the hub-level aggregate dashboard. The other 11 games (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift, Le Champ de Mots, Trade Empire, Continuum) are still pending — §7 below is the *technical* checklist for how to roll this out to each; the actual per-game tracking (what's done, what's next) now lives in `planning/TODO.md`'s "roll achievements out everywhere" section, not here, so there's one place tracking progress rather than two. Le Champ de Mots technically shipped *a* game-local achievements slice first (its own Milestone 23, "derive, don't track"), but that was scoped to that game only, with no manifest file and no hub-dashboard wiring — this doc formalizes and extends that same instinct into the cross-game shape it was explicitly deferred from being at the time.

---

## 1. Core design decision: where earned status lives

The hub already has a save-code + accounts system that every game plugs into via `shared/save-widget.js`: each game exposes `get_state()`/`load_state()`, the widget POSTs `get_state()`'s return value to `/saves`, and a signed-in account's saves are all readable at once via `GET /users/me/saves` (`app/models.py`'s `Save` model: `{id, save_code, game_id, save_data, user_id, created_at, updated_at}`).

**Decision: achievement-earned status rides this exact mechanism as one new field inside each game's own `save_data`, never a new backend table or endpoint.**

- Each game's `get_state()` gains one new top-level key, `"achievements_earned"`: a plain JSON list of achievement-id strings currently satisfied.
- This list is **always freshly recomputed at save time**, never hand-maintained mutable state. A game exposes a pure function (SOL's is `achievement_ids_earned()`) that re-derives the earned set from whatever state the game already tracks, and `serialize_state()`/`get_state()` calls it fresh every time. This is the same "derive, don't track" discipline Le Champ de Mots' own Milestone 23 achievements already established (its whole point was that "currently Automated" and "ever reached Automated" are the same count once stages are monotonic, so no new save state was needed at all) — just formalized here as the rule for *every* game's achievements, not a one-off insight specific to that game.
- On load, `deserialize_state()`/`load_state()` **never reads this key back**. It's a write-only projection of other state that already round-trips normally — reading it back in would risk a save's stale, no-longer-recomputed snapshot silently overriding what the game's real state actually justifies. (Concretely, in SOL: `deserialize_state()`'s big dict of `data.get(...)` fallbacks simply has no line for `"achievements_earned"` — the key is present in every save file but inert on load.)

**Why this design is workable end to end** (checked against the real save/account flow, not assumed):

- A save starts anonymous; `POST /saves/{code}/claim` attaches it to an account. Once claimed, `GET /users/me/saves` returns every save row for that account, across every game, each with its own `save_data`.
- `GET /users/me/saves` has **no `game_id` query filter** today (confirmed by reading `app/main.py`'s `list_my_saves`) — every caller filters client-side. `shared/save-widget.js`'s own signed-in autoload already does exactly this (`saves.filter((s) => s.game_id === GAME_ID)`), so the hub dashboard doing the same for N games is following an established pattern, not inventing a second one. Filtering server-side would be a reasonable future optimization once the accounts feature has real traffic, but isn't needed to ship this.
- "Most recent claimed save for this game" is resolved the same way `save-widget.js`'s autoload resolves it: sort the filtered list by `updated_at` (falling back to `created_at`) descending, take the first. The dashboard reuses this exact sort, not a new one.
- **Zero backend changes were needed or made.** No new table, no new column, no new endpoint. This was confirmed by reading `app/models.py` (`Save.save_data` is already an unstructured JSON blob — a game adding a key to what it writes there requires nothing from the schema) and `app/main.py`'s save endpoints (a `PUT /saves/{code}` already accepts and stores whatever `save_data` dict a game hands it, achievements key included, with no allowlist of accepted top-level keys to update).

## 2. The per-game achievement catalog: `achievements.json`

Each game gets one new static file, `games/<slug>/achievements.json`:

```json
{
  "achievements": [
    { "id": "first_ore", "label": "First Ore", "description": "Mine Iron on Earth for the first time." },
    { "id": "automated", "label": "Automated", "description": "Build Earth's first Auto-Miner — mining without clicking." }
  ]
}
```

- Flat list, 5-30 entries. `id` is a stable snake_case string (never renumbered/reused once shipped — a hub dashboard reading an old claimed save's `achievements_earned` list needs those ids to keep meaning the same thing indefinitely). `label` is the short badge title; `description` is the one-line "how do I earn this" text.
- This is the **single source of truth** for that game's catalog — both the in-game Python code and the hub's own page need to read it, so it has to be genuinely static JSON, not something only constructable from Python (a hand-maintained parallel list in JS would drift from the Python one the moment either changed).

### Loading it from Python

Same convention Le Champ de Mots already established for its own static JSON assets (`games/champ-de-mots/game.py`'s `_read_json_asset()`), reused verbatim in shape for SOL's `_read_achievements_json()`:

1. The page's boot script `fetch()`es `achievements.json` **before** running `game.py`, and sets it as a window global (`window.ACHIEVEMENTS_JSON = achievementsJson`).
2. `game.py` does a deliberately lazy `import js` (guarded by `except ImportError`), reads `getattr(js, "ACHIEVEMENTS_JSON", None)`, and falls back to reading the file straight off disk (`open(os.path.join(here, "achievements.json"))`) when that global doesn't exist.
3. The pytest fake-DOM harness's fake `js` module simply has no such attribute, so tests automatically take the filesystem-fallback path — the module stays importable and testable outside a browser with zero test-only special-casing.

This means every future game adds the exact same three lines to its boot script (fetch + `window.<X>_JSON =` + await it before running `game.py`) and the exact same `_read_json_asset`-style function to its own `game.py` — no new pattern to invent per game.

### Reading it from the hub page

`script.js`'s dashboard does a plain `fetch("games/<slug>/achievements.json")` — a relative path (no leading `/`), which matters: CLAUDE.md's site-level milestone 7 already fixed a hub-wide bug where an absolute root-relative path 404'd under GitHub Pages' `/NoyvjGames/` subpath, and every fetch this feature adds follows that same "always relative" rule rather than reintroducing the bug class.

## 3. In-game UI: a toggle + panel, per game's own visual language

Per the hub's own site-level rule ("Shared shell, free internals... Individual game pages are free to look however they want"), the achievements panel is **not** a shared component — no `shared/achievements-widget.js`. Each game builds its own toggle button + panel in its own CSS, the same way each game already has its own everything-else. What's shared is only the *shape* of the underlying data (the JSON contract above) and the general pattern (a toggle button that shows earned/total, a panel of cards below it).

SOL's own reference implementation (`games/sol/game.py`):

- `ACHIEVEMENT_CHECKS`: a dict of `id -> zero-argument predicate`, each one reading live module state fresh (no caching, no hand-set "earned" flags).
- `ACHIEVEMENT_PROGRESS`: a dict of `id -> zero-argument (current, target)` pair, populated **only** for achievements with a genuine numeric scale-up (e.g. "7 unlocked bodies out of 7", "3 of 4 worlds terraformed"). A one-shot milestone like "build your first Recycler anywhere" gets no progress row at all — a plain earned/not-yet is the honest shape for it, rather than inventing a fake "0 of 1" that reads like a countdown. This mirrors, but doesn't copy, Le Champ de Mots' own panel: that game's achievements are naturally *tiered* (25/50/100/250/500/750 plots automated), so its panel groups each tier into "earned so far (most recent first) + next target"; SOL's achievements are mostly one-shot systems milestones tied to distinct mechanics rather than repeating numeric tiers, so its panel is a flat checklist instead — a **documented judgment call**, not an oversight: match the shape of the panel to the shape of that game's own achievement list, don't force every game's panel into the champ-de-mots tiered-group layout.
- `achievements_summary()`: the catalog in order, each entry annotated with `earned` (bool) and `progress` (the pair above, or `None`). This is the one function both the panel-rendering code and any future summary screen should call — nothing downstream re-derives earned/progress from `ACHIEVEMENTS`/`ACHIEVEMENT_CHECKS`/`ACHIEVEMENT_PROGRESS` directly.
- `update_achievements_display()` is wired into both `tick()` (so a long-running session's panel — if left open — updates live as resources climb, matching how `update_win_display()` already runs every tick) and `_full_render()` (so a fresh load or a save/load round-trip immediately reflects the right earned count), and its toggle button is bound in `setup()` alongside every other button listener.

### A new fake-DOM capability, added once

SOL's game.py had never needed to build DOM nodes dynamically from Python before (every existing panel is static markup in `index.html`, toggled by `.hidden`) — only Le Champ de Mots' farm grid/achievements panel needed that. Achievements needed it here too (a variable-length list of cards), so `games/sol/tests/fakes.py` gained `document.createElement`, `element.appendChild`, `element.children`, `element.className`, and an `element.innerHTML` setter that clears `children` — the same shape Le Champ de Mots' own `tests/fakes.py` already has. This is a one-time addition to SOL's test harness, not a per-achievement cost, and every future game that wants a dynamically-rendered panel (achievements or otherwise) can copy the same small diff to its own `fakes.py` if it doesn't have this capability yet.

## 4. New tracked state, where a game genuinely needs it

Not every achievement is a pure function of already-persisted state. SOL's own catalog needed exactly one new piece of tracked state: **`visited_bodies`**, a set of every world the player has ever actually traveled to.

Why this couldn't be derived from existing state: `current_planet` only remembers *where the player is right now*, and `unlocked_bodies` only means *research has granted travel access* — a player can unlock every Far Body via research and never actually fly to one before returning to Earth. Two achievements ("Off-World", "Grand Tour") are genuinely about having *visited*, not merely unlocked, so there was no existing signal to read.

The pattern for adding new tracked state defensively (demonstrated by `visited_bodies`, and the template for any future game's equivalent need):

1. **A safe default at the module level** — `visited_bodies = {"Earth"}`, so a brand-new game (no save loaded yet) already has correct state.
2. **Mutated only where the real event happens** — each `on_travel_*` handler calls a one-line `_mark_visited(planet)` inside its existing "travel succeeded" branch. No new call sites invented elsewhere; the achievement rides the same code path that already changes `current_planet`.
3. **Added to `serialize_state()`** the same way `unlocked_bodies` already is (a set converted to a sorted list for JSON-safety).
4. **A `.get(key, <current value>)` fallback in `deserialize_state()`**, so a save made before this field existed simply keeps whatever's already live (the fresh-module default, `{"Earth"}`, on a first load) instead of `KeyError`-ing — the exact defensive pattern every other top-level field in SOL's `deserialize_state()` already follows.
5. **A belt-and-suspenders backfill**: after resolving `current_planet` from the save, `visited_bodies.add(current_planet)` unconditionally. This specifically covers an old save (predating this field) that was captured mid-trip — without it, loading a pre-existing "I'm currently on Mars" save would forget Mars was ever visited until the player traveled there again. Small, cheap, and it's the kind of one-line defensive addition this hub's `deserialize_state()` functions already lean on heavily (see SOL's own `CLAUDE.md` post-milestone audit notes for two prior examples of exactly this class of bug).

A future game with an achievement like "played on 5 different days" or "tried every ending" should follow the same five steps: safe default, mutate only at the real event, serialize, defensive deserialize fallback, and (if relevant) a backfill for saves older than the field.

**A second example, caught live rather than at design time:** during this feature's own live-verification pass (§8), a completely fresh, untouched game showed "Governor Appointed" already earned within the first second. The original checker read `governor_tick_count >= 1` — but `governor_tick_count` increments the instant *any* other planet exists to govern, which is true from the very first tick of a brand-new game; it measures ticks elapsed, not the governor having actually done anything. The fix was a second new tracked field, `governor_purchase_count`, incremented only inside `governor_step()`'s own buy branches (a real resource spend, a real building bought) — the achievement now checks that instead. This is exactly the "some achievements will genuinely need new tracked state" case the brief for this feature called out in advance, just discovered by playing the real thing rather than anticipated on paper — worth remembering when designing the next game's catalog: a counter that increments on *time passing* is not the same signal as a counter that increments on *the player (or their governor/automation) actually doing something*, and it's an easy substitution to make by accident.

## 5. Hub-level aggregate dashboard

Lives inside `index.html`'s existing `#account-signed-in` block (root `index.html`, `style.css`, `script.js` — no new files), so it only ever renders for a signed-in visitor; a signed-out visitor sees an added line in the existing sign-in prompt ("Sign in to track achievements across every game and across devices") rather than a second, redundant call-to-action — matching how the rest of that section already degrades (the pre-existing "claimed saves" list is entirely inside the same signed-in/signed-out split).

Data flow (`script.js`'s `loadAchievementsDashboard()`, called from `showSignedIn()` right alongside the pre-existing `loadMySaves()`):

1. **`GAMES_WITH_ACHIEVEMENTS`** — a small hand-maintained JS object, `{ game_id: "games/<slug>/achievements.json" }`. Currently just `{ sol: "games/sol/achievements.json" }`. This is deliberately **not** auto-discovered by probing every game folder for an `achievements.json` that might not exist — that would mean a 404 fetch per not-yet-rolled-out game on every single hub page load, for a rollout that's explicitly staged across many separate future tasks. One line gets added here per game, at the same time that game's own achievements ship.
2. In parallel: fetch every listed game's `achievements.json` (for its total count) and the signed-in user's full `GET /users/me/saves` list (once, shared across every game — not once per game).
3. For each game in the manifest: find its most-recently-updated save (§1's shared sort logic), read `save_data.achievements_earned` (defaulting to an empty list if the save predates achievements, or if there's no save for that game at all), and render a `label: earned/total` progress bar.
4. Sum earned/total across every game actually rendered and render one more bar, "All games", underneath.

**Judgment call — what happens for a game in the manifest the player hasn't saved in yet:** it still renders, as `0/total`. The spec's "must not show as an alarming 0/0" concern is about a game with **no achievements shipped at all** — since the manifest only ever lists games that genuinely have a real catalog, a `0/N` (N > 0) for a game the player simply hasn't earned anything in yet is informative, not alarming, and is arguably useful ("you haven't tried this game's achievements yet"). A game whose `achievements.json` fails to fetch (network hiccup, a typo'd manifest path) is skipped from rendering entirely rather than shown as a fabricated `0/0` — the manifest promises a real catalog exists, and silence is more honest than a made-up total when it couldn't be confirmed this pass.

## 6. Tests

- **SOL** (`games/sol/tests/test_achievements.py`, 35 tests): catalog sanity (id uniqueness, every catalog id has a checker, every progress-fn id refers to a real achievement), nothing earned on a fresh game, every individual achievement earned/not-earned by driving the *real* game systems (clicking, buying, traveling, funding research, ticking the governor) rather than poking synthetic flags, progress readouts, "checking achievements never mutates other game state" (`serialize_state()` byte-identical before/after, modulo the deliberately-always-fresh `achievements_earned` key itself), and the toggle/panel (hidden by default, opens/closes, renders every catalog entry's label+description, marks an earned card distinctly, shows a live progress readout, and stays live across a `tick()`). `games/sol/tests/test_save_system.py` also gained round-trip + defensive-fallback tests for the new `visited_bodies` field and the new `achievements_earned` key in `serialize_state()`'s expected-keys assertion.
- **Hub dashboard (`script.js`)**: **no test coverage was added, and none exists for any of `script.js` today** — confirmed by checking `app/tests/` (backend-only, pytest against the FastAPI app) and searching the repo for any JS test runner config (none: no `package.json`, no `*.test.js` anywhere). The pre-existing accounts UI, save-list rendering, and site-feedback widget this dashboard sits alongside have never had their own test suite either; this change matches that existing (lack of) practice rather than introducing a new one unilaterally for just this feature. If the hub ever adds its own JS test tooling, `loadAchievementsDashboard()`/`renderProgressBar()`/`mostRecentSaveForGame()` were written as small, independently-testable functions specifically so that would be easy to retrofit later.

## 7. Checklist: adding achievements to game N

For each of the remaining 11 games, in order:

1. Design 5-30 real achievements grounded in that game's actual systems (read that game's own `CLAUDE.md` + `game.py`/main content file first — no generic filler). Prefer deriving earned status from state the game already tracks; only add new tracked state where an achievement genuinely can't be expressed otherwise (§4's five-step pattern).
2. Write `games/<slug>/achievements.json` (§2's format).
3. In that game's boot script (`index.html`'s `main()` or equivalent): fetch `achievements.json` alongside the existing `game.py`/catalog fetch, set it as a window global, await both before running the game's Python.
4. In `game.py`: a `_read_achievements_json()`/`_read_json_asset()`-style loader (copy the convention, don't reinvent it), `ACHIEVEMENTS`, `ACHIEVEMENT_CHECKS`, `ACHIEVEMENT_PROGRESS` (only where a numeric target exists), `achievement_ids_earned()`, `achievements_summary()`, a toggle button + panel wired into that game's own render loop and `setup()`.
5. Add `"achievements_earned": achievement_ids_earned()` to that game's `get_state()`/`serialize_state()`. Do **not** read it back in `load_state()`/`deserialize_state()`.
6. If that game's `tests/fakes.py` doesn't already support `document.createElement`/`appendChild`/`children`/`className`/`innerHTML` (check first — several games, including Le Champ de Mots, already do), add it (§3's fake-DOM note has the exact diff shape).
7. Write that game's own `tests/test_achievements.py` — catalog sanity, each achievement driven through real game actions, progress readouts, no-mutation, panel toggle/render — matching that game's existing test-file conventions.
8. Add one line to `script.js`'s `GAMES_WITH_ACHIEVEMENTS` (and `GAME_DISPLAY_NAMES`, if the game_id isn't already a clean display name) — this is the **entire** hub-side change per game; nothing else in `index.html`/`style.css`/`script.js` needs to change per game.
9. Update that game's own `CLAUDE.md` status line and the root `CLAUDE.md`'s achievements-framework note.
10. Commit + tag per that game's existing milestone convention (e.g. `git commit -m "Milestone N: Achievements"` then the game's own tag pattern).

Nothing in this checklist requires touching `app/` (the FastAPI backend) or any other already-shipped game — each game's rollout is fully independent of every other's, which is what makes staging this across 11 separate future tasks safe.

## 8. Event badges data contract (v1, R2-Z23b)

Hub-side display of earned holiday-event badges (e.g. a week-long Christmas event) is built in `script.js` (`renderEventBadges`); the per-game event mechanism (Z23) is separate. A game records a badge as `{ id, label, earned_at }` (`id` = `/^[a-z0-9-]{1,64}$/` slug like `christmas-2026`, `label` <= 60 chars, `earned_at` ISO string <= 32 chars) in either `save_data.event_badges` (an array in its save state, like `achievements_earned`) or the `localStorage` key `event_badges_v1` = `{ "version": 1, "badges": [...] }`. The hub unions both, de-dupes by `id`, ignores malformed entries/unknown versions, and shows an "Event badges" block in the signed-in account area (hidden when empty).
