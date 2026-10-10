# Stranded (working title)

You are Harbour, the plain voice on a thin text line to Ines Varga, a stubborn, funny field engineer alone on the small moon Orrin at the silent Sparrow Relay. Twelve days, 59 scenes, ten endings (nine warm or bittersweet, one sadder but gentle). Every reply gets an answer, nothing is timed, nothing is ever lost, and you can rewind to any of your messages for free. Personal project, no BCM tag, hub registration not done yet. Plan: `planning/stranded-plan.md` (TODO item QI-25). Read `BUILD-STATUS.md` first.

## Rules (owner's hard bans, all enforced by tests)
- No timers, energy, clocks, grinding, daily mechanics or randomness; replies arrive one per tap by default or all at once (a display setting, no timer).
- No on-screen death, no all-good hero (Ines overrode a warning light and avoids her brother's message), nothing that loses progress, no audio, no leaderboards, no generated images.
- Rewinding keeps the map, archive, endings and counters; only the three stats and flags go back (they are the state of that moment).

## Structure
- Story is data: `story_1..4.py` (S/C builders from `kit.py`; text shorthands in kit.py's docstring), `lore.py` (day titles, narrator lines, 29 collectables). The engine holds no story.
- `walker.py` is a pure deterministic stepper; the state is (scene, (trust, supplies, hope), flags), replayed from a string of choice numbers (the run's `path`).
- `explore.py`: `reach_all` (search over every reachable state, dominance-pruned, proves reachability), `route_to`, `loose_end`, `peek`. Edges are (scene, choice, target) triples so conditional routes count as separate paths.
- `game.py`: `handle(json)`, `get_state()`, `load_state()`; save = path, taken edges, seen scenes, endings, found ids, tally; validated field by field, new keys only when non-default, `achievements_earned` written never read.
- `app.js` is glue; `ENGINE_MODULES` must list every engine module in import order (a test checks).
- Desktop boot: `pc-config.json`, `pc.css`, `pc.js`; `pc.html` is generated (never edit by hand): import `scripts/generate-pc-pages.py` with importlib and write `build("stranded", cfg)`.

## Adding story
Add scenes to a story table; every non-ending scene needs 2 to 4 choices, each with a reply and at least one open choice; run `python3 -m pytest -q tests`. The graph tests prove every scene, edge, ending and collectable reachable, no cycles, no dead ends, and the lint refuses death, timer and energy words. Local Python is 3.9.

## Milestones
| # | Milestone | Status |
|---|-----------|--------|
| 1 | Engine and the whole story | Done |
| 2 | Comms UI | Done |
| 3 | Branch map and what-if | Done |
| 4 | Archive, goals, hint ladder | Done |
| 5 | Standard kit | Done |
| 6 | Achievements | Done |
| 7 | Desktop boot | Done |
- AN-7/8/9/10 (2026-10-11): one message per tap is the default (`stranded-reveal`, only the stored value "instant" switches it). Harbour's flaw: flag `quick` set by a too-quick reassurance on d2a, d4b, d6a (each costs trust and Ines says so); d7a offers `need="quick"` to own it (flag `owned`), which adds a line to e_lantern, e_pavel, e_honest and e_asleep. Tenth ending `asleep` (Left in the Window): r11a choice 4, needs `bitgave` (accepted Bit's battery on r9c). The narrator day-note is text only, off by default (`stranded-narrator` setting; hidden lines are filtered in `app.js listOf()` so they never cost a tap; the Story pill can also hide them). Choices were only appended, so old saved paths and taken edges stay valid.
