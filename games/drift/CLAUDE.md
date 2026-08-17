# Drift — Climate Migration & Displacement Game

**Read `../climate-quartet-2-plan.md` first for shared conventions.** This file is Drift-specific only. **Build last** in this set — it's the most systems-heavy and longest-timeline game across both sets; only tackle it once the other patterns are proven.

## Concept

As sea-level and extreme-weather pressure rise over a long timeline (conceptually related to Tide's world-state, though Drift can stand alone), populations in vulnerable regions are displaced. The player manages a **receiving region's response** — building capacity, integration systems, and infrastructure to absorb displaced populations well versus badly. This is less about a single meter and more about how prepared institutions turn a crisis into a manageable transition instead of a chaotic one.

## Function tags: Futures on current path + Systems to combat

Drift does double duty: it simulates a downstream future consequence of unaddressed climate change (displacement), *and* it's fundamentally about designing the systems (housing capacity, integration infrastructure, services) that determine whether that future is a crisis or a manageable transition. Both framings should show up in how this game gets discussed in the Contextual Report Blog.

## Climate issue & hope angle

**Issue:** climate-driven migration and displacement, and the institutional capacity to absorb it.
**Hope angle:** the entire point of this game is that displacement doesn't have to mean crisis — a well-prepared region can absorb significant population pressure smoothly, while an unprepared one turns the same pressure into collapse. The player should be able to reach a genuinely thriving, successfully-integrated end-state through good institutional investment, proving that the "crisis" framing common in real-world migration discourse is a preparedness failure, not an inevitability.

## Core loop

- Turn-based rounds across a long timeline. Displacement pressure (number of people arriving) rises on a schedule loosely tied to background climate severity, largely outside direct player control.
- Player allocates regional resources across: housing capacity, integration services (language, employment, education access), and general infrastructure capacity (utilities, transport, healthcare).
- Under-investment relative to arrival pressure causes visible strain (service shortfalls, social/economic friction) — not a fail-state, but a visibly worse regional outcome that compounds if left unaddressed.
- Over time, well-integrated arrivals should contribute back to regional capacity (economic participation, workforce contribution) — the game should model integration as eventually *net-positive*, not a permanent drain, which is the core of the hope angle.
- Scoring: long-run regional wellbeing (a composite of service quality, economic health, and social cohesion) rather than a single number — reflects that "successful adaptation" here is multidimensional, not just "did you survive."

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core allocation loop | Resource allocation across housing/services/infrastructure, round progression. Tests: allocation logic | Done |
| 2 | Displacement pressure schedule | Arrival numbers rising over the timeline, loosely tied to background severity. Tests: pressure-schedule calculation | Done |
| 3 | Strain vs. capacity system | Visible consequences when investment lags behind arrival pressure, without a hard fail-state. Tests: strain-calculation and threshold logic | Done |
| 4 | Integration payoff loop | Well-integrated population contributing back to regional capacity over time (net-positive modeling). Tests: contribution-calculation formula, timing/lag logic | Done |
| 5 | Composite wellbeing scoring | Multidimensional scoring across service quality, economic health, social cohesion. Tests: composite scoring formula across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: given how sensitive the subject matter is (real displacement, real people), this game risked feeling either too dry (an allocation spreadsheet) or, if over-corrected, too narrativized in a way that dramatizes individuals rather than institutions.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a three-bar composite wellbeing dashboard (services / economy / cohesion), a mid-run plain-language checkpoint summary, and short case-study-style context blurbs about real regions that handled climate migration well institutionally — framed at the policy/systems level, not as individual personal stories.

**Open testing question:** can players identify which of the three sub-scores is lagging and explain why? Is the "integration is eventually net-positive" mechanic actually felt, or does it stay invisible in the background math?

## Iteration Notes — Pass 2 (not yet implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected addition: C (long-horizon outcomes).**

- **Long-horizon outcomes:** end a session with a coda showing descendants of successfully-integrated populations contributing to and thriving within the region generations later — extending the hope angle across a longer timeline than the session itself covers. Keep this framed institutionally (workforce, community roles, regional contribution), consistent with the Pass 1 sensitivity note above — this is about a region's long-run outcome, not a family's.
- **Visual polish for this pass:** the three-bar composite dashboard should carry into the coda as a final, visibly improved state relative to where the session started — the long-horizon payoff needs to be legible as a continuation of the same dashboard the player was already reading, not a disconnected epilogue screen.

## Tech notes

- Python/Pyodide, per root conventions.
- This is the most conceptually sensitive game in either set — displacement and migration are real, ongoing human experiences, not just an abstract system. Keep language and framing (in-game text, UI labels, any narrative flavor) focused on institutional capacity and systems design rather than individual migrant stories, to avoid the game reading as speaking for or dramatizing real people's specific experiences.
- Model regional wellbeing as a small set of tracked sub-scores (service quality, economic health, social cohesion) rather than one blended number — keeps the composite scoring testable and keeps the end-state legible to the player.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag drift-milestone-0N`.
- Update the milestone table Status as work happens.
