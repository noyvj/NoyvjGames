# Grid — Energy Transition Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Grid-specific only.

## Concept

You manage a regional power grid across a series of rounds. Demand grows every round. You choose which plant types to build or retire. Fossil plants are cheap and reliable early; renewables cost more upfront but get cheaper over time as you invest in them (mirrors real-world cost curves — this is the mechanic that carries the lesson, not a stat you show the player directly).

## Climate issue & hope angle

**Issue:** energy-sector emissions, the single largest lever in real-world climate mitigation.
**Hope angle:** the game must show that early investment in renewables pays off — cheaper energy, fewer disruptions, a visibly better late-game position than a fossil-heavy strategy. A player who leans renewable early should end up in a *better* position than one who doesn't, not just a "cleaner but harder" one. This is the antidote to "sustainability = sacrifice."

## Core loop

- Turn-based, discrete rounds (not real-time ticking).
- Each round: demand rises by some amount. Player allocates budget to build/retire/upgrade plants.
- Plant tiers (start simple, expand if time allows): Coal, Gas, Nuclear, Solar, Wind, Hydro.
- Renewable costs decrease the more the player has already invested in them (learning-curve effect) — this needs to be visible/legible to the player, not hidden math.
- Emissions accumulate as a rising background meter tied to the fossil-heavy share of the grid.
- **No hard fail-state/game over.** Instead, rising emissions trigger progressively more frequent/severe disruption events (brownouts, damaged plants, cost spikes) — the game gets *harder to manage*, not suddenly lost. This is what teaches "delay compounds cost" without punishing exploration.
- Scoring/win condition: sustained grid stability over N rounds, weighted by how clean the grid became over time (not just final-state cleanliness).

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Core state loop | Demand growth, budget allocation, plant build/retire, round progression. No emissions or events yet. Tests: state transitions for budget spend, plant count changes, demand growth formula | Done |
| 2 | Emissions meter + cost curve | Emissions accumulate based on grid composition; renewable costs decrease with cumulative investment. Tests: emissions calculation, cost-curve decay formula | Done |
| 3 | Disruption events | Brownouts/damage triggered probabilistically by emissions level, scaling in frequency/severity. Tests: event-trigger thresholds, damage application | Done |
| 4 | Scoring + hope-angle payoff | End-of-run scoring that rewards sustained clean transition, not just final snapshot. Tests: scoring calculation across sample playthrough logs | Done |
| 5 | In-game feedback prompt | End-of-run 1–2 question prompt, piped to Neon backend per root conventions | Done |
| 6 | UI/visual pass + hub integration | Tier icons, meter displays, event notifications. Polish only after 1–5 are solid | Done — all 6 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the renewable cost-curve mechanic (the actual lesson) risked being invisible as pure numbers — a player could succeed without ever consciously registering "investing early made things cheaper."

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** the live two-line emissions/renewable-cost trend graph, and a short factual context blurb on first unlocking a renewable tier. Weather-variability-on-renewable-output was considered and deliberately skipped as scope discretion.

**Open testing question:** does a first-time player, unprompted, notice that early renewable investment made later rounds easier? The in-game feedback prompt asks directly: "Did investing early feel like it paid off?"

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: A (global comparison) + B (infrastructure age/vulnerability).**

- **Global comparison:** at session end, show the player's grid trajectory (emissions curve, clean-energy share over time) plotted against a real-world average trend line, pulled or hardcoded from public data. A secondary comparison against other players' aggregate outcomes (via the ratings backend) is a nice stretch goal, but the real-world benchmark is the priority.
- **Infrastructure age/vulnerability:** plants accumulate an age value each round; older plants become progressively more failure-prone (higher chance of costly breakdown events) unless maintained. Adds a maintenance-budget dimension separate from the build/retire decision, reinforcing "cheap now, costly later" from a different angle.
- **Visual polish for this pass:** the two-line graph should carry the global-comparison line as a third, visually distinct series (three lines max, stay legible). Aging plants should show a visible wear state (icon degrades slightly) so vulnerability is seen before it's felt as a breakdown event.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Electricity generation is one of the largest single sources of global emissions, and the fastest way to cut it is building out cleaner capacity — not rationing power. Renewables have gotten dramatically cheaper the more of them get built, a real economic trend called a learning curve. That's the same tension Grid asks you to manage: lean into that cheaper long-run path, or lean on familiar fossil capacity.

