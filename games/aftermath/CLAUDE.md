# Aftermath — Climate Adaptation & Resilience Game

**Built following the shared conventions in `planning/archive/climate-quartet-plan.md`** (testing, feedback hook, hope-angle requirement, hub integration — moved there 2026-09-22 once all four quartet games shipped; was `climate-quartet-plan.md` at the games root while build order still mattered). This file is Aftermath-specific only. Built last of the four — the meta-progression skill tree was the most complex system, tackled once the other three patterns were proven.

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
`climate-quartet-plan.md` (now `planning/archive/climate-quartet-plan.md`)
— the quartet's standing visual-polish requirement actually asks for eased
state transitions, not against them),
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


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

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

## UI decluttering pass (site-wide goal, planning/TODO.md closing task)

Audited the single-page layout for the "everything looks very crowded" concern (the user's own framing) against the established `<details>`-disclosure fix pattern (Tide's `.ticker-history-toggle`, this game's own `.info-toggle` badges). This game has accumulated the most per-game features of the quartet by a wide margin (see the E1-E20 backlog pass and the changelog/achievements/past-runs/settings additions above) — a genuine, not speculative, crowding candidate.

Walked every always-visible block top to bottom. Most of the apparent length is already load-bearing or already disclosure-gated: `#howto-panel`/`#settings-panel`/`#info-page-panel`/`#achievements-panel`/`#past-runs-panel`/`#changelog-panel` are all `hidden`-by-default toggles already; `#status`'s four `.info-toggle` badges already collapse their own explanatory text; the skill tree's always-visible `skill-practice` paragraphs are a *deliberate* choice from the onboarding-tooltip audit above (permanent, non-gated grounding text, explicitly not a one-time toast) and collapsing them would undo that finding, so they were left alone; the settlement/event decorative visuals are `aria-hidden` art, not text stacking.

**Found one real offender:** `#progress-code-panel` (E12's export/import backup panel — a label paragraph, two textareas, two buttons, and a status line) was a plain always-visible `.section`, despite being a maintenance action a player touches rarely, if ever — the exact "rarely-touched settings/info block" shape the site's decluttering pattern targets. **Fix:** changed it from a `<div class="section">` to a `<details class="section progress-code-toggle">` with a `<summary>💾 Backup / Transfer Progress</summary>` header, collapsed by default. Pure structural swap — every child element keeps its existing id (`#progress-export-button`, `#progress-export-output`, `#progress-import-input`, `#progress-import-button`, `#progress-code-status`), `game.py` never reads or sets this wrapper's own hidden/open state (confirmed via grep), and no Python changed. Added matching CSS (`.progress-code-toggle` `summary` styling with a `▸`/`▾` marker, replacing the browser default triangle) to `style.css`, styled to read as a section heading rather than a raw disclosure widget. Full pytest suite (210/210) unaffected, as expected for a pure HTML/CSS change.

## Round-2 backlog pass (2026-09-20, planning/TODO.md "Per-game: Aftermath")

Built: E1/E3 (skills 6 and 7 -- `civic_preparedness` on the social-shock branch, prereq Community Reserves, -35% Civil Unrest damage; `climate_hardening` on the weather branch, prereqs Reinforced Infrastructure + Early Warning, -20% weather damage; applied via `RunState.mitigation_for(event_type)`, still capped at 85%), E2 (`skill_toast_duration_ms`), E4/E25 (`#runs-completed-display`, settlement name in the Settings panel), E5 (`generational_memory_text`), E6, E7 (`severity_bounds`/`lifetime_severity_widening`, +0.004 per lifetime run capped at 0.06), E8/E28 (`#callout-display`, one-shot flags), E10, E12 (`#settlement-badge-toughest`, lit after surviving a run whose average severity was "severe"; "personal best" interpreted as that), E13 (extended-run epilogue), E14/E20 (range + tooltip), E15 (`deep_specialist`, `broad_generalist`, `both_paths` -- 22 achievements), E16, E18, E22, E24, E26, E30a/b.

Cross-run extras (settlement name, pinned skills, callout flags) live in a localStorage `aftermath_meta_v1` dict (`meta`), included in the progress export bundle with safe defaults, deliberately not in `get_state()` (same reasoning as the skill tree). E8 is interpreted as "a run ends with 0 resources".

Left: E9/E23 (Z1 stats endpoint; not built), E17a/b scenario packs, E19 curriculum, E27 mentor mode, E29 societal-memory skill. Tests: `tests/test_backlog_wave2.py` (210 to 244).

## Tech notes

- Python/Pyodide, per root conventions.
- **Persistence decision (revised from the original plan):** the plan originally called for Neon-backend persistence, written under the assumption this might run in a sandboxed Claude Artifact where browser storage is unavailable. It doesn't — this is a normal static site with no accounts/auth system anywhere in the project (SOL/Canopy/Grid/Tide are all anonymous, shared-per-browser). Persisting to Neon would mean inventing an anonymous-device-identity scheme just to key rows to a browser with no other identity, plus new backend surface on the shared ratings service. Confirmed with the user: **use `localStorage`** instead — same per-browser persistence, no new backend surface. Trade-off: doesn't sync across devices, and clearing browser data resets it.
- Keep run-state and skill-tree-state as separate objects from the start — they're tested and persisted differently.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag aftermath-milestone-0N`.
- Update the milestone table Status as work happens.

- 2026-09-21: E20 -- Growth button/readout now show the real current payoff ("+16 -> +24 resources/event") instead of a static number (`growth_button_label`). Mobile-dock `html body` padding fix (V-AB-2).

## Toolbar consistency fix (Z12, planning/TODO.md, site-wide audit)

The site-wide Z12 audit (a separate session, checking all 12 games' toolbars for a consistent Tutorial -> How to Play -> [Info Page ->] Achievements -> Changelog -> [game-specific toggles] -> Settings order) found Aftermath as the one real outlier: `#settings-toggle-button` sat in a first `.game-toolbar` right after Tutorial/How to Play (everywhere else, Settings is last), while `#info-page-toggle-button`/`#achievements-toggle-button`/`#past-runs-toggle-button`/`#changelog-toggle-button` were stranded in a *second* `.game-toolbar`, separated from the first by the tagline/context-blurb/`#runs-completed-display`/`#legacy-display`/`#legacy-history-panel` narrative block.

Checked for a genuine functional reason to keep the split before touching anything: read `shared/tutorial.js`'s spotlight mechanism (`document.querySelector` + `scrollIntoView`, both position-independent) and confirmed none of `AFTERMATH_TUTORIAL_STEPS`' selectors target any toolbar button (they target `#status`, `#resilience-invest-button`, `#growth-invest-button`, `#mitigation-bar`, `#resolve-event-button`, `#skill-tree`, `#progress-comparison-display`, `#new-run-button` -- all further down the page, untouched by this fix). No such dependency exists. The likeliest original reason for the split -- wanting the narrative/context blurb high up for a first-time player, ahead of the achievements/past-runs/changelog buttons -- is a real, understandable instinct, but the site-wide layout-consistency goal takes priority, and nothing about the narrative block's own visibility or position relative to the *page* changed here (it still renders in the same place relative to the settlement visuals/status card below it); it just now follows a single merged toolbar instead of sitting between two.

**Fix:** merged the two toolbars into one, immediately after `<h1>Aftermath</h1>`, in the order Tutorial -> How to Play -> Info Page -> Achievements -> Past Runs -> Changelog -> Settings (Settings last, matching all 11 other games). Every button's `id`, class list, inner text/content, and adjacent comments (E7's past-runs note, K16's changelog note, the settings-panel A9 note) moved unchanged -- nothing renamed, duplicated, or dropped. The narrative block and every panel div (`#howto-panel`, `#settings-panel`, `#info-page-panel`, `#achievements-panel`, `#past-runs-panel`, `#changelog-panel`) kept their exact prior relative order to each other and to everything below them (`#achievement-toast`, `#skill-unlock-toast`, `#status`, ...); only the toolbar buttons moved, and the now-empty second `.game-toolbar` wrapper was deleted.

Full pytest suite (246 tests) stayed green throughout, since this is a pure HTML reorder with no `game.py` changes. Verified live via the shared `hub-dev-server`: a fresh load shows all seven buttons in one toolbar in the correct order, no overlap/wrapping issues (the row wraps to two visual lines at this viewport width, same as Grid/Tide's own two-row `.game-toolbar` layouts, but it is a single element), the narrative content and settlement visuals render correctly below it, and Achievements/Changelog/Settings/Info Page/Past Runs all still open their correct panel content with zero new console errors.

**Found in passing, not fixed here (flagged as a separate follow-up task):** `.achievements-panel`/`.changelog-panel` in `style.css` set `display: grid` as a class rule, which beats the browser's default `[hidden] { display: none }` UA rule once either class is present -- so both panels are already visible as empty boxes on a first, never-touched page load, and neither one ever visually disappears again once opened once (their close handlers in `game.py` set `hidden = true` but never clear `innerHTML`, and no `[hidden]` override exists anywhere in this game's CSS to force it closed regardless). Confirmed this reproduces identically on a clean load with zero interaction, so it predates and is unrelated to this toolbar move -- purely a pre-existing CSS/close-logic gap, not a functional regression from relocating the buttons.

## Hidden-panel display bug fix (follow-up to the Z12 note above)

Confirmed the diagnosis above exactly: `.achievements-panel`/`.changelog-panel`'s `display: grid` (author-origin, class selector) beat the UA default `[hidden] { display: none }` (equal specificity, author rule wins regardless of source order for this particular pair) whenever the `hidden` attribute was present, so both panels rendered as empty bordered boxes before their first open and stayed fully visible with stale content after being toggled closed. Same shape SOL's/Trade Empire's/Continuum's own `achievements-panel`/`settings-panel` CSS already found and fixed -- Aftermath just never got the matching `[hidden]` override when this pattern was copy-pasted in.

**Fix:** added `.achievements-panel[hidden] { display: none; }` and `.changelog-panel[hidden] { display: none; }` to `style.css`, right after each panel's own `display: grid` rule. CSS-only, matching the site's existing precedent for this exact gotcha; `game.py`'s toggle handlers (which never cleared `innerHTML` on close) were left untouched since the `display: none` override alone fully hides stale content regardless of what's still in the DOM -- no `game.py` change needed or made.

Read-only repo check (informational, not fixed here, out of scope for this game-only task): the same `display: grid`-on-a-hidden-toggle-panel shape exists across most of the other 11 games (`achievements-panel`/`changelog-panel`/`settings-panel` classes recur site-wide from the shared achievements/changelog/settings rollouts). SOL, Trade Empire, Continuum, Drift (changelog only), and Tide (changelog only) already carry a matching `[hidden]` override for at least one of their panels; Canopy, Champ de Mots, Grid, Herd, Loop, and Thaw appear not to, based on a grep for `panel[hidden]` in each game's `style.css` turning up no matches -- worth a dedicated site-wide sweep, not something this dispatch's scope covers.

Verified live via a local server: hard-reloaded with the service worker unregistered and its cache cleared (the shared `hub-dev-server` was already occupied by another session, so this used a fresh browser tab against the same port) -- fresh load shows `getComputedStyle` returning `display: none` for both panels (0 empty boxes), opening each renders its real content (22 achievement cards / 10 changelog entries) with `display: grid`, and closing either one flips it straight back to `display: none` -- confirmed actually invisible, not just `hidden` in the DOM. Zero console errors. Full pytest suite (246 tests) and flake8 stayed clean throughout, as expected for a pure CSS change.

## Info-page toggle icon drift fix (Z26, site-wide regression check)

The site-wide Z26 audit — confirming the shared `shared/info_page.py` "The Real Story" toggle button renders identically (wording/icon) across all 8 climate-quartet games — found one real drift, unique to this game: `style.css` carried a leftover `#info-page-toggle-button::before { content: "📖 "; }` rule from the 2026-09-05 "full visual redesign" pass (which gave several controls decorative `::before` icons, e.g. the skill tree's `🔓` unlock icon), predating this game's later migration onto the shared `info_page.py` module. `info_page.py`'s `render()` only ever sets the button's `innerText` (no icon, by design — see that module's docstring) and no other one of the 8 games has an equivalent CSS rule on `#info-page-toggle-button` (confirmed via `grep -rn "info-page-toggle-button" games/*/style.css` — only this game had a match), so this button was rendering with a book-icon prefix the other 7 games don't have. The icon happened to visually echo the *static* `📖 How to Play` button label a few slots over in the same toolbar (that one's icon is baked into its own HTML text, which is fine — it isn't the shared component) — coincidence, not a deliberate pairing; nothing referenced or explained the info-page icon anywhere in this file or `game.py`.

**Fix:** deleted the `#info-page-toggle-button::before` rule from `style.css`. No `game.py`/`index.html` change needed — the button's id, class list, and static "Loading..." placeholder text already matched the other 7 games exactly; only this one bespoke CSS icon differed. Verified live via the shared `hub-dev-server`: the toggle now reads plain "The Real Story" / "Hide The Real Story" with no icon, matching Canopy/Grid (both spot-checked live in the same pass) and the other 5 games (confirmed via code/grep — identical static markup, identical `render_info_page()`/`on_toggle_info_page()` wrapper calling straight into `info_page.render()`/`info_page.toggle()`, no other CSS override anywhere). 254/254 tests green (unaffected — pure CSS), `flake8 games/aftermath --extend-ignore=E501` clean.

## Legacy weathering scars (V-CD-6, completion audit section N)

The completion audit found a real gap: the original Pass-2 legacy-system idea (`## Iteration Notes -- Pass 2` above) explicitly described "a visual marker in the settlement referencing its history," but what E4 actually built (the per-game backlog pass above) was only `legacy_event_counts` rendered as a text chip row (`legacy-history-chip` spans, e.g. "🌊 Flood ×2") -- no visual marker on the settlement itself. The user was asked to decide and said "you can decide."

**Read first, to confirm there was a genuine gap and not just a naming coincidence:** `index.html`'s `.settlement-visual` *is* a real illustrated element (a small CSS skyline: sky gradient, four buildings, a resilience-shield dome, a ground strip), and it already carries two kinds of history-driven visual state -- `.settlement-damage` cracks (reactive only to the *current* run's last-resolved event category, cleared every new run) and E15/round-2's `.settlement-badge` rooftop dots (one per unlocked skill, plus a "toughest run" badge, all *skill-tree/achievement* history, not climate-event history). Nothing on the settlement reacted to `legacy_event_counts` -- the one piece of cross-run climate history that Pass 2's own idea was actually about. Confirmed this was a real, not cosmetic, gap.

**Decision:** add a third, small visual layer to the same settlement art -- a short CSS-drawn "weathering scar" (a cracked-texture strip using the same `repeating-linear-gradient` technique as `.settlement-damage`) along the settlement's ground line, one per event *category* (weather/non-weather/social, reusing `EVENT_CATEGORY` and the exact hues already established for `event-category--weather/non-weather/social` elsewhere on the page), escalating through three visible tiers as that category's aggregated `legacy_event_counts` total climbs (`legacy_scar_tier()`: tier 1 at 1+, tier 2 at 3+, tier 3 at 6+, tier 3 alone gets a soft pulsing glow). Deliberately **per category, not per exact event type** -- six more rooftop-style dot badges stacked on top of the eight skill/toughest badges the settlement already carries would be exactly the "everything looks very crowded" failure mode the UI-decluttering pass above was written to avoid, and the category grouping reuses an identity (color) the player already recognizes rather than inventing a sixth. No new art asset and no new persistent storage -- `legacy_category_totals()`/`legacy_scar_tier()`/`legacy_scar_tiers()` are pure functions derived from the already-persisted `legacy_event_counts` dict, the same source the E4 chip row already reads.

Implementation: three new `aria-hidden` divs inside `.settlement-visual` (`#settlement-legacy-scar-weather/-non-weather/-social`), a `.settlement-legacy-scar`/`--tier-1/2/3` CSS block in `style.css` positioned along the ground line so it can never collide with the rooftop badges, and one small loop in `render()` (right after the E4 chip-row loop it sits next to) that clears and re-applies the matching tier class per category every render. Covered by a new `tests/test_legacy_scars.py` (category aggregation, tier thresholds at the exact boundary counts, and `render()`-driven classList checks across zero/one/two completed runs, including a stale-higher-tier-doesn't-stick check). Full pytest suite (246 → 254 tests) and flake8 stayed clean throughout.

Verified live via the shared `hub-dev-server` (fresh tab, since the port was already in use): drove `legacy_event_counts` up directly via `pyodide.runPython` (flood/heatwave/storm, supply_chain, and civil_unrest at varying counts) and called `render()` -- all three category scars appeared with the correct tier class (verified via `classList` and visually, via a temporary debug-only `transform: scale(3)` zoom on `.settlement-visual` to inspect the small ground-line marks up close), the civil-unrest scar at count 8 showed the tier-3 pulsing glow, and a fresh/untouched settlement showed all three scars fully transparent (no tier class). Zero console errors throughout.
## Export-progress shared helper (Z8, site-wide goal)

`planning/TODO.md`'s Z8: E12's export/import progress code now runs on a
new shared `shared/export_progress.py` (the base64<->JSON codec plus the
"is this even a dict" structural check), rather than hand-rolling its own
copy of that logic — the same shared module SOL's A17 stats code also
migrated onto in the same pass, since both games turned out to be two
real-world shapes of the same "portable progress-code" pattern (E12: a
structural bundle, replace-on-import; A17: flat counters, monotonic-max
merge — see the shared module's own docstring for why one shape wasn't
forced onto both).

Pure refactor, no player-visible change: `export_progress_code()`/
`import_progress_code()` keep their exact same signatures, the exported
code's shape (no prefix, same bundle keys) and `progress_summary_text()`
are untouched, and the Backup/Transfer Progress panel's UI/copy is
unchanged. `game.py` now does `import export_progress` (loaded into
Pyodide's virtual filesystem by `index.html` the same fetch-then-
`FS.writeFile` way `info_page.py` already is) and the top-level `import
base64` was removed as now-unused. No `changelog.json` entry added, since
nothing a player sees or does changed.

Verified: full pytest suite (257/257) and `flake8` clean. Live via
`hub-dev-server`: exporting real (non-zero) skill-tree/knowledge state
produced a real decodable code, re-importing it round-tripped correctly,
and a malformed pasted code failed soft with the existing status message
— zero console errors throughout.

## Screen-reader accessibility audit (Z15, site-wide goal, planning/TODO.md)

Static-analysis audit (grepping/reading `index.html`/`game.py`, no live screen
reader in this environment — same audit-only method the colorblind-safety
passes already established for this hub) of the achievements and settings
panels: toggle-button accessible names, panel role/heading semantics, focus
order on open/close, keyboard reachability of interactive elements, and
checkbox/label association.

**No real gap found — no change made.** Checked against the same candidate
list as every other game in this pass:
- Both toggle buttons (`#achievements-toggle-button`, `#settings-toggle-button`)
  already carry descriptive visible text, a sufficient accessible name on its
  own — no `aria-label` needed.
- The settings panel's own title is already a real `<h2 class="settings-panel-heading">`
  (this game was already ahead of four sibling games in this hub that had it
  as a plain, heading-nav-invisible `<p>` — fixed there this same pass), so
  it's already reachable via a screen reader's heading-navigation mode.
- The achievements panel itself has no heading of its own, but is adequately
  labeled by the toggle button's own visible text immediately above it — the
  same "plain semantic markup is enough" call this hub's colorblind-safety
  audits already made for comparable cases.
- No focus-trap exists anywhere in this hub, and none was warranted here:
  clicking the toggle button never moves focus itself, so it naturally stays
  on that same button when the panel opens or closes.
- Every interactive element inside both panels is a real `<button>`/`<input>`
  (confirmed via a site-wide grep for `.onclick =` assignments and
  `createElement("div")` calls with a wired click handler — none found).
- The reduced-motion checkbox is properly associated with its label
  (`<label class="settings-checkbox-label" for="reduced-motion-checkbox">`
  wrapping the input).

No code changed; ran as the baseline check this pass calls for regardless
of verdict.

## Reset-confirmation migration to shared ConfirmDialog (Z22, site-wide goal)

`planning/TODO.md`'s Z22 audit flagged this game as one of two (SOL's
Reset This World/Prestige is the other) whose irreversible-action
confirmation predates `shared/confirm-dialog.js`: Reset Skill Tree (E13)
used an in-UI two-click "arm, then confirm" pattern (click once to arm,
click again to actually reset — see the now-superseded comment this
replaced) rather than a modal, chosen back when the shared widget didn't
exist yet and a self-contained approach avoided needing a new `window`
global under the fake-DOM test harness.

Migrated to the shared ConfirmDialog via the same `_confirm_dialog_ask()`
helper shape as Grid/Herd/Loop/Trade Empire/SOL's own copies — falls
through to running the reset immediately if `window`/`window.ConfirmDialog`
isn't available, matching every other game's fallback and the pytest
fake-DOM harness's default. Added `shared/confirm-dialog.js` to
`index.html` (never included before). The refund total, previously shown
by silently changing the button's own label after the first click, now
states itself directly in the dialog's message
(`reset_refund_total()` unchanged). `on_reset_skill_tree()` also gained an
explicit early return when nothing is unlocked, matching every other
game's "never even ask when there's nothing to lose" convention — the
render-time `disabled` state already prevented a real click getting here,
but the guard makes the handler correct on its own terms too. The old
`skill_tree_reset_pending` flag and its `_clear_skill_tree_reset_pending()`
call sites (scattered across every other skill-tree-mutating handler) are
gone entirely — a real modal doesn't need a same-session "cancel by doing
something else" escape hatch.

Tests: 254 → 257 (`tests/test_confirm_dialog.py`, new — 4 tests covering
the dialog-gated path: message/id, cancel leaves state untouched, confirm
resets and fully refunds, and the nothing-unlocked no-op case). Existing
`test_backlog_e2_e20.py`/`test_backlog_wave2.py` tests that drove the old
two-click flow directly were updated to match the new single-click
(no-dialog-faked, immediate) and dialog-faked-and-confirmed shapes. All
green, `flake8` clean. Live-verified via `hub-dev-server`: unlocking a
skill then clicking Reset Skill Tree shows the dialog with the correct
live refund total in its message; Confirm resets `skill_tree.unlocked` to
empty and fully refunds `knowledge_points`. Zero console errors.

## Print-friendly summary (Z21, site-wide goal)

`planning/TODO.md`'s Z21: a shared `media="print"` stylesheet
(`shared/print-summary.css`) so printing the page while a game's
end-of-session summary is open produces a clean paper page instead of the
site's dark space theme (which prints as blank/near-blank on most
printers) plus a pointless copy of the nav/ad bar/toolbar/starfield. The
shared file works off one convention: whatever element the game's own
summary lives in gets a `print-summary` class, and the stylesheet hides
everything else on the page (`body * { visibility: hidden }`, then
un-hides `.print-summary` and its descendants), strips
gradients/glow/`backdrop-filter` in favor of plain dark-on-white, hides
any buttons/inputs inside the summary itself, forces open any collapsed
`<details>`, and adds `page-break-inside: avoid` on the summary's own
direct-child blocks.

**Applied here:** `index.html` gained
`<link rel="stylesheet" href="../../shared/print-summary.css" media="print">`
right after the existing `ad-bar.css` link. The target here is
`#run-summary-panel` — E11's "a proper end-of-run summary" (final
resilience/growth/damage stats, the full event-by-event breakdown, and
the extended epilogue when one applies), which is what the game's own
code comments already call the run summary, distinct from the terse
one-line `#run-summary-display` score sitting just above it. Gained the
`print-summary` class alongside its existing `run-summary-panel` class.
`render()` only ever calls `run_summary_panel.innerHTML = ""` and
re-appends children — it never touches the element's own class list — so
this survives every re-render untouched. Purely additive: `media="print"`
never applies on-screen, and no `game.py`/on-screen markup changed.

**Verification method used:** this sandbox has no print-to-PDF affordance,
so per this task's own guidance, verification was done by confirming the
stylesheet loads with `media="print"` and that its selectors have real
targets in the live DOM, rather than a literal print render — same method
as Canopy's Z21 pass (see that game's CLAUDE.md for the detailed
DOM-selector checks run against a structurally similar panel).
`python3 -m pytest games/aftermath/tests -q` stayed at 257/257 (pure HTML
class/link addition, no Python touched).

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`: tutorial,
Achievements, Settings panels, the mobile-docked "Face Next Event" button,
plus a full-DOM `scrollWidth`/`clientWidth` sweep. Audited, no change
needed — `document.documentElement.scrollWidth` never exceeded 320 in any
state checked, and the docked button sat correctly at 288px wide (16px
margin each side), unlike Grid's/Continuum's docked buttons which had a
real `width: 100%` bug — Aftermath's own mobile-dock CSS already sets
`width: auto` there. The top `#mobile-hud-bar` strip's own `overflow-x:
auto` is the same deliberate scroll-not-clip idiom Canopy's Z18 section
documents, not a bug.

## Difficulty-aware achievements audit (Z27, site-wide goal)

Checked `game.py` for anything resembling a player-facing hard-mode/
difficulty toggle (grep across "difficulty", "hard mode", "scenario",
"challenge", "opt-in") — the only hit is E7's severity-scaling curve
(`SEVERITY_VARIATION_RANGE_PER_LIFETIME_RUN`/`lifetime_severity_
widening()`), and it is not a toggle at all: it's an automatic function of
`skill_tree_strength()` and lifetime run count, both of which the player
influences only indirectly through ordinary play, with no on/off control
or difficulty picker anywhere in the UI. **Aftermath has no player-facing
difficulty toggle to audit — not applicable.** No code touched.

## Achievement-progress bar in toolbar (Z-extra/A10, site-wide goal)

Already satisfied — see the existing toggle-button label. `#achievements-
toggle-button`'s `innerText` already reads `"🏆 Achievements (N/M)"` via
`update_achievements_display()`, called from the main render loop, so the
live earned/total count is visible in the toolbar before the panel is
ever opened. No code change needed here.

## "What's new since you played" banner (Z24, site-wide goal)

A new shared `shared/whats-new-banner.js` -- deliberately distinct from
this game's own in-game "What's New" changelog PANEL above (opt-in,
player-triggered, always shows the full history from scratch). The
banner instead appears automatically on page load, but ONLY for a
RETURNING player who has missed real entries since their last visit: it
diffs this game's `changelog.json` against
`localStorage["whats-new-seen:aftermath"]` (the date string of the
newest entry already shown) and lists just the new ones, not the whole
log. A first-ever visit silently marks the current changelog as seen
rather than dumping the full history on a brand-new player. Reuses the
same `window.CHANGELOG_JSON` global this game's own changelog panel
already fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="aftermath">`
include, added right after `shared/last-played.js`'s own include. See
root `CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Settings, the Info Page, Achievements, Past
Runs, and What's New. `?` opens a small floating shortcuts-help overlay;
`Esc` closes it and clicks the toggle button of whichever listed panel is
currently open, reusing each panel's own open/close logic. The legacy-
history panel and the run-summary panel aren't in the list -- both are
shown by game state/run-completion, with no player-clicked toggle button
to reuse for a generic Esc close.
