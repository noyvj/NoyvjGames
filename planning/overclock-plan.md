# Overclock — Groundwork Plan (baseline only)

**Status:** groundwork, pre-build. Written 2026-09-21 from `IMPROVEMENT-IDEAS-ROUND-2.md` section M (item 6) and the user's answers. Save as `games/overclock/CLAUDE.md` (trimmed to concept + milestone table) once Milestone 1 starts.

**This file holds the FULL shared baseline checklist** (section 4). `last-line-plan.md` and `deep-descent-plan.md` reference it by name and list only what differs.

## 1. One-line pitch and genre shape (from round 2)
A roguelike deck-builder: draft a run-specific deck of abilities each attempt, fight through procedurally arranged encounters of escalating difficulty, permadeath-and-retry. Pure build-crafting and combat satisfaction, "this run vs. the last one." Explicitly **fun-first, not teaching** (user, M1/M5 feedback): no climate/educational framing, no "Real Story" lesson content. No BCM tag (personal project, like Le Champ de Mots) unless the user says otherwise.

## 2. Deliberately undecided (deferred to `IMPROVEMENT-IDEAS-ROUND-3.md`)
The user wants "some kind of gimmick that makes this game special" and leans **space or cult**. Neither is chosen. This plan does NOT define cards, energy/mana rules, enemy design, encounter map shape, or the theme. Working title only; the name "Overclock" leans space/tech but is not locked. Open questions for the user:
1. Space or cult (or something else)? This sets tone, palette, favicon glyph and ambient background.
2. What is the one mechanic that makes it not-just-Slay-the-Spire (e.g. a resource that overheats/corrupts, a shared deck between runs, a ritual/sacrifice loop)?
3. Run length target: ~15 minutes (quick, mobile-friendly) or 45+ minutes? Drives whether mid-run saves matter.
4. Meta-progression between runs: unlocks only (new cards), permanent stat upgrades, or none (pure skill)?
5. Story/flavor text on or off by default? (Z11 says players get a story-mode toggle in each game.)

## 3. Stack and technical foundation (mechanics-agnostic)
- **Stack:** Python via Pyodide, plain HTML/CSS, no build step, runs under `python -m http.server`. No deviation planned. Files: `index.html`, `style.css`, `game.py` (may split into `engine.py`/`content.py` later, as Continuum does), `settings.js`, `achievements.json`, `changelog.json`, `content/*.json`, `requirements-dev.txt`, `tests/`.
- **Deterministic seeded RNG module (`rng.py`):** every run gets a `seed`; all randomness (shuffles, rewards, encounter picks) goes through one `RunRNG` object (small pure-Python PRNG such as mulberry32/xorshift, NOT `random` global state, so results are identical across Pyodide versions). `RunRNG` state (`seed`, `draws`) is serialised, so a saved run resumes with the exact same future. Enables replayable/shareable seeds ("daily seed" is a later option) and makes tests exact.
- **Run-state vs meta-state split in `get_state()`:**
  ```
  {"version": 1,
   "meta": {"runs_started", "runs_won", "best_depth", "unlocks": [], "settings_seen": {}, "achievements_earned": [...]},
   "run": null | {"seed", "rng", "turn", "phase", ...}}
  ```
  `run` is `null` between runs; permadeath = set `run` to `None` and fold results into `meta`. `load_state` tolerates missing keys (old saves) and unknown `version`. `achievements_earned` is written in `get_state()` and never read back (per `ACHIEVEMENTS-SYSTEM-DESIGN.md` section 7 step 5).
