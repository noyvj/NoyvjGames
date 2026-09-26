# Overclock — Groundwork Plan (baseline only)

**Status:** groundwork, pre-build. Written 2026-09-21 from `IMPROVEMENT-IDEAS-ROUND-2.md` section M (item 6) and the user's answers. Save as `games/overclock/CLAUDE.md` (trimmed to concept + milestone table) once Milestone 1 starts.

**This file holds the FULL shared baseline checklist** (section 4). `last-line-plan.md` and `deep-descent-plan.md` reference it by name and list only what differs.

## Decisions (2026-09-27, from Round 3 answers)
Source: `IMPROVEMENT-IDEAS-ROUND-3.md` Part 4, section S. The user chose **space** ("save cult for a game I actually like"), said they dislike roguelikes and card games, delegated every other choice ("do whatever and have fun"), and pre-approved the result, noting they want at least one game in this genre for the "tried all the genres" record. So the remaining calls are **mine**, recorded here. Section 2 below is superseded by this section; sections 1 (pitch, revised), 3, 4, 5 remain the shared baseline; sections 6 and 7 are replaced by the "Revised milestone order" below.

| # | Question | Decision |
|---|----------|----------|
| 1 | Theme | **Space.** Palette and ambient: `shared/space-bg.css`. Tag "Space Roguelike". |
| 2 | The gimmick | **The Reactor Ring** (below). **Not a deck-builder.** |
| 3 | Run length | **About 15 minutes** (8 encounters). Quick, mobile-friendly. |
| 4 | Meta-progression | **Unlocks only**: new modules, ships and sector modifiers. No permanent stat upgrades. |
| 5 | Story text | **Off by default**, behind the shared story toggle. |

### The gimmick: the Reactor Ring
Because the user dislikes card games, the game drops the deck entirely (no draw pile, no hand, no energy) and the combat is a sequencing puzzle with perfect information.

- **The ring.** Your ship has a **reactor ring** of 6 slots (some ships have 5 or 8). Each slot holds one **module** (Laser, Shield, Repair, Coolant, Amplifier, Missile, Decoy, Capacitor, Scanner and so on). At the end of every turn the ring **rotates one slot**, and the module that arrives at the **firing position** fires. Nothing is random inside a fight.
- **Your turn.** Make up to **2 adjustments** (swap two adjacent modules), then optionally **Overclock** the module currently in the firing position, then end the turn. Overclocking makes that module fire twice (or at double strength) but adds **heat**.
- **Heat.** A single gauge, 0 to 10. Each Overclock adds heat (most modules +3, some more or less), and heat falls by 1 each turn on its own. Above the limit the reactor **melts down**: the next two modules in the ring go offline for one rotation and the hull takes damage. Coolant modules remove heat when they fire.
- **Adjacency is the depth.** Modules affect neighbours: an Amplifier boosts the module in the slot after it, a Coolant next to a hot module reduces its heat cost, a Capacitor stores charge and releases it into the next firing. So arranging the ring is the build, and the same modules in a different order are a different machine.
- **Telegraphed enemies.** Every enemy shows its **next three intents** (attack for N, charge a beam, jam slot 3, add heat). You can plan a full rotation ahead. There is no hidden information in combat, so a loss is always a sequencing mistake you can see afterwards, which suits a player who dislikes luck-driven card play.
- **Space flavour that is also mechanics.** A solar flare turn adds heat to everyone. A jamming enemy locks a slot until it rotates past. Derelict turrets fire on a fixed schedule you can plan around. The "Overclock" verb is the name of the game.
- **Why this is genuinely distinct from Slay the Spire.** In Slay the Spire you draw a random hand each turn and spend energy to play cards, with block/attack/status cards and deck thinning as the build. Here there is no deck and no draw luck: the whole "hand" is a fixed ring you rearrange; the resource is heat, which trades tempo for risk on a single action; positions and neighbours matter, which a card hand does not model; and enemy behaviour is fully telegraphed. It shares only the run structure (a map of encounters, a reward pick after each fight), which is standard to the genre. It is closer in spirit to a programming or sequencing puzzle than to a card game.
- **What it costs.** It is a new system that has to be taught and balanced, so the tutorial and bot balancing are load-bearing (see milestones). It also needs a readable ring UI (a circular or arc layout) that still works at 375px; the fallback is a horizontal strip that scrolls the current slot into view.

### Run shape (about 15 minutes)
- **Run:** a small **sector map** of 8 encounters: 5 fights, 1 repair or salvage stop, 1 event, 1 boss. Route choice is 2 branches wide at three points. A fight lasts 5 to 8 rotations (about 1.5 minutes).
- **After each fight:** pick 1 of 3 modules (or take a repair, or a ring-expansion at rare nodes).
- **Death** ends the run and folds results into `meta`; there is no mid-fight retry.
- **Saves:** allowed only at node boundaries and at the start of a turn, so a resume never lands mid-animation. The serialised RNG state keeps the future identical.

