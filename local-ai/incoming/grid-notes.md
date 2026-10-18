# Grid: LA-8 batch 1 (session s1, 2026-10-18)

Steps are in `local-ai/incoming/grid.txt`: 46 steps in 8 chains, lint reports 0 problems. Every step was built and its tests
run in a scratch copy of `games/grid` first (the engine, save, panel and browser tests all passed, and so did the rest of the
Grid suite); the step texts were then tightened to fit 1500 characters.

## Do this BEFORE the steps are queued (needs Claude, not the local AI)
1. **Raise the `index.html` cap.** `tests/test_file_sizes.py` caps `index.html` at 15,500 tokens and the file is at 15,307, so only
   about 770 bytes are free. The 8 chains add about 2.9 KB of markup (8 small panels, kept to one line each, no comments); with all of
   them the file measured about 16,041 tokens in the scratch copy. Change `CAPS = {"index.html": 15_500}` to 16_500 (or higher). The runner's fast suite uses `-x`, so without this every markup step fails.
2. Expect trivial merge conflicts when more than one chain is merged: every markup step adds one `ELEMENT_IDS += [...]` line above
   `INITIALLY_DISABLED_IDS = (` in `tests/conftest.py`, one entry to `pc-config.json` `zones` (each chain uses a different anchor)
   and one or two lines in `game.py` `setup()`/imports; keep both sides. `ai.ps1` regenerates `pc.html` before each test run, so no
   step touches it.

## A (relabel `[local AI: yes]`)
None. Every Grid item that survived needed an engine change plus a panel plus a browser test, so none is one small step.

## B (split) - items, chain, steps
| Item | Chain | Steps | What the chain builds |
|------|-------|-------|-----------------------|
| C-15 | `chain:C-15` | 6 | `round_snapshots` (last 100 rounds: fleet, demand, funds, disruption, weather), saved only when not empty, a "Look back at past rounds" slider panel |
| GC-10 | `chain:GC-10` | 8 | opt-in boss rounds every 8th round (Heatwave, Polar Vortex, Dry Summer), one-round preview, +150 funds when the whole demand is met, a toggle button |
| R4-GR-1 | `chain:R4-GR-1` | 5 | new scenario "Electrified city" with four announced demand jumps (3 rounds notice) |
| R4-PG-3 | `chain:R4-PG-3` | 6 | 12 Incident Files (brownout x3, damage x2, aging x7) filed the first time each happens, panel with completion percent |
| R4-PG-25 | `chain:R4-PG-25` | 4 | power line bench (voltage, current, distance sliders, I squared R loss) |
| R4-GRPC-8 | `chain:R4-GRPC-8` | 5 | sortable plan table (cost, output, emissions, payback) with a Build button per row |
| R4-GRMO-7 | `chain:R4-GRMO-7` | 4 | Auto-plan: one suggested renewable build in plain words and a button that builds it |
| R4-GRPC-4 + R4-GRPC-9 | `chain:R4-GRPC-4` | 8 | `capacity_history`, supply-against-demand SVG with a dashed next-round forecast and the what-if swing slider (GRPC-9 is folded in because it needs the chart) |