- **Event/turn loop skeleton:** a tiny phase state machine (`MENU -> RUN_START -> ENCOUNTER -> RESOLVE -> REWARD -> ... -> RUN_END`) driven by explicit `dispatch(action_dict)` calls that return a list of event dicts (`{"type": ..., ...}`). UI renders from state; achievements/logging subscribe to the event list. No mechanics in Milestone 1-7: the placeholder loop is "click Fight, get placeholder reward, advance a counter, die at node N."
- **Content as JSON:** `content/cards.json`, `enemies.json`, `encounters.json` (empty or 2-3 placeholder rows) loaded like `achievements.json`: fetched in `index.html` `main()`, set as window globals, parsed by a `_read_json_asset()` loader in Python. Ids are stable snake_case, never reused. Adding a mechanic later = adding data plus one handler, not restructuring.
- **Rendering:** DOM/CSS, not canvas. Turn-based card UI is text-and-boxes: DOM gives free accessibility (screen reader, focus, text scale), simple fake-DOM testing, and small mobile layouts. Cards are `<button>`s in a hand row. Animation limited to CSS transitions (respects the reduce-motion setting).
- **Pyodide performance:** turn-based, so no per-frame Python. Only concern is initial boot (cold Pyodide load) and keeping `render()` from rebuilding the whole DOM every action; render only changed panels.
- **Persistence caveats:** mid-encounter saves are allowed because the RNG state is serialised; save only at stable phases if that proves fragile (decision deferred to Milestone 2).

## 4. FULL shared baseline checklist (the reference list)
Sources: `shared/` modules, `planning/SAVE-BUTTON-INTEGRATION.md`, `ACHIEVEMENTS-SYSTEM-DESIGN.md`, and finished games (Thaw, Le Champ de Mots) as patterns.

| # | Item | How (existing conventions to copy) |
|---|------|------------------------------------|
| a | Save system | `get_state()` / `load_state()` contract; `<script src="../../shared/save-widget.js">` plus its drop-in HTML block (SAVE-BUTTON-INTEGRATION section 4); `shared/hub-auth.js` loaded before it. Save-code and account save both work automatically. Test: round-trip, old-save tolerance, no mutation on serialise. |
| b | Settings panel | Per-game `settings.js` (text scale + reduce motion, localStorage) modeled on Thaw/Aftermath; toggle button plus panel. Add a story on/off toggle if a narrative layer exists. |
| c | Achievements | `achievements.json` (5-30 entries, ids permanent), Python loader, `ACHIEVEMENT_CHECKS`, in-game panel + toast, `achievements_earned` in state. Hub side: one line in `script.js` `GAMES_WITH_ACHIEVEMENTS` (plus `GAME_DISPLAY_NAMES`), rerun `scripts/generate-last-updated.py` to refresh `game-manifest.json`. Follow the 10-step checklist in ACHIEVEMENTS-SYSTEM-DESIGN section 7. Launch set: ~8 generic ones (first run, first win, N runs, best-depth thresholds). |
| d | Changelog panel | `changelog.json` fetched in `main()`, "What's New" toggle and panel (`#changelog-panel`), same shape as Thaw/Continuum. |
| e | Onboarding tour/tooltips | `shared/tutorial.js`: `GameTutorial.init(STEPS, {gameId})` after Pyodide boot; one STEPS array drives both spotlight walkthrough and read-through "How to Play". Steps target real placeholder UI, rewritten when mechanics land. |
| f | Confirm dialog | `shared/confirm-dialog.js` wrapping destructive clicks (Abandon run, Reset all progress, Load over an active run), with persistent "don't ask again". |
| g | Mobile dock / HUD | `shared/mobile-dock.js` pins the action panel (hand/actions) to the bottom on narrow screens; `shared/mobile-hud.js` mirrors 1-3 key stats (e.g. HP, floor). Test at 375px. |
| h | Colorblind-safety rules | No hue-only encoding: every state (damage/heal, card type, rarity) carries an icon, text label or shape as well as color; pass the same audit written up for the hub shell in root `CLAUDE.md` (no red/green or blue/purple pairs distinguished by hue alone). |
| i | Info panel | `shared/info_page.py` is for "The Real Story" sources on climate games. Overclock is fun-first, so **not** used as a sources page; instead a plain "About / Credits / How runs work" panel reusing `shared/info-page.css` styling. Decide at Milestone 6 whether to skip. |
| j | Ambient look | `shared/ambient-bg.css` (or `space-bg.css` if space is chosen) for the backdrop; `shared/personal-best.css` for a best-depth badge. |
| k | Test harness | `tests/conftest.py` + `fakes.py` (fake DOM/timers/`create_proxy`) copied from a recent game (Thaw), `SHARED_DIR` on `sys.path`, `requirements-dev.txt` (`pytest>=8.0`). Suites: core loop, RNG determinism (same seed -> same run), save round-trip, achievements, changelog, settings, worst-case perf. Zero tests hit the network. |
| l | Feedback / reports | In-game feedback prompt piped to the Neon backend per root conventions (as Thaw milestone 6). |
| m | Hub integration | See section 5. |

