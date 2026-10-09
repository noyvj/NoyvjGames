# Logic Gates (working title)

Personal project, no BCM tag. Plan: `planning/logic-gates-plan.md` (QI-1 in `planning/TODO.md`). Section code LG.

## One-line pitch
A dead station computer, rebuilt one circuit at a time: wire gates to match a truth table, keep each solved circuit as a chip, and end by wiring a four-instruction computer.

## Standing rules
No timers, energy, grinding or lost progress; no roguelike or deck mechanics; no audio; no generated images (the board is SVG drawn by code); no mandatory leaderboard; no all-good hero. A level is a pure function of the wiring: deterministic, no randomness, no clock (a test scans the engine for it). Every action visibly counts (chips placed, wires drawn, switches flipped, levels solved/at par, sandbox truth tables). Three goals always visible. Display settings live in localStorage, never in the save.

## Stack
Python via Pyodide: DOM-free engine modules, `game.py` with `handle(json)`, `get_state()`, `load_state()`, and a thin JS view (`app.js`). Plain HTML/CSS, no build step.

## Engine modules
| File | Job |
|---|---|
| `chips.py` | the seven gates and the three memory cells (SR latch, D latch, flip-flop) |
| `net.py` | text form for circuits and scripted steps (level data and tests) |
| `sim.py` | flatten built chips into primitives; acyclic pass (all truth-table rows at once as bitsets) or cyclic settle with oscillation detection; power-on state is all 0 |
| `levels_a/b/c.py`, `levels.py` | the 40 levels (data), the chip registry (a level's chip IS its reference circuit), open/unlock rules |
| `check.py` | does a circuit meet a level: truth table or scripted sequence |

## Levels
40 in five chapters (Switches and Lamps 8, Combining Gates 9, Memory 7, Adders 7, A Tiny Computer 9). A level opens when the chips its reference uses are unlocked. Par = reference chip count. Sequence levels start from power-on.

## Milestones
See the table in `planning/logic-gates-plan.md`; state is in `BUILD-STATUS.md`.
