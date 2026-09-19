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

## Achievements + mobile-dock rollout (E1, ACHIEVEMENTS-SYSTEM-DESIGN.md)

19 achievements (`achievements.json`) following SOL/Canopy/Grid's reference
pattern: an in-game toggle + panel, an unlock toast, a hub-dashboard link,
and `achievements_earned` riding `get_state()`. Most checkers read
already-persisted state directly (`run_history`, `skill_tree.unlocked`),
but several genuinely needed new persistent tracked state — "ever invested
in Resilience," "ever finished a run in profit," "ever maxed mitigation,"
and three playstyle achievements (growth-focused/resilience-focused/
balanced) — because those are facts about a specific run's `RunState`,
which resets every new run. Backed by a new small persistent dict
(`achievement_progress`, its own `aftermath_achievement_progress_v1`
localStorage key, alongside the pre-existing skill tree/run history/legacy
events), mutated only inside `RunState.invest_resilience()`/
`invest_growth()`/`resolve_next_event()` at the exact point each fact
becomes true — same five-step defensive pattern as the design doc's
`visited_bodies` example. Knowledge-point achievements needed a similar
fix: `knowledge_points` is a spendable balance that drops on unlock, so a
new `SkillTreeState.lifetime_knowledge` field (only ever increments) backs
the "earn N knowledge points over your lifetime" achievements instead.

E1 (mobile-dock rollout, planning/TODO.md) also landed alongside this:
Resilience/Growth/Face Next Event/Start New Run are now wrapped in one
`#actions-dock` element that `shared/mobile-dock.js` pins to the bottom of
the viewport on mobile, same pattern as Canopy's `#action-panel`/Grid's
`#advance-round-button`. `#actions` itself (the resilience/growth tiles)
is untouched internally.

Hub-side `script.js` registration (`GAMES_WITH_ACHIEVEMENTS`) is out of
scope for this `games/aftermath/`-only dispatch — same caveat every prior
per-game achievements rollout in this hub has noted.

## Per-game backlog pass (E2-E4, E6-E20, planning/TODO.md)

A large batch of small-to-medium features from Aftermath's own TODO.md
checklist (E5 stays parked in `LATER.md`; E1 is the achievements/
mobile-dock entry above):

- **E2/E3 — a fourth and fifth skill node, with prerequisites:**
  Adaptive Growth Practices (+1 starting growth capacity, no prereqs) and
  Mutual Aid Network (+5% flat mitigation, stacking with Resilience
  investment) — the latter requiring both Reinforced Infrastructure *and*
  Community Reserves already unlocked, the tree's first branching node.
  Every `SKILLS` entry now carries a `prereqs` list (empty for the
  original three); a locked skill missing prereqs shows exactly which
  ones in its status line instead of just a disabled button.
- **E4 — legacy system expansion:** a new per-event-type weathered
  *count* (`legacy_event_counts`, its own localStorage key), rendered as
  a chip row under the original single flavor-text line, which is
  untouched.