## 5. Hub integration checklist
- Title card in root `index.html` (`<article class="title-card" data-tags="...">`, thumb class `title-card-thumb--overclock` in `style.css`, blurb, tag pills, `review-widget` with `data-game-slug="overclock"`). Tag: something like "Roguelike Strategy"; **no** "Made for BCM" line.
- `icons/favicon-overclock.svg` in the shared rounded-square + one-glyph convention (Z30), using the game's accent color; `<link rel="icon">` in the game's `index.html`.
- `sw.js`: add `games/overclock/index.html`, `style.css`, `game.py`, `settings.js`, `achievements.json`, `changelog.json`, content JSONs to the precache list (stale-while-revalidate means JSON changes show one load late; note in dev log).
- Root `CLAUDE.md`: add a row to "Current games" (this also feeds `roadmap.html`, which parses that table live) and a Milestone N status update as work proceeds.
- Rerun `scripts/generate-last-updated.py` and `scripts/generate-roadmap-data.py`; commit the JSONs. `whats-new.html` picks the game up from the dev logs, so log entries name it plainly.
- Hub `script.js`: achievements list (item c). No backend change needed (`/app` ratings/saves are slug-generic; verify the slug isn't allow-listed in `app/main.py` before shipping).

## 6. Milestones (baseline only)
Commit + tag each: `git commit -m "Milestone N: <name>"`, `git tag overclock-milestone-0N`.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Skeleton + seeded RNG + phase loop | `games/overclock/` folder, index/style/game.py, `rng.py`, phase state machine, placeholder "Fight -> reward -> advance -> die at node N" loop, test harness. Tests: RNG determinism, phase transitions | Not started |
| 2 | Run/meta state + save | `get_state`/`load_state` with the meta/run split, shared save widget, permadeath folds run into meta. Tests: round-trip mid-run, old-save tolerance | Not started |
| 3 | Settings + confirm dialog | `settings.js` (text scale, reduce motion), `confirm-dialog.js` on Abandon/Reset. Tests: settings persistence, confirm opt-out | Not started |
| 4 | Content JSON pipeline | `content/*.json` loaded through fetch + Python loader with schema validation; placeholder rows only. Tests: id uniqueness, validation errors | Not started |
| 5 | Achievements + changelog | `achievements.json` (~8 generic), panel/toast, `changelog.json` panel, hub `script.js` line, manifest regenerated | Not started |
| 6 | Onboarding + mobile + a11y | `tutorial.js` steps, mobile dock/HUD, colorblind audit, About panel, feedback prompt | Not started |
| 7 | Hub integration + ship | Title card, favicon, `sw.js`, root CLAUDE.md row, roadmap/last-updated data, dev-log entries, live verification at desktop and 375px | Not started |

## 7. Milestones after the gimmick is chosen (stub)
Blocked on the round-3 decision (theme, core gimmick, run length, meta-progression). Expected shape once decided: card/effect engine, enemy and encounter content, map/route generation, reward drafting, meta unlocks, balance pass, visual pass, achievements expansion, Pass 2/3 iteration. Not scoped here.

## Working conventions
Session logging to `BCM114-DEV-LOG.md` (game content) and/or `BCM206-DEV-LOG.md` (infra), append-only; check off `planning/TODO.md` items and recompute its Progress line; update Status column as work lands.
