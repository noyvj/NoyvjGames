# Aftermath — Climate Adaptation & Resilience Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Aftermath-specific only. **Build last** — the meta-progression skill tree is the most complex system of the four; only tackle it once the other three patterns are proven.

## Concept

Unlike the other three (all mitigation-focused), Aftermath treats climate change as a given, not a variable the player controls. Extreme weather events (floods, heatwaves, storms) hit on a schedule within each run. Between events, the player spends resources on resilience infrastructure vs. immediate growth. Runs are short and repeatable; a **skill tree/tech tree persists between runs**, representing accumulated societal adaptation knowledge — each run, the player starts a little more capable than the last, even though the climate events themselves don't get easier.

## Climate issue & hope angle

**Issue:** adaptation and disaster resilience as a distinct climate response — not mitigation, not a failure state, but its own necessary category.
**Hope angle:** the persistent skill tree *is* the hope mechanic — every run, even a rough one, contributes permanent capability for the next. The game should make clear that resilience is cumulative and never wasted, even when a single run goes badly. This is the most direct "long-term societal progress is real" message of the four.

## Core loop

- **Repeated short runs** (not full permadeath roguelite — that's more scope than needed). Each run: a settlement facing a scheduled sequence of extreme weather events, with resource-allocation decisions between events (build resilience infrastructure vs. pursue growth).
- Events are the same *type* of climate reality each run (floods, heatwaves, storms recur), but the settlement's baseline capability shifts run-to-run based on the skill tree.
- **Skill tree lives outside the run loop** — unlocked using a currency earned during runs (e.g. "resilience knowledge points"), persists across sessions, and pre-equips future runs with permanent bonuses (faster infrastructure builds, reduced event damage, better resource yields).
- A run "ends" when its scheduled event sequence completes — not a win/loss framing, more a "how well did the settlement weather this run" score that also feeds skill-tree currency.

## Milestones

1. **Single-run core loop** — scheduled event sequence, resource allocation between events, event damage resolution. Tests: event scheduling, allocation logic, damage resolution.
2. **Run scoring + skill-tree currency generation** — end-of-run score, currency earned based on performance. Tests: scoring formula, currency calculation.
3. **Skill tree structure** — persistent tree of unlockable resilience bonuses, spend currency between runs. Tests: unlock logic, currency spend/balance tracking, persistence across sessions (local storage substitute — no browser storage per artifact rules if this ends up in an HTML/React context; use in-memory/session state or your existing Neon backend for persistence instead).
4. **Bonus application to new runs** — unlocked skill-tree bonuses actually modify the next run's starting conditions/event resolution. Tests: bonus application across a sample run.
5. **Hope-angle payoff** — a clear "look how far you've come" comparison across runs (e.g. run 1 vs. run 5 outcome, same event sequence, visibly better handled).
6. **In-game feedback prompt** — piped to Neon backend per root conventions.
7. **Visual/UI pass + hub integration.**

## Tech notes

- Python/Pyodide, per root conventions.
- **Persistence matters more here than in the other three** — the skill tree needs to survive between runs within a session at minimum, and ideally between visits. Use the existing Neon/FastAPI backend for this rather than browser storage (browser storage APIs are unsupported in the artifact/hub environment).
- Keep run-state and skill-tree-state as separate objects from the start — they're tested and persisted differently.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag aftermath-milestone-0N`.
- Update the milestone table Status as work happens.
- Once ready, move this file into `games/aftermath/CLAUDE.md` and build there — same pattern as SOL and Trade Empire.
