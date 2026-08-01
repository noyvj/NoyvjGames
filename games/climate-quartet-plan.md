# Climate Quartet — Root Plan

**Context for Claude Code:** This is the planning root for four small climate-awareness games that together form the BCM114 Round 1 Digital Artefact (due Sunday 4 September 2026, 5pm). They sit inside the same portfolio hub (GitHub Pages) as SOL and Trade Empire. Round 2 will be a story-based game on a different global issue — do not carry climate framing into Round 2 planning.

Read this file first in any session touching more than one game. Each game also has its own pre-build plan (`games/<slug>/<slug>-plan.md`, becoming `games/<slug>/CLAUDE.md` once building starts) — read that before working on that specific game. Hand off one milestone at a time; don't try to re-derive the whole plan from scratch each session.

## Why four games, not one

BCM114's outline requires "one Digital Artefact project" per round responding to a framing theme — but explicitly allows running multiple concurrent projects ("Run several at once if you like... test ideas and see what pulls you in"). The four games here are being treated as **one DA effort with a shared theme (climate action) expressed through four independent prototypes**, not four unrelated assignments. The Contextual Report Blog for Round 1 should discuss them as a set: one theme, four mechanics, each teaching a different facet of the same problem.

**Not all four need to finish.** Priority order below reflects build complexity, so whatever gets finished forms a complete, coherent submission on its own — this isn't four half-built games, it's N complete games out of a planned four.

## Shared theme: Climate Action (SDG 13)

Each game targets a **different lever of climate response**, so the four together cover more ground than any one game could alone:

| Game | Climate issue | Response type | Core lesson |
|---|---|---|---|
| Grid | Energy transition / emissions | Mitigation | Delay compounds cost; clean energy gets cheaper if you invest early |
| Canopy | Deforestation / carbon sinks | Mitigation | Restraint compounds better than extraction, just more slowly |
| Tide | Ocean acidification / sea-level rise | Mitigation + delayed consequence | Damage from today's choices arrives late — investing now buys tomorrow |
| Aftermath | Climate adaptation / resilience | Adaptation | Adaptation is a distinct, necessary response, not a consolation prize for failed mitigation |

**The hope angle (non-negotiable across all four):** every game must give the player a path where investment pays off — none of these should end in "everything is doomed." The point is to leave players with agency, not despair. Build a visible "things are recoverable if you act" signal into each game's end-state or ongoing feedback, not just a doom clock.

## Build order (simplest → most complex)

1. **Canopy** — simplest mechanic (clicker + grid of tiles), build first to prove the shared framework
2. **Grid** — turn-based tier system, moderate complexity
3. **Tide** — grid redraw for sea-level rise adds visual complexity
4. **Aftermath** — meta-progression skill tree between runs is the most complex system

Build in this order so that if time runs out, you still have the simplest-to-most-complex subset finished, not a random scatter of half-done systems.

## Shared technical conventions

- **Language:** Python via Pyodide for all four by default. **Tide is the one candidate for a JS/Canvas fallback** if the grid-redraw rendering turns out to be painful in pure Pyodide — decide this at Tide's first milestone, not before.
- **Testing is mandatory for every game, every milestone.** Use `pytest` for core game-state logic (resource updates, meter thresholds, win/loss or scoring conditions). UI/rendering code doesn't need tests; state transitions do. No milestone is "done" without its tests passing.
- **Feedback hook:** every game ends (or reaches a natural pause point) with a short 1–2 question in-game prompt — e.g. "Did this change how you think about [issue]? Yes/No" + optional one-line comment. Pipe this to the existing Neon/FastAPI ratings backend (extend the existing schema with a `game_id` and `response` field rather than building a separate system). This is in addition to, not instead of, manual playtesting via Discord/LinkedIn/peer discussion.
- **Hub integration:** each game gets its own page/route in the existing GitHub Pages hub, linked from the main hub nav alongside SOL and Trade Empire.
- **Milestone structure:** mirrors SOL's format — numbered milestones, each a complete checkpoint (playable state + tests passing), not time-boxed. Session length per game is not fixed; let each game be as long as its content naturally supports.

## Per-game files

- `games/grid/grid-plan.md`
- `games/canopy/canopy-plan.md`
- `games/tide/tide-plan.md`
- `games/aftermath/aftermath-plan.md`

Each contains: concept summary, hope-angle specifics, core loop, milestone checklist, tech notes, testing notes, feedback hook spec. Once a game is ready to start building, move its plan into `games/<slug>/CLAUDE.md` and build there — same pattern as SOL and Trade Empire.
