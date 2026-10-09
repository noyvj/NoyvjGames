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
| # | Milestone | Status |
|---|---|---|
| 1 | Engine and level data (chips, simulator, checker, 40 levels) | Done |
| 2 | Board UI (SVG board, chip cards, probe, table, picker, save contract) | Done |
| 3 | Chapters 2-3, hint ladder, sandbox | Done |
| 4 | Chapters 4-5 (adders, the tiny computer) | Done |
| 5 | Standard kit (settings, tutorial, About, changelog, accessibility, light theme) | Done |
| 6 | Achievements (14) | Done |
| 7 | Desktop boot | Done |
| 8 | Wrap-up | Done |
| 9 | Hub registration | BLOCKED ON MAIN SESSION (not done here) |

Open questions for the owner (Lg1-Lg5) are at the end of `planning/logic-gates-plan.md`.

## Playing notes
Chips are earned by solving: a level hands out the chip it builds (a level's reference circuit IS the chip). Memory cells (SR latch, D latch, flip-flop) are modelled directly so the whole computer simulates quickly. A flip-flop never fires on the first look at its clock (power-on). The tiny computer: a 4-bit accumulator, a 2-bit program counter and a 4-word ROM; an instruction word W3 W2 W1 W0 is op (00 add, 01 and, 10 or, 11 xor) then a number 0-3; each clock edge runs ACC = ACC op number.
