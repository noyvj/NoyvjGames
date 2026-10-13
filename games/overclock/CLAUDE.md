# Overclock

Seed: `planning/overclock-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Originally: a roguelike deck-builder. **Now: a space roguelike built around the Reactor Ring (no deck).** The rest of this paragraph is the round-2 framing: draft a run-specific build each attempt, fight through procedurally arranged encounters of escalating difficulty, permadeath-and-retry. Pure build-crafting and combat satisfaction, "this run vs. the last one." Explicitly **fun-first, not teaching** (user, M1/M5 feedback): no climate/educational framing, no "Real Story" lesson content. No BCM tag (personal project, like Le Champ de Mots) unless the user says otherwise.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Theme | **Space.** Palette and ambient: `shared/space-bg.css`. Tag "Space Roguelike". | Not started |
| 2 | The gimmick | **The Reactor Ring** (below). **Not a deck-builder.** | Not started |
| 3 | Run length | **About 15 minutes** (8 encounters). Quick, mobile-friendly. | Not started |
| 4 | Meta-progression | **Unlocks only**: new modules, ships and sector modifiers. No permanent stat upgrades. | Not started |
| 5 | Story text | **Off by default**, behind the shared story toggle. | Not started |
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
| 1 | Skeleton + seeded RNG + phase loop | `games/overclock/` folder, index/style/game.py, `rng.py`, phase state machine, placeholder "Fight -> reward -> advance -> die at node N" loop, test harness. Tests: RNG determinism, phase transitions | Not started |
| 2 | Run/meta state + save | `get_state`/`load_state` with the meta/run split, shared save widget, permadeath folds run into meta. Tests: round-trip mid-run, old-save tolerance | Not started |
| 3 | Settings + confirm dialog | `settings.js` (text scale, reduce motion), `confirm-dialog.js` on Abandon/Reset. Tests: settings persistence, confirm opt-out | Not started |
| 4 | Content JSON pipeline | `content/*.json` loaded through fetch + Python loader with schema validation; placeholder rows only. Tests: id uniqueness, validation errors | Not started |
| 5 | Achievements + changelog | `achievements.json` (~8 generic), panel/toast, `changelog.json` panel, hub `script.js` line, manifest regenerated | Not started |
| 6 | Onboarding + mobile + a11y | `tutorial.js` steps, mobile dock/HUD, colorblind audit, About panel, feedback prompt | Not started |
| 7 | Hub integration + ship | Title card, favicon, `sw.js`, root CLAUDE.md row, roadmap/last-updated data, dev-log entries, live verification at desktop and 375px | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag overclock-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/overclock/register.json`, then `scripts/register_game.py overclock`).
