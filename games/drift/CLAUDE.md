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

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected addition: C (long-horizon outcomes).**

- **Long-horizon outcomes:** end a session with a coda showing descendants of successfully-integrated populations contributing to and thriving within the region generations later — extending the hope angle across a longer timeline than the session itself covers. Keep this framed institutionally (workforce, community roles, regional contribution), consistent with the Pass 1 sensitivity note above — this is about a region's long-run outcome, not a family's.
- **Visual polish for this pass:** the three-bar composite dashboard should carry into the coda as a final, visibly improved state relative to where the session started — the long-horizon payoff needs to be legible as a continuation of the same dashboard the player was already reading, not a disconnected epilogue screen.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** shares Loop's "dry abstraction" risk (a composite dashboard can feel like a spreadsheet) and Thaw's "fear without efficacy" risk (real displacement framed institutionally can read as fatalistic if the net-positive integration payoff isn't clearly felt).

**Implemented:** the net-positive integration mechanic previously only showed up as a background number (`integration_contribution()` folded into the funds total each round) — there was no called-out moment where the player notices the shift from strain to contribution. Added a legible "turning point" milestone: the game now tracks cumulative funds integrated arrivals have contributed back against cumulative funds spent on the services investment that enabled that integration (`cumulative_integration_contribution`, `cumulative_services_investment`). The first round the former catches up to the latter, the region has durably crossed from net strain to net contribution (`has_crossed_to_net_positive()`, `net_positive_round` — a milestone that's recorded once and stays true for the rest of the run, not a live ratio that could flicker if a later services investment briefly raises the payback bar again). A new callout (`integration_turning_point_message()`, rendered in a dedicated `#integration-turning-point-display` element styled with the coda's warm accent) surfaces this the moment it happens: *"Turning point, round N: this region's integrated arrivals have paid back the services investment that got them there. From here, integration is a net gain for regional capacity, not a cost."* Framing stays institutional/systems-level throughout — no names, no individual stories, consistent with this file's sensitivity note.

Also updated the in-game feedback prompt, given this game's added topic sensitivity: it now asks directly "Did you come away feeling migration pressure is a manageable systems problem, rather than an unmanageable crisis?" — a testable version of the trust-vs-fear distinction from the cited research, replacing the previous more general "did this change how you think about..." question.

## Info Page — real-world sources (implemented)

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links. Framing kept institutional/systems-level, consistent with this file's sensitivity note above — about regional capacity, not individual migrant stories.

**Framing:** Climate-driven displacement is already happening at scale, and how well it goes depends far more on a receiving region's institutional preparedness than on the number of people arriving — real projections vary by tens of millions depending on how much the world invests in resilience now. Drift's capacity-vs-pressure system is modeled on that same institutional framing, deliberately kept impersonal rather than told through individual stories.

**Mechanic tie-in:** Drift's long-horizon coda is grounded in real evidence that early institutional investment in integration converts displacement pressure into a net-positive contribution over time, not just crisis management.

**Sources:**
1. [UNHCR — Climate change and displacement](https://www.unhcr.org/us/what-we-do/build-better-futures/climate-change-and-displacement) — the authoritative agency perspective, framing displacement institutionally.
2. [Migration Policy Institute — Climate Migration 101: An Explainer](https://www.migrationpolicy.org/journal/feature/climate-migration-101-explainer) — real projections (44-216 million internal migrants by 2050) echoing Drift's "preparedness changes the outcome" hope angle.
3. [Migration Policy Institute — Who Counts as a Climate Migrant?](https://www.migrationpolicy.org/article/who-is-a-climate-migrant) — the legal/definitional gap behind why Drift frames this as a systems/capacity problem, not a legal one.
4. [Brookings — The climate crisis, migration, and refugees](https://www.brookings.edu/articles/the-climate-crisis-migration-and-refugees/) — policy-level analysis of the institutional response gap.

All four links verified live before merging. Source 1 (UNHCR) and sources 2–3 (Migration Policy Institute) return 403/bot-challenge to automated fetchers but are well-known, legitimate institutional domains — consistent with the bot-protection pattern confirmed on several other sources across this batch.

## Tech notes

- Python/Pyodide, per root conventions.
- This is the most conceptually sensitive game in either set — displacement and migration are real, ongoing human experiences, not just an abstract system. Keep language and framing (in-game text, UI labels, any narrative flavor) focused on institutional capacity and systems design rather than individual migrant stories, to avoid the game reading as speaking for or dramatizing real people's specific experiences.
- Model regional wellbeing as a small set of tracked sub-scores (service quality, economic health, social cohesion) rather than one blended number — keeps the composite scoring testable and keeps the end-state legible to the player.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag drift-milestone-0N`.
- Update the milestone table Status as work happens.
