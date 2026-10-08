# Signal

Seed: `planning/signal-plan.md` (including its "Decisions (2026-09-27, from Round 3 answers)" section). Built 2026-09-27. Not tied to any BCM assessment. Fun over teaching: nothing here teaches anything.

## One-line pitch
A five-minute daily deduction puzzle in a retro radio room: hidden transmitters broadcast on a grid, you can only listen at a few tiles, and each listen returns the *sum* of every transmitter's signal there.

## Concept
Each ping on a tile returns ONE number: the sum over all transmitters of `max(0, radius - manhattan_distance)`. A reading of 5 could be one close transmitter or several far ones; the "aha" is when two readings clip together. You get a small ping budget, then mark the exact tiles of every transmitter and commit (one answer, exact match to win). Same board for everyone each UTC day; every past day stays playable in an archive that never touches your streak; an endless practice mode generates fresh puzzles from shareable codes.

## Stack (deliberate structure, not a default drift)
- **Pyodide Python, no plain-JS exception.** `game.py` is the ENGINE and holds every rule: the seeded generator, the constraint solver, par, scoring, streaks, achievements, share text, save/merge/validation. It never touches the DOM.
- **`app.js` is glue only** (draws the view the engine returns, forwards taps as JSON, loads Pyodide lazily, queues early taps). `index.html` is a static shell that is readable and tappable with no script beyond that.
- Because the engine has no DOM, the older games' fake-DOM harness (`tests/fakes.py`) is not needed: `tests/conftest.py` loads `game.py` once and resets it per test through the `g` fixture. JS is not unit-tested (no Node here); it is verified live (below).
- Runs from any static server (`python -m http.server`), like every game. No build step.

## How the pieces fit
- `handle(json) -> json` is the engine's one entry point (`open`, `practice`, `ping`, `mark`, `clear_marks`, `commit`, `give_up`, `share`, `settings`, `stats`, `achievements`, `boot`, `reset`, ...). The response carries a full `view` (board, pings with level/fill/glyph, marks, shading, status, result, stats, presets, settings), newly earned achievements, `events` (leaderboard reports) and a `dirty` flag. The true transmitters are only in the view once the puzzle is finished.
- `get_state()` / `load_state(data)` are the shared save-widget contract. `load_state` MERGES (never replaces): days are unioned per key (finished beats in-progress, a daily beats an archive replay, a win beats a loss, fewer pings beats more, commutative), earned achievements are unioned, practice counters take the larger value, settings come from the save, and junk is dropped field by field. Streaks/stats are recomputed from `days`, never trusted from the blob. After a load it calls `window.signalOnStateLoaded()` so the page redraws.
- The saved-state view without the engine: app.js keeps `localStorage["signal:state"]` (last `get_state()`) and `["signal:lastview"]` (last engine view). A returning player's board, readings, result and the archive calendar paint from those before Pyodide exists. Taps made meanwhile are queued and replayed in order (engine is deterministic; tested).
- Browser-level display prefs (text size, reduced motion, high contrast) live in `settings.js` + localStorage, deliberately not in the save.

## Core constraints (do not violate without asking)
1. A puzzle is a pure function of `(seed version, UTC date, mode)`; practice puzzles of `(preset, code)`. No backend, no fetch for puzzles, works offline once Pyodide is cached.
2. Past daily puzzles are frozen: `tests/fixtures/daily_v1.json` pins 365 days x 2 modes. Any intentional generator change must bump `SEED_VERSION` to `v2` and regenerate the fixture (`tests/make_fixture.py`).
3. No timers in play. The clock is read only on load and when the page becomes visible again (rollover). The "next puzzle in" line is computed on render, not ticked.
4. Never colour-only feedback: every reading is a number AND a bar glyph AND a fill height; marks are a diamond glyph; ruled-out tiles are hatched; results use words and symbols. Colour is decoration.
5. Only a first ping on a puzzle's own UTC date makes it a daily. Archive and practice never touch streaks (tested).
6. Share text contains no positions and no per-tile numbers (tested).
7. Fully keyboard playable and playable at 360px wide.
8. No account required; signing in only adds cross-device sync and the opt-in leaderboard.