**Mechanic tie-in:** Grid's cost curve and its global-comparison line are grounded in published wind/solar learning-rate data (roughly 15%/24% cost decline per capacity doubling), not an invented number.

**Sources:**
1. [IEA — Rapid rollout of clean technologies makes energy cheaper, not more costly](https://www.iea.org/news/rapid-rollout-of-clean-technologies-makes-energy-cheaper-not-more-costly) — real-world backing for Grid's central claim that leaning renewable is the cheaper long-run path, not a sacrifice.
2. [Oxford Institute for Energy Studies — A critical assessment of learning curves for solar and wind power technologies](https://www.oxfordenergy.org/publications/a-critical-assessment-of-learning-curves-for-solar-and-wind-power-technologies/) — a balanced, critical look at the same cost-decline concept Grid's core mechanic is built on.
3. [US DOE / Lawrence Berkeley National Lab — Learning a Better Way To Forecast Wind and Solar Energy Costs](https://www.energy.gov/cmei/solar/articles/learning-better-way-forecast-wind-and-solar-energy-costs) — the actual learning-rate figures (wind ~15%, solar ~24% per capacity doubling) behind Grid's cost curve.
4. [IEA — Breakthrough Agenda Report 2025: Power](https://www.iea.org/reports/breakthrough-agenda-report-2025/power) — current real-world electricity cost figures, grounding the global-comparison line.

All four links verified live before merging. Source 2 (Oxford) returns 403 to automated fetchers (bot-protection) but loads fine in a real browser — confirmed the pattern is consistent with several other major institutional domains checked the same way.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** the tiered plant system could drift toward a pure optimization spreadsheet where a player wins by number-crunching without ever registering *why* the renewable path pays off — the emissions meter reading as a side-score rather than the actual mechanism gating disruption risk.

**Found already satisfied:** the fix's core ask — disruption probability/severity scaling directly off the same emissions meter, with no separate difficulty setting, on a soft escalating curve rather than a sudden spike — was already built in Milestone 3 (`disruption_probability()` / `disruption_severity()` are both a direct linear function of `state.emissions`, capped rather than cliffed, and covered by `tests/test_disruption_events.py`). The Pass 2 aging/vulnerability system is a deliberately separate axis (plant neglect, not emissions) and was left untouched here — it's a different lesson, not a rival difficulty curve standing in for the emissions one.

**Actual gap — legibility:** nothing on-screen ever stated in words that rising emissions were the thing driving disruption risk. A player could watch the emissions bar fill and brownouts get worse without the causal link ever being spelled out, which is exactly the "invisible math" failure mode the risk describes. **Built in response:** a live `disruption-risk-display` line under the emissions meter (`game.py`'s new `disruption_risk_message()`, wired into `render()`) that states the current next-round disruption probability in plain language, and calls out when severity has crossed into damage-risk territory — e.g. "Rising emissions mean a 50% chance of a disruption next round." Scoped to this one addition; no changes to the underlying probability/severity math, which didn't need any.

## Audit fix — retire refund exploit

Code-quality audit pass. **Bug found:** `retire_plant()` refunded a flat `PLANT_BASE_COST * REFUND_FRACTION` regardless of a renewable's current (learning-curve-discounted) cost. Once a renewable's cumulative-built discount passed 50% off base cost — solar around 14 units in, well within a normal playthrough — its build cost dropped below the flat refund, turning build-then-immediately-retire into a risk-free, repeatable money exploit (and each cycle nudged the discount further, making later cycles more profitable). **Fixed** by refunding off `plant_cost()` (the plant's current cost) instead of the flat base cost; for fossil/nuclear plant_cost() already equals base cost, so their refund behavior is unchanged. Covered by a new regression test in `tests/test_emissions_and_cost_curve.py`.

## Second audit pass — save/load merge fix + comment cleanup

A more aggressive follow-up pass (fix anything safe, however minor, rather than just flagging it). **Bug found:** `load_state()` replaced `plant_counts`, `cumulative_built` and `plant_age` wholesale (`state.plant_counts = copy.deepcopy(data["plant_counts"])`, etc.) instead of merging key-by-key. A save missing one of those keys — e.g. an older save format from before a plant type existed, or a hand-edited/truncated payload — would drop that key from live state entirely, and every consumer (`render()`, `total_capacity()`, `plant_cost()`, ...) does `state.plant_counts[plant_type]` unconditionally for every type in `PLANT_TYPES`, so the very next access crashed with a `KeyError`, after the save widget had already reported a successful load. Exactly the same bug shape found and fixed this session in Continuum's `restore_city()` and SOL's `deserialize_state()`. **Fixed** with a new `_merge_plant_dict()` helper that writes only the keys present in the saved dict into the live one, leaving any key the save doesn't know about at its current live value. Covered by a new regression test in `tests/test_save_widget.py` that deletes a key from a snapshot before loading it and confirms `render()` no longer crashes.

Also checked and found clean on this pass: no second cost/refund asymmetry (maintenance and aging-breakdown repair costs are debits off a flat base cost, not refunds, so there's no exploit direction the way the flat-refund bug had); no `create_proxy()` leak (all proxies are created once in `setup()`, never per-repaint, since `render()` only updates existing DOM elements rather than recreating any); no dead constants or functions (every module-level constant is read at least once). Two stale comments were corrected: the module docstring still described the Milestone-1-only state ("Emissions, cost curves, and disruption events land in later milestones") despite all of those having since landed in this same file, and a comment above `PLANT_BASE_COST` said renewable cost decay was "Milestone 2's job" as an unfinished forward reference rather than pointing at the `plant_cost()` method that has implemented it since.

## Visual pass — space theme (site-wide design system adoption)

Site-wide visual overhaul pass (hub + SOL already shipped; this game brought in line). Adopted the shared `shared/space-bg.css` starfield/nebula background (added the `<div class="space-bg">` markup + stylesheet link right after `<body>`) and reskinned `#game`/`.section` as glass panels (translucent gradient background, `backdrop-filter: blur`, violet-tinted `rgba(140,160,255,…)` borders, soft drop shadow) matching SOL's reference implementation. `<h1>` got the gradient-glow text treatment; `.tagline`/sub-headings were left plain for hierarchy. `button.secondary`/`button.primary` moved from flat solid backgrounds to two-stop gradients with a glossy inset highlight and a `filter: brightness(1.1)` hover state, keeping every existing `:disabled`/`:active`/`.selected` behavior intact (just re-skinned colors). `.meter`/`.meter-fill--emissions`/`.meter-fill--score` kept their exact existing colors (red/green) and only gained a matching-hue `box-shadow` glow — width/fill logic in `game.py` untouched. Flat gray borders (`.plant-row`, `.context-blurb`) switched to the violet-tinted rgba used elsewhere.

**Deliberately left alone:** `PLANT_ICON` emoji and the `wear-1`/`wear-2`/`wear-3` desaturation filters (aging-vulnerability cue) — these are the actual state-encoding visuals (plant identity + wear) and weren't touched beyond leaving their existing filter/opacity values exactly as they were. The trend-graph SVG stroke colors (`trend-line--emissions`/`--cost`/`--global`) are also untouched — they're a legend, not decoration. No "no motion" test constraint exists in this game's `tests/` (that's a Drift-specific wellbeing-pass decision, confirmed by grepping all 8 climate-quartet games' tests before starting) and the root `climate-quartet-plan.md` visual-polish requirement explicitly calls for eased transitions, so the existing `transition: filter`/`width` rules were kept and a hover-brightness transition was added to buttons — no new hover-lift/transform motion was introduced. `ad-bar.css`/`shared/info-page.css` are shared files out of this game's scope and weren't touched (matches SOL, which also left them flat). Full pytest suite (132 tests) stayed green throughout; live-verified in-browser (starfield/glass panels render, Solar build + Advance Round both work exactly as before, funds/capacity/round state update correctly, no new console errors beyond a pre-existing ServiceWorker-registration warning unrelated to this CSS/HTML-only change).

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the core state (demand, budget, plant counts, emissions, event log) as a plain serializable object — this makes both testing and later save/resume trivial if you want it.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag grid-milestone-0N`.
- Update the milestone table Status as work happens.
