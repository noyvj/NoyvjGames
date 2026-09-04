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

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Single-run core loop | Scheduled event sequence, resource allocation between events, event damage resolution. Tests: event scheduling, allocation logic, damage resolution | Done |
| 2 | Run scoring + skill-tree currency generation | End-of-run score, currency earned based on performance. Tests: scoring formula, currency calculation | Done |
| 3 | Skill tree structure | Persistent tree of unlockable resilience bonuses, spend currency between runs. Tests: unlock logic, currency spend/balance tracking | Done |
| 4 | Bonus application to new runs | Unlocked skill-tree bonuses actually modify the next run's starting conditions/event resolution. Tests: bonus application across a sample run | Done |
| 5 | Hope-angle payoff | A clear "look how far you've come" comparison across runs (e.g. run 1 vs. run 5 outcome, same event sequence, visibly better handled) | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the skill tree risked feeling like abstract stat-boosting disconnected from the climate-adaptation lesson, and repeated runs risked feeling grindy rather than purposeful.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** real-practice grounding text on each skill-tree unlock, and deterministic per-event severity variation (deliberately locked off on a player's first run so it doesn't undermine the existing run-comparison hope angle).

**Open testing question:** does the "look how far you've come" run-1-vs-run-5 comparison actually land? Do unlock costs feel earned rather than grindy?

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: B (diversified event types) + C, tentative/stretch (legacy system).**

- **Diversified event types:** broaden beyond weather events to include other resilience-relevant shocks (e.g. supply-chain disruption, infrastructure failure unrelated to weather) so "resilience" reads as a broader societal capacity, not just storm-proofing. Same scheduled-event structure as the core loop — additional event variety, not a new system.
- **Legacy system (stretch — build only if time allows, after the diversified events are solid):** each completed run leaves behind a small narrative or visual trace that carries into the next run beyond the skill-tree currency — e.g. a short line of flavor text referencing what the previous run overcame, or a visual marker in the settlement referencing its history.
- **Visual polish for this pass:** new event types should each get a distinct visual/audio signature so they're immediately distinguishable from weather events at a glance, not just a different label on the same event UI.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** repeated runs risk sliding into boredom if the skill tree makes the player meaningfully stronger while event difficulty stays flat — skill outpacing challenge is the textbook flow-boredom failure mode. Aftermath's skill tree only ever made runs easier (starting resources, starting resilience, flat mitigation) while the Pass-2 event schedule's severity variation had no relationship to how much the player had invested.

**Built in response:** event-severity variation now widens with the player's accumulated skill-tree strength (`skill_tree_strength()`, the count of unlocked resilience skills). The variation band stays centered on 1.0 — a stronger skill tree isn't punished, and the run-1-vs-latest-run hope-angle comparison stays meaningful — but the spread grows per unlocked skill (`SEVERITY_VARIATION_RANGE_PER_SKILL`), so a fully-invested run can hit both milder lows and notably harsher highs than a skill-strength-zero run ever sees. This is difficulty-curve tuning on the existing severity-selection function from Pass 1/2, not a new mechanic: same event schedule, same event types, wider unpredictability at the high end of investment so a maxed-out skill tree still has to react to something, not just execute an already-solved run.

