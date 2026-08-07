# Climate Quartet — Second Set — Root Plan

**Context for Claude Code:** This is a second set of four candidate games for the same BCM114 Round 1 Digital Artefact as the original Climate Quartet (Grid, Canopy, Tide, Aftermath — see `climate-quartet-plan.md`, and each game's own `games/<slug>/CLAUDE.md`). Read that file too if working across both sets; the shared conventions (testing, feedback hook, hub integration, tech stack) apply here unchanged. This file only covers what's different about this set.

## Why a second set

The original four were built around specific climate *issues* (energy, land use, oceans, adaptation). This set is built around the **three functions named directly in the subject framing**: demonstrating causes of climate change, simulating futures if the current path continues, and ideating systems to combat the concern. Each game below is tagged with which function(s) it serves, and that tag should show up explicitly in whatever Contextual Report Blog writing discusses it — this is the thing that makes the SDG/theme link read as substantive rather than decorative.

**Total candidate pool is now eight games across two sets.** This is intentionally more than can likely be finished by 4 September — treat both sets as a shared priority queue, not two separate obligations. Pull from whichever set's next-simplest unbuilt game when picking up new work, don't feel obligated to finish one set before touching the other. (The original quartet — Canopy, Grid, Tide, Aftermath — is fully built as of this writing, so this set is the active queue.)

## The three functions

| Function | What it means in practice |
|---|---|
| **Causes** | Making an abstract driver of climate change (methane, emissions, extraction) into something the player is actively producing and has to reckon with |
| **Futures on the current path** | Simulating what happens if nothing changes — background trajectories the player doesn't fully control, only influences |
| **Systems to combat** | Games about redesigning structures (supply chains, institutions, response capacity) rather than managing a single rising meter |

## This set's four games

| Game | Function(s) | Climate issue | Core lesson |
|---|---|---|---|
| Herd | Causes | Industrial agriculture & methane | Growth and emissions are coupled unless you deliberately decouple them |
| Thaw | Futures on current path | Permafrost feedback loops | Slow problems can flip into runaway ones once a feedback loop kicks in |
| Loop | Systems to combat | Circular economy & overconsumption | Waste is a design choice, not an inevitability |
| Drift | Futures + Systems to combat | Climate migration & displacement | How well-prepared institutions turn crisis into manageable transition |

The **hope angle still applies to all four** — see the original root doc's requirement. Loop and Drift are naturally the easiest to make hopeful (they're explicitly about building better systems). Thaw and Herd need more deliberate design attention to avoid reading as pure doom — Thaw especially, since a feedback loop is inherently a runaway-danger mechanic; give the player a real lever that visibly slows or interrupts the loop, not just a countdown.

## Build order (simplest → most complex)

1. **Herd** — single coupled-meter system, most similar in shape to Grid/Canopy from the first set
2. **Thaw** — background trajectory + feedback loop, moderate complexity
3. **Loop** — supply-chain redesign, more systemic than a single meter
4. **Drift** — institutional response to a long-timeline crisis; most complex, most systems-heavy

## Per-game files

- `games/herd/herd-plan.md`
- `games/thaw/thaw-plan.md`
- `games/loop/loop-plan.md`
- `games/drift/drift-plan.md`

Each follows the same structure as the first set: concept, climate issue + hope angle, core loop, milestone checklist, tech notes, feedback hook spec. Once a game is ready to start building, move its plan into `games/<slug>/CLAUDE.md` and build there — same pattern as SOL, Trade Empire, and the first quartet.
