# Zero-G Shift

Seed: `planning/zero-g-shift-plan.md` (Quick ideas round A9, TODO QI-9). Personal project, no BCM tag, working title. Built 2026-10-11 by a background agent.

## One-line pitch
In a weightless cargo bay every thrust sends you or a crate gliding until something stops it, so you plan each slide to dock every crate. Forty-eight bays on six decks of the freight hauler Marrow.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. The bay, the pieces and the ship are SVG strings built in Python (`render.py`) so their markup is unit-tested.
- Runs from any static server. No audio files, and no sound at all in this build. Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code.

## Core constraints (do not violate without asking)
1. Rules, search and hints are pure and deterministic: no clock, no randomness in the engine (a test scans it). `tools/gen.py` uses a seeded `random` to FIND bays; its output is frozen in `bays_*.py`.
2. No timers, energy, grinding or progress loss; no roguelike, deck or card mechanics; no mandatory leaderboard; no all-good hero.
3. A wrong thrust is never a dead end for the player: Step back and Restart are free and unlimited (Step back straight after a Restart brings the set-aside attempt back), hints are free, "Can I still win?" never changes the position; states only go up.
4. Every bay is proved by the solver in tests: solvable, par stored and equal to the shortest solution, par at least 4, at most 3 shortest solutions (so a stored hint line is fair), and the deck's new part really needed.
5. No colour-only encoding: crates and pads carry a shape and a letter.
6. Every deck and every bay is open from the start (the plan's "deck n+1 opens at 5 of 8" was dropped: the owner's profile wants objectives with no strict order).

## Rules as built (`rules.py`)
- Cells: `#` wall, `o` post (works like a wall, drawn as a pillar), `.` floor, `h` hatch (a crate slides through, you cannot), `b` bumper (stops you on it, crates roll over), `=` airlock door (shut until every pad of the bay's `door` letter holds a crate), `A-D` dock pad, `1-4` crate of kind A-D, `@` you.
- One move = one thrust U/D/L/R. You slide until blocked. If the next cell holds a loose crate, you stop where you are and the crate slides until blocked (a "push"; a crate never pushes a crate; a pad of its own kind stops it and it docks for good; another kind's pad is slid over). A move that changes nothing is refused. A bay is clear when every crate is docked. The player does not recoil.
- A state is `(player cell, sorted tuple of crates)`, crate = `kind << 7 | cell`; identical-kind crates are interchangeable so the search space stays small.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and solver | `rules.py`, `solver.py` (full-graph BFS: par, shortest lines, dead states), `tools/gen.py` + `tools/build_bays.py`, deck 1 (8 bays) with proofs | Done |
| 2 | Bay UI | SVG bay, swipe/tap/keys/buttons, slide animation (toggleable), step back and restart, save contract. Playable slice | Pending |
| 3 | Decks 2-4 | 24 more bays, posts, pads, hatches, manifest panel | Pending |
| 4 | Decks 5-6, hints, goals | 16 more bays (48), bumpers and doors, hint ladder, three-goals strip, par medals. First complete game | Pending |
| 5 | Standard kit | Opening screen, tutorial, About, What's New, keyboard help, confirm dialogs, light theme, accessibility | Pending |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Pending |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Pending |

## Working conventions
- Commit only this folder with a pathspec commit, then tag `zero-g-shift-milestone-0N`. Hub registration is a separate later job.
- Tests: `python3 -m pytest -q games/zero-g-shift`; lint: `python3 -m flake8 --extend-ignore=E501 games/zero-g-shift`.
- Finding bays: `python3 tools/build_bays.py [deck ...]` rewrites `bays_<deck>.py` from the search settings in `tools/texts.py` (deterministic).

## Milestone 1 notes
- `solver.Analysis(bay)` walks the whole position graph from the start (the largest authored bay has well under 40,000 positions; a test caps it), then searches backwards from every cleared position, so one table answers par, the number of shortest solutions, "can this position still be won", the best next move and one stored shortest line. `solver.analysis(bay)` caches it per bay. `first_broken_move(bay, line)` binary-searches a played line for the move after which the bay could no longer be cleared (winnable prefixes stay winnable going backwards).
- Plan deviation: deck 1 ("Cargo Floor") is one crate on open floor with a few wall segments, deck 2 ("Crates") has two or three crates with their own shapes and letters, deck 3 adds posts and duplicate kinds. The plan's "Crates (one crate)" would have made decks 1 and 2 the same.
