# Logic Gates (working title) -- Groundwork Plan (Quick ideas QI-1)

Status: being built in `games/logic-gates/` (slug `logic-gates`, section code LG). Owner approved it from the Quick ideas round: "wire AND, OR, NOT and XOR chips to hit target outputs. Each solved level unlocks a new chip, and the last levels have you build a tiny working computer." Personal project, no BCM tag. Hub registration is a separate later job. Checked against `PLAYER-PROFILE.md`: logic/coding puzzle (yes), computers theme (favoured), collector of chips (yes), easy-to-medium, no timers, nothing lost, no audio.

## 1. Pitch
A dead station computer, rebuilt one circuit at a time. Each level gives you switches on the left and lamps on the right and a truth table the lamps must match. You wire chips between them. Solve it and the circuit becomes a chip you keep, so by the end you are wiring a clock, a register, an ALU and a four-instruction computer out of parts you built yourself.

## 2. Core constraints (binding)
- Python via Pyodide, DOM-free engine + thin JS view, plain HTML/CSS, no build step, no audio, no generated images (the board is SVG drawn by code).
- **Level state is a pure function of the wiring.** The checker evaluates every row of the truth table (or every step of a scripted sequence from power-on) deterministically. No randomness anywhere, no clock, no timers, no energy, nothing lost by leaving. Source-scan tests enforce it.
- Every action visibly counts: chips placed, wires drawn and switches flipped are lifetime counters on screen; levels solved and at par are always shown; the sandbox logs every new truth table.
- Three goals always visible ("Next goals", any order). A fail is never a dead end: Undo, Clear (with Restore), and a three-rung hint ladder.
- No roguelike or deck mechanics, no mandatory leaderboard, no all-good hero (the story's previous engineer is a flawed person).
- The reference solution of every level is data and is tested: it solves the level, uses only chips unlocked by then, and its chip count is the par.

## 3. The board
- Inputs are switches (left), outputs are lamps (right), chips sit between in columns laid out automatically by depth, so there is no dragging.
- A chip has named input and output pins. A wire joins one source (a switch, a chip output, or a tied 0/1) to one input pin or lamp. One source can feed many pins. An unwired pin reads 0 and is drawn as a floating pin.
- Two ways to wire, both always available: click a source pin then click input pins (touch and mouse), or choose the source from a list on the chip's card (keyboard and screen reader). A text description of the whole circuit is always shown.
- Live probe: flip the switches, see every wire show 1 (solid, thick) or 0 (dashed, thin) and every lamp 1 or 0 (filled or hollow, with the digit). Wire colour is decoration only.
- Loops (feedback) are allowed only in levels that mark `loops` (the memory chapter on) and the sandbox; elsewhere a wire that would loop is refused with a plain reason.
- Board space is a per-level cap on chips (about double the par), shown as "Chips 4/12". Composite chips count as one chip.

## 4. Chips and unlocks
Seven gates (NOT, AND, OR, XOR, NAND, NOR, XNOR) then about 30 built chips (MUX, decoder, comparator, SR latch, D latch, D flip-flop, toggle, counter, shift register, half and full adder, 4-bit adder, add/subtract, zero detector, equality, register, ALU slice and ALU, program counter, ROM, CPU core ...). A level's chip is defined by its own reference solution (combinational ones) or by a small behavioural model (the three memory cells: SR latch, D latch, D flip-flop, so a whole computer simulates quickly). A level opens when the chips its reference needs are unlocked, so order is free wherever the chips allow, and the picker says what a locked level is waiting for. A level never offers the chip it unlocks.

## 5. Levels (40, five chapters)
1. **Switches and lamps** (8): Straight Through, Invert, Both, Either, Odd One Out (build XOR), Not Both, Neither, Same.
2. **Combining gates** (9): Three Keys, Any of Three, Lock Code, Selector, Majority, Exactly One, Four-Way Selector, Comparator, Decoder.
3. **Memory** (7, sequences, loops allowed): Latch Up (NOR loop), Gated Latch, Edge Catcher, Toggle, Two-Bit Counter, Shift Register, Pulse Catcher.
4. **Adders** (7): Half Adder, Full Adder, Two-Bit Adder, Four-Bit Adder, Add/Subtract, Zero Detector, Equal.
5. **A tiny computer** (9): Register Bit, Register, ALU Slice, ALU, Program Counter, Program ROM, Fetch and Execute (the machine runs the station's first program), Second Program (your own ROM for the same core), Wake the Station (write a program that ends on 9).
Sequential levels use scripted steps from power-on ("S=1 R=0 -> Q=1"); the board shows the step table and you can step through it or flip switches yourself.

## 6. Scoring, easy to 100%
Solved is the main mark. **Par** (a second, optional mark) is solving with no more chips than the reference. Par is generous and never gates progress, chips or achievements except two optional ones. Using the answer still solves the level (no one is stuck) but does not count as par. 100% = all 14 achievements, all reachable, none timed or hidden.

## 7. Hint ladder
Rung 1 **Nudge**: one sentence about the idea. Rung 2 **Hint**: names the chips and the shape of the wiring in words. Rung 3 **Answer**: the full wiring in words plus a button that places it on the board. Each rung is one button; hints used is shown, never punished.

## 8. Sandbox
Free board: switches A, B, C and lamps X, Y, every unlocked chip, loops allowed. Every new truth table an output makes is logged ("n of 256 found"); the 16 two-input functions (FALSE, AND, ..., NAND, TRUE) form a named collection, "The Sixteen".

## 9. Achievements (14, hub manifest `achievements.json`, shown as have/need)
First Light (solve 1), Gate Keeper (chapter 1), Mix and Match (chapter 2), Remember Me (chapter 3), Carry the One (chapter 4), Wake the Station (final level), Forty for Forty (all 40), Tidy Ten (par on 10), Full Par (par on all 40), On Your Own (15 levels with no hint), Asked Nicely (use a hint once), The Sixteen, Hundred Chips (place 100), Switch Flipper (flip 100 switches).

## 10. Look and tone
Dark, quiet "night blueprint": near-black navy, cyan signal, amber lamps, thin lines; light theme is a pale drafting sheet. Station log lines (switchable story text) tell of Meridian Relay and a previous engineer, Vale, who shut the core down and wrote notes that explain less than they hide. No audio.

## 11. Milestones
| # | Milestone | Content | Status |
|---|---|---|---|
| 1 | Engine and level data | chips, circuit text form, simulator (acyclic pass + cyclic settle), checker, all 40 levels with verified references, tests | Done |
| 2 | Board UI | SVG board, chip cards with source lists, palette, probe, truth table, picker, stats and goals strip, save contract, localStorage | Planned |
| 3 | Chapters 2-3, hints, sandbox | levels 9-24, sequential checking, hint ladder, sandbox with truth-table log | Planned |
| 4 | Chapters 4-5 | levels 25-40, the CPU core, full play-through test, restore and clear | Planned |
| 5 | Standard kit | settings, tutorial, About with live-read sources, changelog, shortcuts, accessibility, light theme, shared includes | Planned |
| 6 | Achievements | 14 achievements, manifest, panel, goals strip, copy result | Planned |
| 7 | Desktop boot | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html` | Planned |
| 8 | Wrap-up | story log, mobile and desktop pass, docs, BUILD-STATUS | Planned |
| 9 | Hub registration | NOT mine: main session (cards, manifests, sw, game-*.json) | BLOCKED ON MAIN |

## 12. Open questions for the owner (defaults in brackets are in the build)
- **Lg1** Keep the small story (station Meridian Relay, the flawed engineer Vale), or make it pure puzzle? [kept, switchable]
- **Lg2** Should a level open only when its chips are unlocked (free order inside that) or strictly one after another? [chip-based]
- **Lg3** Is par (fewest chips) welcome as an optional second mark, or should it go? [kept, optional, generous]
- **Lg4** Add later chapters (a bigger instruction set, a two-register machine, a small program editor)? [no, parked]
- **Lg5** Should the finished chips be shareable as a code a friend can paste in the sandbox? [no, owner dislikes sharing codes]