- **E6 — a third event category:** "social" shocks, represented by one
  new event type, Civil Unrest. Deliberately *replaces* the schedule's
  second Storm slot rather than extending the schedule to 8 events —
  appending a new event first, then discovering it silently broke the
  existing hope-angle/skill-tree "do-nothing baseline eventually scores
  positive" tests (adding ~30 more base damage to an already-tight
  200-resources-vs-total-damage budget), so the fix was to keep the
  schedule at 7 events and swap one slot instead, which if anything
  *reduces* total base damage slightly (32 vs. storm's 50).
- **E7 — reviewing a past run's breakdown:** a new `run_log_history`
  (parallel to, not a replacement for, the existing score-only
  `run_history`) persists every completed run's full event-by-event log;
  a "Review Past Runs" toggle lists them newest-first.
- **E8/E16 — expected-damage preview with numeric severity:** one new
  `expected_next_event_damage()` reuses the exact same deterministic
  formula `resolve_next_event()` will apply, so the preview is exact, not
  an estimate; severity shows as a multiplier (e.g. "1.13× severity,
  severe") instead of only the word.
- **E9 — "X/5 skills unlocked."**
- **E10 — investment confirmation flash:** a brief self-clearing CSS
  animation on the resources readout, only on a successful (funded)
  investment.
- **E11 — proper end-of-run summary:** final resilience/growth/damage
  stats plus the full event-by-event breakdown (reusing E7's rendering
  helper), alongside the original one-line score text.
- **E12 — export/import progress code:** a base64-wrapped JSON blob
  covering everything this game persists *outside* the per-run save
  widget (skill tree, run history, legacy system, achievement progress).
  Deliberately fails soft (returns `False`) on a malformed paste rather
  than raising, unlike `load_state()`'s deliberate strictness — a
  progress code is hand-pasted by a player, not a same-site round trip.
- **E13 — reset skill tree:** an in-UI two-click confirm (click once to
  arm, click again to reset) rather than a browser `confirm()` dialog, so
  it needed no new fake-DOM global. Fully refunds every spent-and-unspent
  knowledge point; `lifetime_knowledge` (the achievement-tracking total)
  is untouched, since a respec shouldn't roll back a lifetime-earned
  counter. Any other action clears the pending confirmation.
- **E14 — skill-unlock toast:** a dedicated toast (visually distinct
  violet identity vs. the gold achievement toast) surfacing the skill's
  `real_practice` text at the exact moment it's unlocked.
- **E15 — settlement-art badges:** five fixed small badge dots along the
  settlement's rooftop line, one per skill, toggled via a
  `settlement-badge--earned` class.
- **E17 — "toughest run yet":** the lowest-scoring completed run.
  `run_history` only ever stored a flat list of scores (no run_number
  alongside each), so the displayed "Run #N" is that run's *position* in
  the list — exact for the overwhelmingly common case, and only an
  approximation in the same rare stale-reload edge case the save-system
  double-award guard already documents elsewhere in this file.
- **E18 — extended-run mode:** an opt-in checkbox that doubles the event
  schedule for the *next* run (`RunState(extended=True)` sets
  `self.schedule = EVENT_SCHEDULE * 2`). Required refactoring every
  schedule-length-dependent RunState method to read `self.schedule`
  instead of the module-level `EVENT_SCHEDULE` directly — a normal run's
  behavior is unchanged since its `self.schedule` is the same list.
  `get_state()`/`load_state()` gained one new `"extended"` field, read
  back with `.get(..., False)` rather than direct key access — the one
  deliberate exception to this save contract's "KeyError on a malformed
  payload" rule, since an old save code genuinely predates the field.
- **E19 — severity visual intensity:** a `severity--mild/typical/severe`
  class layered alongside the existing event-category class everywhere
  an event's severity is shown (last-event, expected-damage, and every
  past-run/end-of-run breakdown line); severe pulses, mild fades.
- **E20 — live knowledge-points preview:** "If the run ended now: N
  knowledge points," reusing the existing scoring formula mid-run.

Full pytest suite went from 154 to 201 tests, all passing; the whole
feature set was also verified live via a local server (Pyodide, not just
the fake-DOM harness) — skill unlock + prereqs + toast + badges, run
completion + past-runs review + end-of-run summary, extended-run mode,
reset-skill-tree's two-click confirm, and a full export/import round
trip all behaved correctly with no console errors.

## Colorblind-safety audit (site-wide goal)

Audited as part of the site-wide colorblind-safety audit (Okabe-Ito-palette method, per Continuum's Phase 5, Canopy's B9, Tide's D11, Grid's C18). Checked `game.py`/`style.css` for any place game-state meaning is conveyed by color alone, including the three event-category colors the earlier space-theme visual pass explicitly noted as deliberately untouched.

**No real hue-only encoding found — no change made.**
- The three event categories — weather (`#6fa8d8`, blue), non-weather (`#d8a24c`, amber), social (`#c07fd8`, purple, added later with E6) — are neither a red/green nor a blue/purple confusion pair with each other, and every place any of them renders (`last-event-display`, `next-event-display`, each `past-run-event` breakdown line) already pairs the color with `EVENT_ICON` + `EVENT_LABEL` text (e.g. "🌊 Flood", "⚡ Civil Unrest") — the color is decoration on top of an icon+text pair that already carries the real distinction, same shape as Tide's D11 finding.
- The mitigation meter (`.meter-fill--mitigation`) is the only meter in this game — a single always-green gradient bar with no red/contrasting "bad" counterpart, same "single-hue bar" shape Tide's and Grid's own audits already found clean.
- The skill tree's locked/unlocked node state (`.skill-node`) uses a padlock emoji (🔒) vs. a checkmark (✓) plus a purple-vs-neutral background — icon-driven, not color-only.
- Severity (`severity--mild`/`--severe`) is opacity/pulse-animation intensity layered on top of whichever event-category color/icon/text is already showing, not a separate color-coded state.
- The gold achievement toast/panel and the violet skill-unlock toast are two different one-at-a-time notification types (never shown side by side needing discrimination), each carrying its own full text.

Matches Tide's D11 precedent: investigated the real candidate list (including the one place a prior CLAUDE.md note already flagged as "deliberately left alone" for a different visual-pass reason) and found no genuine deuteranopia/protanopia or blue/purple confusion pair conveying meaning by hue alone, so no speculative change was made.

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A-/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`) and a reduced-motion
checkbox — toggled from a new "⚙️ Settings" button in the top toolbar
alongside Tutorial/How to Play, rendered into a `.section`-styled panel
matching the existing `#howto-panel`/`#achievements-panel` hidden-until-
opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely (same
discipline as Continuum's `accessibility.js`) — it has no Python dependency
and works even if `game.py` never boots, and it's wired up in `<head>`
before `game.py`'s own `<script>` runs. `style.css` gained a `:root
{ --text-scale: 1 }` custom property read by `html { font-size: calc(16px *
var(--text-scale, 1)) }` (every font-size in this file is already in rem,
confirmed by grep, so scaling the root font-size scales the whole game
uniformly with zero other changes needed) and a blanket
`html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant, additive to the existing
`prefers-reduced-motion` media-query-gated rules already in this file.

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (see `planning/LATER.md`'s "what can you actually do with
audio" standing question), so a sound control here would control nothing
real; the site-wide goal's own description ("text-scale, sound, and
animation toggles") is aspirational and gets corrected in practice by this
scope decision.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`aftermath-text-scale`, `aftermath-reduced-motion`),
deliberately never touching `get_state()`/`load_state()`, since a save code
is meant to be portable across devices/browsers and a local browser's
accessibility preference shouldn't silently override another device's.

Verified live via a local server (fresh port to sidestep an unrelated
browser heuristic-caching quirk in the dev-server setup that had nothing to
do with this game's own code): text-scale increases/resets the whole page's
font size correctly (confirmed via computed `font-size` on `<html>`), the
reduced-motion checkbox collapses a real animated element's
`transition-duration` to ~0, and both settings persist correctly across a
full page reload. Zero new console errors — the only console errors present
are the pre-existing site-wide ServiceWorker registration quirk already
documented above, also reproducible on the unmodified hub page. Full pytest
suite (201 tests, unchanged — `settings.js` is plain frontend JS with no
Python surface) stayed green throughout.

## "What's New" changelog panel (K16, planning/TODO.md, site-wide goal)

A small in-game highlights panel — a curated `changelog.json` (flat list of
`{"date", "entry"}` objects, fetched into the Pyodide boot sequence exactly
like `achievements.json` already is: `window.CHANGELOG_JSON` set before
`game.py` runs, with a filesystem-read fallback in
`_read_changelog_json()` for the pytest harness) rendered into a
hidden-until-opened "📋 What's New" panel — same toggle+panel idiom as the
achievements/past-runs panels, using the past-runs-panel's plain
date+text-card layout rather than achievements' earned/unearned styling,
since a changelog entry has no checkable condition. `CHANGELOG` is sorted
newest-first at load time (defensive against entries being added out of
date order later), and degrades to an empty list rather than crashing the
module on a malformed/missing file, matching `ACHIEVEMENTS`'s own
defensive pattern.

Populated with 9 real highlight entries pulled from this file's own
milestone table and iteration notes above, with dates cross-checked
against `git log` for this game's path — a curated highlights view, not a
full duplicate of this CLAUDE.md or `BCM114-DEV-LOG.md`. Covered by
`tests/test_changelog.py` (catalog sanity, newest-first ordering, toggle
open/close, panel content, no state mutation as a side effect). Full
pytest suite (201 → 210 tests) stayed green throughout; verified live via
a local server — the panel opens, shows all 9 real entries in the correct
order, and there are zero console errors.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited, no change needed. Checked whether a returning player who's
forgotten the tutorial (`shared/tutorial.js`'s spotlight walkthrough) can
still make sense of the permanent UI's non-obvious parts, on top of the
persistent, reachable-any-time `#howto-toggle-button`/`#howto-panel`.

Found the permanent UI already covers every non-obvious mechanic more
thoroughly than any other quartet game audited so far, with no gated or
one-time explanation anywhere:
- Every skill-tree row's `status_el.innerText` permanently states the
  skill's exact numeric effect (e.g. "Reinforced Infrastructure — +2
  starting resilience capacity") and, while still locked, exactly which
  prerequisite skills are still missing (`missing_prereqs()`) rather than
  just a disabled button with no reason given.
- Every skill row's `skill-practice` paragraph unconditionally shows that
  skill's `real_practice` grounding text every render, regardless of
  unlock state — not a one-time toast (E14's toast is a separate,
  additional first-unlock moment, not this text's only home).
- Every action button shows its cost or effect inline in its own label
  ("Invest in Resilience (10)", "Unlock (N)") rather than requiring a
  separate lookup.
- Four section-level `.info-toggle` icons permanently explain the
  deterministic per-run severity pattern, the mitigation cap/formula, the
  knowledge-points-per-run formula, and Growth's "no damage mitigation,
  just flat income" trade-off — the same explanations a one-time-only
  callout might otherwise carry elsewhere in this hub.
- The Extended Run checkbox and Export/Import Progress buttons are
  self-explanatory from their own adjacent label text, with no hidden
  mechanic behind them beyond what's stated.
- Reset Skill Tree's two-click confirm needs no advance warning tooltip:
  the first click is harmless (only arms it) and immediately changes the
  button's own text to "Click again to confirm reset," so the affordance
  teaches itself in the one click it takes to discover it exists.

No gaps found; nothing added. Full 210/210 pytest suite unaffected (no
code changed).

## Tech notes

- Python/Pyodide, per root conventions.
- **Persistence decision (revised from the original plan):** the plan originally called for Neon-backend persistence, written under the assumption this might run in a sandboxed Claude Artifact where browser storage is unavailable. It doesn't — this is a normal static site with no accounts/auth system anywhere in the project (SOL/Canopy/Grid/Tide are all anonymous, shared-per-browser). Persisting to Neon would mean inventing an anonymous-device-identity scheme just to key rows to a browser with no other identity, plus new backend surface on the shared ratings service. Confirmed with the user: **use `localStorage`** instead — same per-browser persistence, no new backend surface. Trade-off: doesn't sync across devices, and clearing browser data resets it.
- Keep run-state and skill-tree-state as separate objects from the start — they're tested and persisted differently.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag aftermath-milestone-0N`.
- Update the milestone table Status as work happens.