## C (no steps written)
| Item | Label | Reason |
|------|-------|--------|
| GC-3 dispatch puzzle | `[needs you]` | how dispatch order turns into revenue and brownouts is not specified (numbers), and dragging into merit order is a gesture the model fails at |
| GC-7 siting map | `[needs you]` | tile qualities, NIMBY rules and the map layout are design decisions and change capacity numbers |
| GC-22 neighbour trading | `[needs you]` | "negotiated price" has no defined mechanic (accept, haggle?), and it changes the revenue economy |
| R4-GR-3 transmission lines | `[needs you]` | needs a location model for plants and lines; changes capacity and revenue |
| R4-GR-4 winter/summer split | `[needs you]` | changes the round structure (two peaks per round) and every demand and revenue test |
| R4-PG-4 island rescue | `[Claude: story text and scenario balance]` | three voices of written content plus a new scenario's numbers |
| R4-PG-5 operator styles | `[needs you]` | which numbers each style highlights and which perks it earns are undefined |
| R4-PG-12 Brownout City | `[Claude: story writing]` | dark multi-view story scenario |
| R4-PG-17 fault tracing | `[needs you]` | the three instruments, the causes and the bonus size are not defined |
| R4-PG-18 rule-tile puzzles | `[Claude: new puzzle engine]` | a Baba-Is-You style rule rewriter needs a design and an engine |
| R4-PG-20 equippable parts | `[needs you]` | slot tables and the milestone unlock list are design decisions |
| R4-PG-22 Continental Grid | `[needs you]` | multi-region state and billion-scale numbers |
| R4-PG-27 script puzzles | `[Claude: new puzzle engine]` | needs a small rule interpreter |
| R4-PG-28 household story | `[Claude: story writing]` | branching story content |
| R4-GRPC-1 drag plants onto a map | `[Claude: drag UI and a map]` | there is no map, and drag gestures fail for the local AI |
| R4-GRMO-1 swipe cards | `[Claude: swipe gesture]` | gesture work |
| R4-GRMO-3 touch bubble on the chart | `[Claude: pointer events, after R4-GRPC-4 merges]` | needs the supply chart that R4-GRPC-4 builds; the chart SVG is rebuilt on every render, which broke earlier touch tasks |

## Table
| Item | Decision | Steps |
|------|----------|-------|
| C-15 | B | 6 |
| GC-3 | C | 0 |
| GC-7 | C | 0 |
| GC-10 | B | 8 |
| GC-22 | C | 0 |
| R4-GR-1 | B | 5 |
| R4-GR-3 | C | 0 |
| R4-GR-4 | C | 0 |
| R4-PG-3 | B | 6 |
| R4-PG-4 | C | 0 |
| R4-PG-5 | C | 0 |
| R4-PG-12 | C | 0 |
| R4-PG-17 | C | 0 |
| R4-PG-18 | C | 0 |
| R4-PG-20 | C | 0 |
| R4-PG-22 | C | 0 |
| R4-PG-25 | B | 4 |
| R4-PG-27 | C | 0 |
| R4-PG-28 | C | 0 |
| R4-GRPC-1 | C | 0 |
| R4-GRPC-4 | B | 8 (shared chain) |
| R4-GRPC-8 | B | 5 |
| R4-GRPC-9 | B | folded into the R4-GRPC-4 chain |
| R4-GRMO-1 | C | 0 |
| R4-GRMO-3 | C | 0 |
| R4-GRMO-7 | B | 4 |

## Choices I made that the owner may want to change
- GC-10: only the funds reward (+150) is built. The "cost discount" would touch `plant_cost()`/refund rules (see CLAUDE.md, past
  exploit) and the achievement needs `achievements.json`, `story.json`, `grid_achievements.py` and a hub-wide total: left for Claude.
  Boss rounds are an opt-in toggle (the owner's "hard modes are opt-in" rule); nothing is lost when a boss is missed.
- R4-GR-1: demand jumps only exist in the new "Electrified city" scenario, not in every run, because many tests pin the demand
  numbers and the extra demand makes the game harder. Step 3 of the chain has to edit two older tests that count scenario clicks.
- R4-PG-3: "handles" is read as "the first time that incident happens". The cause and stops texts are built from the game's own constants.
- R4-PG-25: the bench keeps a session-only "settings tried / lowest loss found" line so using it visibly counts (project rule on practice
  actions); nothing is saved.
- R4-GRMO-7: Auto-plan only ever suggests a renewable plant (hope angle), chosen by price per unit of capacity among those affordable.

## Where the CLAUDE.md map was wrong or missing something
- Grid's test fake DOM (`tests/fakes.py`) raises `KeyError` for an id that is not in `tests/conftest.py` `ELEMENT_IDS`, and its
  elements have no `setAttribute` (plain attribute assignment works). Neither is in the "For the local AI" map; the steps say so.
- The "New panel" recipe only covers toggle panels. A `<details>` panel with no toggle button needs no `runstate` flag, no window
  and no listener for its toggle; it just needs the id lines in `conftest.py` and an entry in `pc-config.json` `zones`.
- The map says `index.html` is capped at 15,500; it does not say there are only about 770 bytes left.