### Meta-progression: unlocks only
Winning or reaching depth unlocks new modules (into the reward pool), new ships (ring layouts: the 6-slot standard, a 5-slot ring with a double-firing position, an 8-slot ring that rotates every other turn), and sector modifiers. Nothing makes the ship stronger in absolute terms, so a first run and a hundredth run are equally hard on the same seed. Where the shared skill-tree component (TODO-NEXT W-3) exists by then, the unlock list uses it as a tree of unlocks (no stat nodes); otherwise a simple list.

### Story text: off by default
Use `shared/story-toggle.js` with selectors for the story elements (event flavour, ship-log lines, the sector intro). That script treats an absent `localStorage["story-text:overclock"]` as **on**, so to default to off without changing the shared file, the game's `<head>` writes `"off"` into that key on the very first load if it is absent, before the script runs. Players turn it on with the normal pill. Mechanics text is never hidden by it. Story is a thin optional layer (a salvage crew crossing a sector), consistent with the "fun-first, not teaching" rule.

### Scope guard
The user wants this genre represented, not polished to their taste and has no expectation of input. Keep launch scope modest: about 24 modules, 10 enemy types, 3 ships, 1 boss. Deeper content is Pass 2. Balance is checked with automated bot playthroughs (the sim is pure Python and deterministic), since the user will not be the playtester.

### Revised milestone order (replaces sections 6 and 7)
Tag: `overclock-milestone-0N`. Milestones 1-4 are the baseline foundation from section 6; the game comes before the shipping kit so nothing is shipped as an empty shell. Milestones 1-8 plus 9-10 and 11 give a complete first release; 12 onward is the second set.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Skeleton + seeded RNG + phase loop | As section 6 milestone 1 | Not started |
| 2 | Run/meta state + save | As section 6 milestone 2 | Not started |
| 3 | Settings + confirm dialog | As section 6 milestone 3 (add the story-off default write) | Not started |
| 4 | Content JSON pipeline | As section 6 milestone 4 (modules, enemies, ships, sector nodes) | Not started |
| 5 | Ring combat engine | Pure Python: ring, rotation, adjustments, overclock, heat, meltdown, adjacency effects, intents. Tests: determinism, heat edge cases, adjacency rules | Not started |
| 6 | Combat UI | Ring layout (arc plus strip fallback), intent bar showing 3 turns, heat gauge, one playable fight | Not started |
| 7 | Modules and enemies | 12 modules, 6 enemies, reward pick, ship 1 | Not started |
| 8 | Sector map + run loop | 8-encounter map, route choice, repair stop, boss, death and win flow. **First complete, playable run** | Not started |
| 9 | Achievements + changelog | As section 6 milestone 5 (add ring-specific ones: Perfect Rotation, Cold Reactor, Meltdown Survivor) | Not started |
| 10 | Onboarding + mobile + a11y | As section 6 milestone 6; the ring tutorial is the critical step | Not started |
| 11 | Hub integration + ship | As section 6 milestone 7. **First release, single ship, no meta** | Not started |
| 12 | Meta unlocks | Unlock pool, ships 2 and 3, sector modifiers, unlock list or tree | Not started |
| 13 | Bots and balance | Random and greedy bots over thousands of seeds, win-rate and depth bands, tune | Not started |
| 14 | Content and visual pass | Modules to 24, enemies to 10, ring and space art, animation within reduce-motion rules | Not started |
| 15 | Pass 2/3 | Iteration, extra sectors, daily seed option (with an opt-in leaderboard via `app/leaderboards.py` and `shared/leaderboard.js`) | Not started |

## 1. One-line pitch and genre shape (from round 2; REVISED, see Decisions)
Originally: a roguelike deck-builder. **Now: a space roguelike built around the Reactor Ring (no deck).** The rest of this paragraph is the round-2 framing: draft a run-specific build each attempt, fight through procedurally arranged encounters of escalating difficulty, permadeath-and-retry. Pure build-crafting and combat satisfaction, "this run vs. the last one." Explicitly **fun-first, not teaching** (user, M1/M5 feedback): no climate/educational framing, no "Real Story" lesson content. No BCM tag (personal project, like Le Champ de Mots) unless the user says otherwise.

## 2. Deliberately undecided (SUPERSEDED 2026-09-27: all five decided in the Decisions section above; kept for history)
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

## 6. Milestones (baseline only; SUPERSEDED in ordering by "Revised milestone order" in the Decisions section, kept because the revised table refers to these rows)
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

## 7. Milestones after the gimmick is chosen (SUPERSEDED 2026-09-27)
The gimmick was chosen (the Reactor Ring). The second milestone set is now milestones 5-8 and 12-15 in the revised order in the Decisions section.

## Working conventions
Session logging to `BCM114-DEV-LOG.md` (game content) and/or `BCM206-DEV-LOG.md` (infra), append-only; check off `planning/TODO.md` items and recompute its Progress line; update Status column as work lands.