## Rules as built
| Preset | Board | Transmitters | Radius | Min spacing | Pings | Daily? |
|--------|-------|--------------|--------|-------------|-------|--------|
| Easy | 9x9 | 2 | 4 | 3 | 8 | yes (shading assist on by default) |
| Hard | 9x9 | 4 | 4 | 2 | 9 | yes (no assist) |
| Wide | 13x13 | 4 | 5 | 3 | 12 | practice only |
| Big Sky | 15x15 | 5 | 6 | 3 | 14 | practice only |

Transmitters never sit on the outer ring. **Par** = pings a deterministic greedy solver (centre opener, then the tile that best splits a sample of the still-consistent sets) needs to leave exactly one consistent set. A puzzle is accepted only if par <= budget - 2. Par is an upper bound on the true minimum, so beating it is possible (that is the Under Par achievement).

Deviations from the plan, and why:
- **Budgets and radius are set from measured par, as the plan required**, not the plan's original numbers. Non-adaptive "reference sequences" needed 8-13 pings even for 2 transmitters, so par uses an adaptive greedy solver instead (measured par: Easy 3-6, Hard 5-7, Wide 6-10, Big Sky 8-12). Hard's plan budget of 8 became 9 because par 7 occurs on ~59% of days and needs slack; Easy became 8 (plan: 10) because par is 4-5.
- **"Overlap = a reading of 9+" from the plan is impossible** with spacing 3 and radius 4 (two fields can add to at most 5). It is now "a reading stronger than any single transmitter can give" (reading > radius).
- **Wide and Big Sky are NOT daily at launch.** See timings; the desktop numbers would allow Wide, but there is no phone measurement, and the UI (mode tabs, calendar) is two-daily-mode. Turning Wide daily later = `daily: True` in `PRESETS` plus tab/calendar UI.
- **Custom size/transmitter/budget practice is not built**; practice uses the four presets. (Plan said "or sets size, transmitter count and ping budget"; this needs code-format design for shared codes.)
- **Share glyph**: the plan's lightning bolt is kept in the header; ASCII fallback is `.:+#`.
- **18 achievements**, not 14: the plan's 14 numbered items expand to 16 (item 5 is three streak badges) plus two for the archive/practice/big-board modes the plan's milestone 9 asked for.
- `settings` in the save holds only game-rule prefs (`mode`, `assist_shading`, `ascii_share`, `last_preset`); display prefs are browser-level (see above).
- "New Game" on the shared opening screen does not wipe local progress (a daily game's streak should not vanish on a menu click); erasing is Settings > "Reset all Signal progress" behind a confirm.

## Timings (recorded 2026-09-27; desktop Chrome-based browser pane on the dev machine; NOT measured on a phone)
| What | Result |
|------|--------|
| Static shell ready (DOMContentLoaded) | ~0.01-0.03 s |
| First paint | not measurable in this embedded browser (no paint entries) |
| Engine ready, **cold** (very first visit, nothing cached; one run) | ~4.4 s from navigation start (Pyodide finished at ~4.3 s) |
| Engine ready, **warm** (Pyodide in the service-worker/HTTP cache) | ~0.82-1.0 s, five runs |
| First ping, warm, tapped before ready (queued) | applied at ~0.82 s |
| Pyodide files in `sw.js` cache-first cache | verified: `pyodide.js`, `pyodide-lock.json`, `pyodide.asm.js`, `pyodide.asm.wasm`, `python_stdlib.zip` all present after one visit |
| Generation in Pyodide, avg / p95 / max | Easy 10 / 12 / 12 ms (n=30); Hard 55 / 98 / 166 ms (n=30); Wide 98 / 274 / 274 ms (n=8); Big Sky 334 / 783 / 783 ms (n=5) |
| Generation, CPython 3.9 (pytest), 365 dailies | Easy avg 7 ms max 13 ms; Hard avg 35 ms p95 63 ms max 130 ms; Wide avg 125 ms max 680 ms (n=60); Big Sky avg 0.58 s max 5.1 s (n=25, sample 200; presets now use sample 100) |
| UI round trip for "New puzzle", 4 runs each | Wide 68-143 ms, Big Sky 158-774 ms, Hard ~30 ms, Easy ~10 ms |

The plan's reopen criterion for the JS-port decision is "warm time to first ping worse than ~3 s on a mid-range phone". Desktop warm is ~0.9 s; a phone is unmeasured, so **that check is still open**. Cold first visit is the honest weak spot (~4-5 s on desktop before the first ping works; the board is usable meanwhile and taps queue).

The service worker is stale-while-revalidate, so a new `game.py` reaches a returning player one visit late.

## Leaderboard
Opt-in board `signal / best_streak` (higher is better; the player's longest daily streak in any mode, reported after each daily win). The backend needs (in `app/leaderboards.py`):
```python
    ("signal", "best_streak"): {
        "order": "desc", "low": 1.0, "high": 100_000.0, "label": "Longest daily streak (days)",
    },
```
Until that is deployed, `GET /leaderboards/signal/best_streak` returns 404 and the disclosure shows "unavailable" (fails soft). Similarly `GET /stats/games/signal` 404s until `signal` is in `app/stats.py` `STATS_FIELDS` (suggested: `"signal": ("stats.easy.best_streak", "stats.hard.best_streak", "stats.easy.played", "stats.hard.played")`, all present in `get_state()`); the achievements panel's "% of players" line then fills in.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Generator + solver (Python) | mulberry32/FNV-1a, spaced placement, constraint solver (brute-force cross-checked), adaptive-greedy par, uniqueness, frozen 365x2 fixture, per-preset timing ceilings | Done |
| 2 | Static shell + engine bridge | Static HTML shell, lazy Pyodide load, queued taps, saved-state paint without the engine, cold/warm timings, Pyodide cache check | Done (phone timing still open) |
| 3 | Playable board | Grid, ping, number+glyph+fill readings, waterfall, budget, mark + commit, win/lose reveal, assist shading | Done |
| 4 | Daily loop + stats | UTC rollover, daily-vs-archive rule, stats + histogram, streaks derived from `days`, localStorage persistence | Done |
| 5 | Share + hard mode | Spoiler-free share (+ ASCII), Hard, mode tabs, per-mode stats | Done |
| 6 | Archive | Month calendar with per-mode status, archive play, separate bucket, future-date refusal | Done |
| 7 | Endless practice + bigger boards | Practice with shareable `P-Xxxxxx` codes, Wide and Big Sky presets, budgets from measured par | Done (custom size not built; Wide/Big Sky practice-only by decision) |
| 8 | Save + settings | Save-widget contract with merge + strict validation, settings panel (text size, reduced motion, high contrast, theme, assist, ASCII share, reset), confirm dialogs | Done |
| 9 | Achievements + changelog | 18 achievements + panel/toast, changelog panel, 4-step tutorial, about panel | Done |
| 10 | Polish + hub integration | Light theme, keyboard + mobile audit, favicon, flavour text (~40 lines), leaderboard include, feedback prompt | Done in-game; **hub registration (title card, manifests, game-added/last-updated, backend board) is the log owner's job** |
| 11 | Desktop boot (PC version plan): `pc.html` generated from `index.html`, board as the stage, readout chips, side column, windows, Desktop tutorial, layout switch on the opening screen | Done (2026-10-07); see "Desktop boot" below |

## Verification
- `cd games/signal && python3 -m pytest -q` (see the dev log entry for the exact count) and `python3 -m flake8 game.py tests --extend-ignore=E501`.
- Live checks via `hub-dev-server` (port 8073), `index.html#play`: a full puzzle played through the UI (pings, marks, commit through the confirm dialog, share), archive calendar (with a mocked clock), practice codes, queued taps before the engine was ready, keyboard (arrows, Enter, Space, jump-by-letter, `?`, Esc), light theme contrast, 360px layout (docked action bar, big board scrolls horizontally), console clean apart from an expected 404 from backend routes that do not exist yet (above).

## Working conventions
- Commit + tag per milestone (`git tag signal-milestone-0N`); update the Status column as you go.
- Flavour lines (`_LINES` in `game.py`, ~40) are a first draft awaiting the user's tone veto.
- Open: phone timing; whether Wide should become a daily mode; custom practice sizes; a "what if I ping here" hint is deliberately NOT built (it would trivialise the deduction).

## Desktop boot (PC version, 2026-10-07)

`games/signal/pc.html` is the Desktop boot: the same `game.py`, `app.js`, saves and `game_id` as the Classic page, in a full-window layout for wide windows with a mouse. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py` (a test fails if it is stale). No rule, state or save change, and `game.py` and `app.js` are untouched. The only Classic edits are the `shared/layout-pref.js` tag and `GameTutorial.init(window.SIGNAL_PC_TUTORIAL_STEPS || SIGNAL_TUTORIAL_STEPS, ...)`. The static first paint and queued early taps behave exactly as in Classic (verified live: a tap made before the engine is ready is queued and replayed).

- **Layout.** Top bar: back link, title, four icon buttons (Archive, Stats, Achievements, Settings) and the Menu (also opened by Esc). Under it, readout chips mirroring `#session-line` (puzzle), `#pings-text`, `#par-text` and `#marks-text` (the originals move into a hidden holder and keep updating). The stage is the board, the largest square that fits the window height (`pc.css` uses a size container, so Easy/Hard 9x9, Wide 13x13 and Big Sky 15x15 all keep square tiles), with the mode tabs (Easy / Hard / Archive / Practice) and the "receiver warming up" line above it, the message line below it and a hotkey bar (arrows, Enter, Space, D4 jump, ?, Esc). The side column holds the practice controls (only in practice), the Ping/Mark tool toggle, the ping dots, Commit / Clear / Give up, the readings and the result panel with the share button.
- **Windows.** How to Play, Archive, Stats, Achievements, What's New, Settings and About Signal are windows. Composite windows opened from the Menu: Community leaderboard (the shared opt-in mount) and Was Signal fun? (feedback). The tagline is hidden (it is on the opening screen).
- **Tutorial.** `pc.js` holds `SIGNAL_PC_TUTORIAL_STEPS` (8 steps: chips, board, readings, tool toggle, commit, Menu). It also replaces `window.MobileDock` with an inert stand-in, so resizing the window below 640px never lifts the answer buttons out of the side column.
- **Notifications.** `notify` is null: Signal has no log list. Achievement toasts use the game's own top-centre toast.
- **Known limits.** At 1024x700 the practice controls wrap onto three lines in the narrow side column and Big Sky tiles are about 22px. Right-click and Shift+click (mark) work as in Classic but are not hotkeys, so they are not in the hint bar. Phones and narrow windows are meant to use Classic.

## Shared touch targets (Z-23, 2026-10-08)

`shared/touch-targets.css` makes buttons at least 44px tall on phones. A 9x9 board cannot have 44px cells on a 360px screen, so `app.js` marks every `.cell` button with `data-touch-exempt` and the shared rule skips it. Everything else (toolbar buttons, mode tabs, Commit / Clear / Give up, the tool toggle) follows the 44px rule.

- **Oct 8 wiring (Z-27, Y-7, Y-8, Y-29):** Signal keeps its own share text (`lastShareText` in `app.js`) and does NOT use `shared/copy-result.js`. `shared/copy-result.js` is loaded only so the achievement Share helper can use its clipboard fallback. `shared/achievement-share.js` adds Share to earned achievement cards (the cards already carry `data-achievement-id`). The Open Graph block and JSON-LD sit in `<head>` before the shared includes; a `#credits-link` anchor sits above the ad bar (in the Desktop Help menu via `pc-config.json`). Tests: `tests/test_wiring_oct8.py`.