Deliberately scoped narrow: only the severity-variation function changed. Event *type* selection and the fixed `EVENT_SCHEDULE` order/length were left untouched, since extending or reordering the schedule per skill level risked breaking run-length assumptions baked into the existing Milestone 4/5 tests (and, per Pass 1's existing rule, run 1 still gets flat severity regardless of skill strength — the very first run is unaffected by this change).

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Adaptation — building resilience to climate impacts already locked in — is treated by climate science and policy as its own necessary response, not a fallback for failed mitigation. Real communities that invested early in resilient infrastructure have documented, measurable payoffs. Aftermath's resource-allocation choices and its "how far you've come" comparison are modeled on that same idea.

**Mechanic tie-in:** The skill tree's resilience/growth split mirrors a real, documented tradeoff facing infrastructure investment: pay up front for resilience, or grow capacity and risk being caught underprepared.

**Sources:**
1. [IPCC AR6 Working Group II — Climate Change 2022: Impacts, Adaptation and Vulnerability](https://www.ipcc.ch/report/ar6/wg2/) — the authoritative global reference on adaptation as a distinct climate response.
2. [World Resources Institute — Accelerating Climate-resilient Infrastructure Investment in China](https://www.wri.org/research/accelerating-climate-resilient-infrastructure-investment-china) — a real resilience-infrastructure investment case study.
3. [World Resources Institute — Driving System Shifts for Climate Resilience (Bhutan, Ethiopia, Costa Rica)](https://www.wri.org/research/driving-system-shifts-climate-resilience-case-studies-transformative-adaptation-bhutan) — real communities' documented adaptation journeys, backing the "look how far you've come" hope angle.
4. [EU Mission on Adaptation to Climate Change — Success Stories](https://mission-adaptation-portal.ec.europa.eu/stories-0_en) — a running collection of real municipal adaptation wins.

All four links verified live before merging. Source 4's original URL (`climate-adapt.eea.europa.eu`) permanently redirected to the EU's newer Mission Adaptation Portal during verification — updated to the canonical destination above. Source 1 (IPCC) returns 403 to automated fetchers (bot-protection) but was confirmed loading correctly in a real browser.

## Audit fix — stale-save double-award guard

Code-quality audit pass found a real exploit at the seam between this game's
two persistence layers (localStorage skill tree/run history vs. the shared
save widget's per-run `get_state()`/`load_state()`): saving mid-run (before
the last scheduled event), playing on to a normal completion (which awards
knowledge points/history/legacy as usual), and then reloading that same
still-valid save code afterward would restore the run to its pre-completion
`event_index`. Resolving the final event again from that reloaded snapshot
re-triggered the completion payout a second time for the same run — free
knowledge points and a duplicate `run_history` entry, just from reloading an
old save. `load_state()`'s existing scope boundary (skill tree/history/legacy
are untouched by a load) was correct; the bug was that `resolve_next_event()`
had no persistent memory of *which run_number had already paid out*, only
the in-memory `RunState` instance's own `event_index`, which a reload can
freely rewind.

**Fix:** a new localStorage key (`aftermath_highest_awarded_run_v1`) tracks
the highest `run_number` that has ever been awarded, independent of any one
`RunState` object. A run's completion only pays out if its `run_number`
exceeds that persisted high-water mark, and updates it when it does — so
reloading and re-resolving an already-awarded run's old snapshot is now a
no-op payout-wise, while a genuinely new run (higher `run_number`) still
awards normally. Deliberately not folded into `get_state()`/`load_state()`'s
round trip — same reasoning as the skill tree/history/legacy split already
documented below, this is derived, persistent-by-run-number bookkeeping, not
per-run state that should travel with a save code. Covered by two new tests
in `tests/test_save_system.py`.

**Follow-up (second audit pass):** the high-water-mark guard above created
its own sibling bug in `start_new_run()`, which derived the new run's
`run_number` from the *current* RunState's own `run_number + 1` — but that
current RunState can itself be a stale, reloaded snapshot sitting behind
runs that have since completed and been awarded elsewhere in the session.
Loading an old, still-incomplete save (nothing exploitative — just resuming
an earlier snapshot) and then starting a new run from it could hand out a
`run_number` that a later run had already completed and been awarded for,
silently blocking the guard from ever awarding that genuinely new,
never-before-played run. Fixed by deriving the new run's number from
`max(run.run_number, highest_awarded_run) + 1` instead, so it can never
collide with an already-awarded run regardless of what stale snapshot
happens to be loaded when `start_new_run()` is called. Covered by a new
test in `tests/test_save_system.py`.

Also fixed this pass (both purely cosmetic, no functional/balance change):
the module docstring still described the game as only having Milestone 1's
single-run loop built, with scoring/skill tree/comparisons "landing in
later milestones" — stale now that all 7 milestones are complete, updated
to describe the finished game. `EVENT_ICON`'s `storm` entry carried an
explicit U+FE0F variation selector to force emoji rendering while the other
four entries didn't; added it consistently across all five so rendering
doesn't vary by platform/font depending on which event icon is shown.

## Visual pass — space theme (site-wide design system rollout)

Adopted the shared space-themed visual language already shipped to the hub
and SOL: `shared/space-bg.css`'s starfield+nebula background
(`<div class="space-bg">` markup right after `<body>`), a glass-panel
treatment (translucent gradient + `backdrop-filter: blur()` + soft violet
border + drop shadow) on `#game` and every `.section`/`.context-blurb`,
gradient buttons with a glossy top highlight and a `brightness(1.1)` hover
state, a glowing gradient meter fill, and a gradient-glow `<h1>` title
matching the hub/SOL treatment. Purely a CSS/HTML property-value change —
no selector was renamed and no `game.py` DOM code touched.

**Deliberately left alone:** the `event-category--weather` (blue) and
`event-category--non-weather` (amber) hues, and the mitigation meter's
green, are exactly the colors a player already relies on to tell things
apart at a glance — only a matching `text-shadow`/`box-shadow` glow was
added around each, the hue itself is untouched. No "no animation" test or
CLAUDE.md constraint exists for this game (checked `tests/` and the shared
`games/climate-quartet-plan.md` — the quartet's standing visual-polish
requirement actually asks for eased state transitions, not against them),
so the existing `transition: filter`/`width` rules were kept and a couple
more added for button hover states; nothing in `shared/space-bg.css`'s own
drift animation was touched either way. Full pytest suite (116 tests)
stayed green throughout; verified live via a local server — starfield/glass
panels render, Invest in Resilience / Face Next Event still update
resources/resilience/event progress/mitigation bar correctly, and the only
console errors present are the pre-existing site-wide ServiceWorker
registration quirk also reproducible on the unmodified hub page.

## Tech notes

- Python/Pyodide, per root conventions.
- **Persistence decision (revised from the original plan):** the plan originally called for Neon-backend persistence, written under the assumption this might run in a sandboxed Claude Artifact where browser storage is unavailable. It doesn't — this is a normal static site with no accounts/auth system anywhere in the project (SOL/Canopy/Grid/Tide are all anonymous, shared-per-browser). Persisting to Neon would mean inventing an anonymous-device-identity scheme just to key rows to a browser with no other identity, plus new backend surface on the shared ratings service. Confirmed with the user: **use `localStorage`** instead — same per-browser persistence, no new backend surface. Trade-off: doesn't sync across devices, and clearing browser data resets it.
- Keep run-state and skill-tree-state as separate objects from the start — they're tested and persisted differently.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag aftermath-milestone-0N`.
- Update the milestone table Status as work happens.
