# SOL — Solar System Incremental Clicker

Dual-purpose university digital artefact (DA) for BCM114 + BCM206 at UOW, Spring 2026 semester (starts July 27, 13 weeks). Built almost entirely via AI-assisted development.

## Stack
- **Python via Pyodide** (runs in-browser via WebAssembly) — not JavaScript. All game logic should be written in Python in `game.py`, using the `js` module / `pyodide.ffi.create_proxy` to interact with the DOM.
- Plain HTML/CSS shell (`index.html`, `style.css`). No frameworks.
- Must be served via a local HTTP server (`python -m http.server`) — `fetch()` of `game.py` fails on `file://` due to CORS.
- No build step, no bundler. Keep it simple — this is a solo AI-assisted project, not a production app.

## Core design constraints (do not violate without asking)
- **No idle/wait-timer mechanics.** No countdowns, no "wait 30 min for upgrade." Everything is either an active click or a continuous passive rate — never a timer gate.
- **Mobile-friendly**, responsive, playable in a browser.
- Visual style: **text/numbers first** (no icons yet), but structure code so icons/images could be layered in later without a rewrite.
- Button press gives visible feedback (darkens briefly on click, ~120ms).

## Game concept
Universal-Paperclips-style incremental game, solar-system themed. Player starts clicking to gather a resource on Earth, unlocks automation, then expands outward through the solar system.

**Core loop progression:** click → automation → multi-resource economy → ecology tension → research-gated expansion → trade → terraforming → endgame.

### Key systems
1. **Resources** — named per planet (e.g. Iron, Water on Earth), not abstract points. Numbers can go into scientific notation at scale.
2. **Ecology system** — one global sustainability meter.
   - Below 10% health: 25% output penalty.
   - At 0% health: production halts entirely until back to 10%.
   - Recoverable by shipping in materials from an already-stabilized planet (ties into trade system).
   - Certain buildings cost resources to build but improve ecological health / contribute to terraforming.
3. **Research system** — NOT strictly linear planet-by-planet. Research unlocks "distance tiers"; reaching a tier can open multiple bodies in parallel (e.g. Jupiter's moons together). Some buildings require resources only found on specific other planets (e.g. gas giant buildings need Mars materials) — this is what makes trade matter.
4. **Trade system** — resource exchange between active planets. First introduced as a 2-planet mechanic, later extended to more.
5. **Governor system** — when the player leaves a planet, it doesn't go idle-silent; the player sets priorities + a resource budget, and a "governor" manages it passively while away.
6. **Terraforming** — a per-planet progress bar filled by sustained economic/ecological balance (not a separate grind resource).
7. **Manual clicking** — relevance fades as automation kicks in per-planet, but re-becomes relevant again on each *new* planet (small structural loop, not literal one mechanic reused forever).
8. **Gas giants** — reuse the standard building system, reskinned; not a separate subsystem.
9. **Win condition** — 100% completion across the solar system triggers a soft "win" state; game remains playable sandbox-style afterward.
10. **Balance philosophy** — soft punishment for imbalance, always recoverable. No dead-end/unwinnable states.

## Milestone plan (11 milestones, weeks 1–11 of 13; weeks 12–13 are buffer)

| Wk | Milestone | Content |
|----|-----------|---------|
| 1 | Core loop | Click Earth resource, dark-button feedback, basic mobile UI — **DONE** |
| 2 | First automation | Auto-generators, continuous passive rate, no timers — **DONE** |
| 3 | Ecology system | Global sustainability meter, penalty curve, ecology-improving buildings — **DONE** |
| 4 | Research system v1 | Tech-tree/distance framework, first unlock tier (Moon or Mars) — **DONE** |
| 5 | Planet transition + governor | Travel to new planet, governor priority/budget system — **DONE** |
| 6 | Second planet resource loop | New resource, reuse week 2/3 systems — **DONE** |
| 7 | Trade system v1 | Resource exchange between two planets, ties into ecology recovery |
| 8 | Terraforming | Per-planet progress bar |
| 9 | Research tier 2 | Parallel-unlock tier, extend trade + governor to more planets |
| 10 | Gas giant buildings | Reskinned building system + Mars-material dependency |
| 11 | Full system endgame | 100% completion win-state, final balance pass |

**Important:** milestones can be built ahead of schedule, but should be *tagged* (`git tag milestone-0N`) at actual completion time and *not publicized* (Instagram/devlog) until their assigned week. Don't backdate anything — the tag date must be real. This is a deliberate anti-burnout pacing strategy, not a submission deadline system.

## Working conventions
- Commit + tag at the end of each milestone: `git commit -m "Milestone N: <name>"` then `git tag milestone-0N`.
- Keep `game.py` as the single source of game logic where reasonable; split into modules only once it gets unwieldy.
- Public evidence: Instagram (BCM114, audience-facing) + WordPress devlog on ah752bcm.wordpress.com under a new tag/category (BCM206, process-facing) — not part of this codebase, but milestones should produce something screenshot/clip-worthy.
- Prefer asking before large architecture changes — this project intentionally avoids scope creep beyond what's listed above.
