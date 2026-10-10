# Circuit Playground (slug `circuit-playground`, TODO QI-39) - Groundwork Plan

Source: the Quick ideas round (G6), owner-approved: "a free sandbox for building circuits with live voltage readouts." Checked against `PLAYER-PROFILE.md`: electronics and physics named as interests, computers and science fiction, collecting every part, sandbox plus optional goals, three goals visible, easy to 100%, effects toggleable, "more game than teaching", no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: a quiet workbench where you drop batteries, resistors, lamps and switches on a board, wire them up and read the volts and amps on every part, with small optional workbench jobs to give it direction.

## 1. Concept
A bench in an old relay shed at **Lowfield Station**. A grid board, a drawer of parts, and meters. You place parts, draw wires between their ends, and press nothing: the circuit is solved the moment it changes, and every wire end shows its voltage, every part its current. Switches click, lamps glow in steps (brightness shown as a word and a shape, not only colour), a capacitor charges when you press **Step**, and a meter can be put anywhere.
- 2-minute session: a battery, a resistor and a lamp; flip a switch; read 9 V, 0.03 A.
- 20-minute session: build a voltage divider, a two-lamp parallel set and a latch from two switches, finishing a few Workbench jobs.
- Look: clean dark low-poly workbench as SVG; parts as flat faceted symbols with names; wires thick and straight on a grid. Readouts are always numbers with units and a plain word ("warm", "bright", "too much"). Quiet; optional generated clicks via `shared/sfx.js`.
- **Nothing breaks.** A short circuit shows "this wire is carrying a lot" and the board holds; a lamp pushed past its rating shows "would burn out" and stays whole. Restore, undo and clear are free. The sandbox is the core game, with no goals required.

## 2. Rules (a pure function of the board)
- Parts: wire, battery, resistor, lamp, LED (with a resistor warning), switch, push button, potentiometer, capacitor, diode, ground, voltmeter, ammeter, buzzer-lamp (visual only). Component values come from standard sets (resistors in the E12 series, batteries 1.5 V, 5 V, 9 V, 12 V) and can be changed from a small list.
- Solver: **modified nodal analysis** on a small network of nodes (at most 24 parts), solved exactly with `Fraction` or with a 1e-9 tolerance float. Diodes and LEDs use a piecewise model (off or on with a fixed forward drop), solved by trying on/off states deterministically. Capacitors are open in steady state and charge in fixed **Steps** (an RC step, not real time).
- Display: voltage at each node to the ground node, current through each part, power in watts. Floating (unconnected) nodes show a hint, not an error.
- No clock, no randomness, no network.

## 3. Content size
- 14 part types and a 24-part board limit; 30 **Workbench jobs** in five sets of six (Series, Parallel, Divider, Switches, Time), each a tiny brief with a check ("make the lamp get half the battery voltage"); 20 **Discoveries** (named circuits the game recognises: series, parallel, divider, short circuit, open circuit, latch, pull-down, RC delay...).
- A **Parts Drawer** of 14 entries that fills the first time you place each part, each with a one-line card and the real symbol.

## 4. How fairness is PROVED (tests)
- Solver correctness: hand-solved reference circuits (Ohm's law, series, parallel, dividers, Wheatstone bridge) must match within tolerance; **Kirchhoff checks** on thousands of seeded random boards (current into each node sums to zero, voltage around each loop sums to zero); results are independent of the order parts were placed.
- Singular cases: floating nodes, shorted batteries, and parallel ideal sources are handled with a friendly message, never an exception.
- Diode and LED model: a table test across forward and reverse cases; the on/off search converges on every test board.
- Every Workbench job has a stored reference board that passes its check, and a list of near-miss boards that must fail; every Discovery has a positive and negative board.
- Determinism: same board, same readouts. Source scan: no clock, no randomness.

## 5. Bigger picture, goals, hints
- The **Workshop Wall**: a shelf of 14 drawer slots and a corkboard of 20 Discovery cards plus 30 job tags that fill in; a completion percentage bar.
- Three goals always visible (any order): the next three unearned achievements or unfinished jobs with counts and bars. Stats strip: Parts met, Jobs done, Discoveries, Boards built.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"), for a job: Nudge (which part matters), Hint (a ghost of the first half of the board), Answer (the whole board as a ghost with a Place it button; the job still counts).
- All sets and jobs open from the start; the sandbox is always open.

## 6. Achievements (14; computed from facts)
1 First Glow (light a lamp); 2 Parts Drawer Half (7); 3 Drawer Full (14); 4 First Job; 5 Ten Jobs; 6 Thirty Jobs (all); 7 Series; 8 Parallel; 9 Divider; 10 Ten Discoveries; 11 All Twenty; 12 Too Much (see a "would burn out" warning and fix it); 13 Step (charge a capacitor to 90%); 14 Second Opinion (all three hint rungs on one job).

## 7. Real-world facts
Part cards show real values read live from named, dated sources: the E12 resistor series and resistor colour code (a standards explainer), typical LED forward voltages (a named electronics reference) and a battery voltage table. Marked as background; the sandbox's own numbers are computed. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG (board, parts, wires), no build step. Modules: `parts.py`, `board.py` (grid, wires, nets), `solver.py` (nodal analysis, diode search, capacitor step), `jobs_*.py`, `discoveries.py`, `drawer.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js` (drag, wire drawing, keyboard).
- Reuses Logic Gates' board and probe rendering, Hull Repair's drag-to-draw glue, `shared/sandbox-mode.js` patterns, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: the current board (compact text, re-solved on load), job results, discoveries, drawer, hint rungs, flags.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Parts, nets, nodal solver, diode and capacitor steps, Kirchhoff property tests, reference circuits |
| 2 | Bench UI | SVG board, part drawer, wire drawing, live readouts, undo and clear, save contract. Playable slice (the sandbox) |
| 3 | Jobs and Discoveries | 30 Workbench jobs, 20 Discoveries, Workshop Wall, hint ladder, three-goals strip |
| 4 | Parts and polish | Remaining parts (potentiometer, push button, capacitor Step), warnings, Parts Drawer. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should the board stay at 24 parts (works well on phones), or allow bigger boards on desktop? Default: 24 on every device.
2. Should AC (a swinging source) ever be added, or keep everything DC? Default: DC only.
