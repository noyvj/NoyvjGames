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
| 8 | PC version: a Desktop boot (`pc.html`, generated from `index.html`) with a full-window dashboard layout, windows for the long sections, a Desktop tutorial and the layout switch on the opening screen | Done (2026-10-07; see `planning/PC-VERSION-PLAN.md`) |

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

## Climate scenario pack (E17a, 2026-09-26)

Four selectable event schedules (`SCENARIOS`): the Classic mix (the original, and the default, kept as the same list object so nothing else changes) and Coastal, Inland and Urban variants that shift which shocks dominate (coastal: two floods and two storms; inland: two heatwaves and broken supply lines; urban: two infrastructure failures and two civil unrests). Every schedule is 7 events long and within about 12% of the classic run's total base damage (Coastal 277, Inland 260, Urban 245 vs Classic 265) so the damage-vs-starting-resources balance the skill-tree tests are tuned against still holds; only which shocks arrive, and in what order, changes. `RunState(scenario=...)` builds its schedule from the chosen scenario (Extended Run doubles it; unknown names fall back to classic). A Scenario selector shows before a run's first event and between runs: changing it before the first event swaps the current run, and a new run reads it at start; mid-run it is hidden and ignored. Save: `scenario` written only when not classic, validated on load. Note the run-1-versus-latest progress comparison mixes scenarios if you switch between them, since totals differ by design. 257 -> 271 tests (`tests/test_scenarios.py`); verified live (coastal swapped the schedule, the blurb updated, the selector hid mid-run). E17b (named real locations) still builds on this.

## Societal memory (E29, 2026-09-26)

A settlement that comes through a run in ruin does not forget. When a run completes and pays out with a score at or below `VERY_BAD_RUN_SCORE` (10), the event CATEGORY that did the most total damage in it (`worst_damage_category()`) becomes a permanent memory (`societal_memory`, kept per browser in localStorage like the skill tree, key `aftermath_societal_memory_v1`, validated on load). Each memory reduces damage from that category via `category_mitigation_bonus()`, stacking with the skill tree but still capped by `MAX_MITIGATION`: 25% for non-weather shocks (supply chain, infrastructure), because the tree has no specialization for that category at all, so this is the only dedicated protection it can ever get ('a unique defensive skill not otherwise available'); 15% for weather and social, where the tree already offers upgrades. It is earned, not bought, so it is not a `SKILLS` entry and does not touch the tree's counts or achievements. A one-time callout names what the settlement now remembers the round the run ends, and a persistent line lists the memories. A rough-but-alive run never triggers it. 271 -> 286 tests (`tests/test_societal_memory.py`); verified live (a ruinous supply-chain run stored non-weather and showed the callout).

## Resilience mentor (E27, 2026-09-26)

An OPTIONAL guided mode, off by default and remembered per browser (`aftermath_mentor_v1`), separate from the one-time tutorial: a checkbox under the legacy line shows one inline sentence of advice, `mentor_suggestion(run)`, that reads the live run and says what it would do and why. Rules are checked in order and the first that applies wins: an opening note before anything is bought (what resilience and growth each do, and which event comes first); a warning when the next event's expected damage (`expected_next_event_damage()`) would take all your resources, split by whether you can afford resilience; no resilience yet; no growth after the second event; otherwise a steady-position note with the next event's cost and how many remain; and after the run ends a pointer to the skill tree. Advice only: it never acts for the player and never changes any number or state (tested), and the hint re-renders with every state change. 286 -> 299 tests (`tests/test_mentor.py`); verified live (opening advice, then the no-resilience warning after the first event, choice persisted).

## Resilience curriculum (E19, 2026-09-26)

A guided sequence of five lessons (`CURRICULUM`), each a run with one specific goal that teaches one idea: First steps (finish with resources in hand), Resilience first (3+ resilience), Growth pays (2+ growth and more than you started with), Balance (2+ growth, 2+ resilience, 100+ resources), and The coastal test (Coastal scenario, from E17a, with resources in hand). Strictly in order: only the CURRENT lesson can be completed, judged on the run's final state when it pays out (`note_curriculum_run()`, inside the same award guard as the knowledge payout, so replaying a stale run number can never pay a lesson twice). Progress is a plain count kept per browser (`aftermath_curriculum_v1`, clamped to 0..5 on read), a line under the legacy text shows the current lesson and goal and, once, the lesson just completed with its idea. Lessons never change any number in a run. 299 -> 311 tests (`tests/test_curriculum.py`); verified live (a genuinely new run advanced lesson 1 and showed lesson 2).

## Hardest-schedule leaderboard (E23, 2026-09-26)
When a run completes with resources left, `_report_hardest_schedule()` sends its `average_severity(event_log)` (rounded to 3 places) and `run N` to `window.NoyvjLeaderboard` (shared/leaderboard.js, mounted under the legacy history panel), which submits only for a signed-in, opted-in player and remembers the personal best. Run 1 is always exactly 1.00x so only later, harsher runs can climb. Backend board `aftermath/hardest_schedule`. Tests: `tests/test_leaderboard_report.py` (3).

## Community resilience index (E9, 2026-09-26)
`get_state()` gains a write-only `skill_tree_strength` (`skill_tree_strength()`, never read back; the save-system test pins the key set), whitelisted in `app/stats.py`. `shared/community-index.js` (a data-template script under the legacy history panel) reads `/stats/games/aftermath` and shows mean and median across players, hidden when there are too few saves. Needs the next backend deploy for the whitelist. Test in `tests/test_leaderboard_report.py`.

## Named real locations (E17b, 2026-09-26)
Four more `SCENARIOS` entries under a 'Real places (simplified)' group in the selector: San Francisco (three infrastructure failures, two heatwaves, one flood, no storm: earthquake and wildfire mapped onto infrastructure and heat), Houston (two storms, two floods), Phoenix (three heatwaves) and Chicago (two storms, heat, flood). The game has only six event types, so each is a deliberate simplification and the blurbs say so. Same rules as E17a (7 events, total base damage 245 to 283 vs classic 265, within 12%); nothing else changed, saves and validation reuse the `scenario` key. Tests added to `tests/test_scenarios.py` (315 -> 317).

## In the real world (W2-aftermath, 2026-09-26)
`REAL_WORLD_EXAMPLES` holds one real example per event type, every figure read from the linked Wikipedia page on 2026-09-26 (`REAL_WORLD_READ_DATE`) and nothing recalled: Room for the River (2006 to 2015, 2.2 billion euros, about forty projects, after the 1993 and 1995 floods), France's National Heat Wave Plan after the 2003 heat wave (over 70,000 deaths in Europe, 14,802 in France), Bangladesh's Cyclone Preparedness Programme (1973, 55 thousand volunteers; the page gave no death-toll comparison so none is quoted), the 2021 Suez blockage (six days, at least 369 ships queuing, about 9.6 billion dollars a day per Lloyd's List), the 2003 Northeast blackout (55 million people, a software bug stalling an alarm system for over an hour), and Christchurch's Student Volunteer Army (13,000 students a week at peak, over 360,000 tonnes of silt) for civil unrest and community strain. `render_real_world()` shows the note for the event last faced (else the next), with an external link and the read date; it changes no number. Tests: `tests/test_real_world.py` (5; 317 -> 322). User direction: SOL, Trade Empire and Le Champ were dropped from the real-world ask.

## Y11b light-theme polish (2026-09-27)

Method: a computed-style WCAG scan run in a real browser with the light theme on (walks every visible element with text, composites the ancestors' backgrounds including gradients, compares against the computed text colour, flags below 4.5:1 for normal text and below 3:1 for large text; also flags meter/track/tile fills that sit within 1.5:1 of their parent and dark surfaces left under the light theme). Disabled buttons are excluded (WCAG exempts inactive controls) and counted separately. It was run on the fresh game and again after playing, with every panel opened one at a time, and finally with every `[hidden]` element force-shown to catch panels a normal session does not reach. Screenshots in this environment were unreliable, so the scan output is the evidence, not eyeballing.

**Found (before):** 12 text groups: the four `.status-line` "dark glass" pills (`#resources-display`, `#resilience-display`, `#growth-display`, `#knowledge-points-display`, ID-selected so the shared light layer could not reach them) kept a near-black fill under dark text (2.4:1); the primary "Face Next Event" button's white label on a mid-brown gradient (4.24:1); the info "i" (1.23:1); dimmed `.skill-practice`, meter labels and back link (3.3-4.3:1). After play: the selected feedback button (dark text on dark green, 1.34:1) and the amber non-weather event colour on past-run lines (4.27:1).

**Fixed:** a `Y11b` block at the end of `style.css`, all under `html[data-theme="light"]`: light pills, a deeper primary gradient, captions at full opacity with a deeper slate, feedback button text, and deeper weather (blue), non-weather (amber) and social (violet) event colours. The three category hues are kept, so the cue (hue plus the label text beside it) still holds, and `.severity--mild`'s dimming is softened from .7 to .85 on light so mild events stay readable.

**After:** 0 flagged text and 0 flagged fills on the fresh game, after 20-30 events with skills unlocked and pinned, and with every hidden element shown. Exceptions: disabled buttons (skill unlocks before you can afford them, exempt), the gradient-clipped `h1`, and toasts (dark in both themes). The settlement illustration (`.settlement-visual`, dark night-sky scene with glowing windows) is intentionally left dark: it is a scene, not UI, and its dark sky is what the glow and damage marks are drawn against. `tests/test_light_theme.py` pins the block.

## Desktop boot (PC version, 2026-10-07)

`games/aftermath/pc.html` is the Desktop boot: the same game over the same `game.py` and saves (same `game_id`), laid out for wide windows with a mouse. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py` (run it after changing either; `--check` and the shared tests fail if it is stale). No rule, state or save change, and `game.py` is untouched. Per-game files: `pc-config.json` (what moves where), `pc.css` (layout, all under the pc layout), `pc.js` (`window.AFTERMATH_PC_TUTORIAL_STEPS`, which `index.html` uses when present, plus a small Escape fix for the `?` list). `index.html` gained only the `layout-pref.js` tag and the `AFTERMATH_PC_TUTORIAL_STEPS ||` fallback.

- **Layout.** No page scroll. Top bar: back link, title, three icon buttons (Achievements, Past Runs, Settings) and the Menu (Esc). Under it a strip of readout chips mirroring the original lines (event number, Resources, Resilience, Growth, Knowledge), which keep updating by id inside a hidden holder (Knowledge also stays in the skill tree). Stage: the Resilience mentor checkbox, then the settlement card (`#status`, kept whole because the damage scars and event icon rely on CSS sibling selectors from `#last-event-display` / `#next-event-display`): the settlement picture on the left (zoomed 1.3x to 3.5x with the window, because it is drawn in fixed pixels), the next event, expected damage, last event, mitigation meter and knowledge preview on the right, and the end-of-run breakdown spanning the bottom (the stage scrolls when it is long). Under the card: runs completed, the legacy line and chips, societal memory, the curriculum lesson and the mentor hint, then the hotkey bar (sticky at the bottom of the stage). Right column (scrolls on its own): the investments, Face Next Event / Start New Run and the Scenario and Extended Run controls pinned at the top, then the permanent skill tree, one skill per row.
- **Windows from the Menu.** Community (the resilience index and the hardest-schedule leaderboard), Backup / transfer progress, About Aftermath (tagline and context blurb) and Send feedback; plus How to Play, Achievements, Past Runs, What's New, Settings and The Real Story as before (the "In the real world" note is moved into the Real Story window). The Menu also holds the tutorial, the Story toggle, Fullscreen and the Classic layout switch.
- **Extended Run toggle** is still hidden until a run completes (the site-wide `[hidden]` rule); the Desktop CSS never sets a `display` on it.
- **Desktop tutorial.** `pc.js`: 12 steps pointing at the chips, the settlement card, the pinned decision tiles, the mitigation bar, Face Next Event, the knowledge line (the skill tree itself is taller than the column, so a spotlight on it would be off-screen), the comparison line, the Start New Run button (hidden until a run ends, so that step shows centred, as in Classic) and the Menu; the shared tests check every selector exists.
- **Notifications / hotkeys.** `notify` is null: Aftermath has no log list (its run log is the end-of-run breakdown). Only `?` and Esc are real hotkeys, so the hint bar lists those. MobileHud/MobileDock stay as they were (both only act at 640px and narrower; the HUD bar is hidden by CSS on the Desktop boot).
- **Known limits.** The mitigation meter's tutorial spotlight is a thin sliver while mitigation is 0 (the same in Classic). The settlement picture is zoomed with CSS `zoom`. At 1920x1080 the stage has spare room below the history lines. Below about 960px wide the side column narrows to 21rem; phones and narrow windows are meant to use Classic. The `?` overlay is the shared one, not a shell window. Verified live at 1440x900, 1920x1080 and 1024x700 in dark and light themes with scripted play (a full 7-event run, a new run, the mentor on); no human playthrough. 325 tests unchanged.

## Round-3 batch (2026-10-07, planning/TODO.md "GE + E. Aftermath")

Built: **E-12** Disaster Codex (`codex-panel`; one page per event type with times faced, average/lowest/worst damage, best mitigation, Flawless count and, once faced, the sourced real-world note; completion X/6, `codex_complete` achievement), **E-1** Lifetime Stats (`stats-panel`: damage by category, average mitigation per type with best/worst matchup, KP over time, average score by skill-strength band, each bar with its numbers written beside it), **E-15** x1/x5/Max step row (one click buys 1, 5 or as many as affordable; x5/Max never buy resilience past the 85% cap; choice kept in `aftermath-invest-step`), **GE-18** undo (`undo-allocation-button`, one undo per click, cleared by Face Next Event and by a load, never saved), **GE-15** Flawless Defense (event damage at most 15% of its base = mitigation at the cap against a typical or milder event: +1 knowledge per flawless event at run end, `flawless_defense` achievement, a hint line naming the limit for the coming event), **GE-13** prevented-damage line with held-streak (2+ events preventing at least half the damage) and a count-up in `ui.js` (static under reduced motion), **E-23** knowledge itemisation in the end-of-run panel plus a parenthetical on the live preview, **E-24** Copy run summary (clipboard, falling back to a text box), **E-27** live tab title, **E-5 (partial)** an aria-live announcer for every investment, undo and event resolution, **E-14** keys in `ui.js` (1/2 invest, Enter resolve from the bare page, U undo, T tree, H/C/S panels; listed in the "?" overlay and the Desktop hint bar), **E-16** High contrast and Readable font in Settings (`settings.js`, both themes, included in Reset to Default).

Deviations worth knowing: the Flawless threshold is 15% not the 10% in the TODO text, because mitigation is capped at 85% and the severity multiplier is at least 0.85 for a fresh settlement, so under 10% was unreachable. Mitigation, prevented damage and flawless status are derived from each stored event_log entry (base damage x severity versus damage), so no saved field was added; only run_log_history entries gained `skill_strength` (older logs are left out of the band stat). The undo does not roll back achievement flags already set by the undone click. `RunState.invest_resilience/invest_growth` gained a `record` argument (default True) and `allocation_history`; `invest_steps(kind, step)` is the bulk path. New element ids exist in both pages; Codex and Stats are Desktop windows and Menu entries (Records). Tests 325 -> 387 (`tests/test_round3_oct7.py`; `fakes.py` gained setAttribute/getAttribute).
- Wiring pass 2026-10-08: the run-summary actions (beside Copy run summary, which still copies the full event-by-event text) carry the shared Copy result button (`copy_result_fields()` in game.py feeds `shared/copy-result.js`; mounted by the inline script at the end of index.html), earned achievement cards get a Share button (`shared/achievement-share.js`), the head carries the Open Graph/Twitter block and JSON-LD from `share/meta/aftermath.html` and `share/jsonld/aftermath.json`, and the How to Play and Info panels end with a Credits link. Pins: `tests/test_wiring_oct8.py`.

## Fourth event category: health (FY-3, 2026-10-09)

A new category, `health`, with one event type, `heat_mortality` ("Heat-Health Emergency", 🌡️, base damage 36, teal `event-category--health`), for the case where heat harms people directly. **Design choice: an opt-in scenario, not a change to the base schedule.** The Classic mix stays exactly as it was (still the baseline for the run-1-versus-latest comparison, every saved run, and the hope-angle and skill-tree tests tuned to its 265 total damage). The new `heat_season` scenario (heatwave, heat-health, supply chain, infrastructure failure, heat-health, flood, civil unrest; 7 events, 247 total) is chosen from the existing Scenario selector, so it needs no new save field (`scenario` is already written and validated) and old saves load unchanged. Existing named scenarios were not edited either.

- **Mitigation:** general resilience and early warning apply. The tree has no health specialization (adding a skill would change `full_skill_tree` and every "X/7 skills" count for existing players), so the only dedicated protection is societal memory, which gains a `health` entry (25%, like non-weather) earned by a ruinous run.
- **Codex:** `EVENT_LABEL` now has 7 types, so the codex shows X/7 and the new locked page says it only arrives in the Heat season scenario (`event_source_hint()`). `codex_complete` ("Seen It All") is now defined on `CODEX_CORE_TYPES` (the original six) so nobody who earned it loses it; two new achievements, `heat_health_faced` and `codex_full_record` (all seven), cover the new page. Legacy counts, `legacy_events` and run logs need no migration (unknown types were already ignored and the new one is simply absent in old data).
- **Also:** a fourth settlement scar (`#settlement-legacy-scar-health`, in both pages), the settlement damage marks react to the health class, the Stats panel shows a Health damage row only once it has damage, the high-contrast and light-theme colours, and the real-world note (1995 Chicago heat wave, 739 heat-related deaths over five days, read 2026-10-09; examples may carry their own `read` date).
- Tests: `tests/test_heat_health.py` (schedule, damage, mitigation, societal memory, codex, achievements, legacy and stats, save round trip, old-save load); existing codex, scar and scenario tests updated for 7 types and 4 categories.

## Schedule strip (E-17, 2026-10-09)

`#schedule-strip` (an ordered list inside `#status`, so it is in the Desktop stage with no config change) shows every event of the run as a chip: number, icon, name, the category colour (the `event-category--*` classes, so high contrast and the light theme apply) and a state mark (tick done, arrow next) with a dashed or outlined border, so colour is never the only cue. `schedule_strip_entries()` gives the numbers: done events read the stored log entry; the next and upcoming ones use the deterministic severity for this run number and the CURRENT build (`mitigation_for`), so the damage is exact and moves as the player invests. Each chip has the same plain-text sentence as its `title`, `aria-label` and `data-detail`, and `tabindex=0`; `ui.js` delegates hover and focus to copy that sentence into `#schedule-detail` and restores the next event's text on leave (nothing depends on the script). This is also the plain-text schedule list the open E-5 item asked for. Tests: `tests/test_schedule_strip.py`.

## Skill 'Helps against' lines (E-29, 2026-10-09)

`skill-<id>-helps` under each skill row (both pages, Desktop grid span in `pc.css`). `skill_helps_against()` reads `SKILL_MITIGATION_EXTRA` (the four mitigation skills: category or all events, amount) and walks the events from `event_index` onward using the same deterministic severities and the 85% cap as `resolve_next_event()`, so the saved-damage figure is exact. Starting-build skills (reinforced infrastructure, community reserves, adaptive growth) cannot change the current run (they are read when a run is created), so their line says they help from the next run. Unlocked skills show nothing (decluttering). Tests: `tests/test_skill_helps.py`.

## Damage waterfall (E-18, 2026-10-09)

`#damage-waterfall` (a collapsed `<details>` in `#status`, body `#damage-waterfall-body`) explains the last event. `RunState.damage_breakdown()` is evaluated inside `resolve_next_event()` (before the damage is applied, so later investments cannot change it) and kept in memory as `run.last_breakdown`; it is never saved, so after a load or a new run the section is hidden. It splits the mitigation into resilience, early warning, mutual aid, the category skills (`category_skill_bonus()`) and societal memory (`category_memory_bonus()`; `category_mitigation_bonus()` is now their sum), in damage points, plus the amount the 85% caps gave back, and the test pins that base x severity - mitigation + cap equals the real damage. The stacked bar shows what each source really prevented (scaled down when the cap bit) then what got through; it is `role=img` with the same sentences as its aria-label and written as lines below, so the bar is never the only carrier. Tests: `tests/test_waterfall.py`.

## Unspent-resources confirm (E-28, 2026-10-09)

Settings checkbox `#confirm-unspent-checkbox` (settings.js, key `aftermath-confirm-unspent`, default off, cleared by Reset to Default) is read by game.py (`confirm_unspent_enabled()`). `on_resolve_event()` now asks first through the shared ConfirmDialog (`_confirm_dialog_ask(..., allow_skip=False)`: the helper gained an optional `allow_skip` that is only passed when given, so existing callers and fakes are unchanged, and the dialog's own 'don't ask again' is off because the Settings checkbox is the one switch) when the setting is on, the run is not over and the resources can buy at least one unit (`unspent_confirm_message()` also names how many resilience or growth units they could still buy). The actual resolve moved to `_resolve_event_now()`; without the dialog (tests, or the script missing) it resolves immediately. Enter and the click share the path, so the key is covered. Tests: `tests/test_unspent_confirm.py`.

## Past Runs: notes, sort, filter, archive, compare (E-22, E-21, E-20, 2026-10-09)

`#past-runs-panel` now holds static controls (`#past-runs-controls`: sort, filter, Show archived, a status line), `#past-runs-compare` and the list container `#past-runs-list` (so the Desktop window and every id exist in both pages; `render_past_runs_panel()` only rebuilds the list). **Notes (E-22):** `meta["run_notes"]` (run number as a string, 140 characters, at most 500), set from a text box on each card; **archive (E-21):** `meta["archived_runs"]`; both are in `meta`, so they ride the existing progress export with safe defaults for older codes (`_sanitize_meta`) and add no storage key. Archiving only hides a run from the default list: `run_history`, `run_log_history`, knowledge, achievements and Lifetime Stats are untouched (tested). `run_log_history` has no scenario or extended field, so `run_mode()` infers them from the event log (the schedule it matches, or the schedule twice); a log that matches nothing is labelled Custom schedule. The sort, filter and show-archived choices and the two compare picks are in-memory view state. **Compare (E-20):** up to two ticked runs (a third drops the oldest) render in `#past-runs-compare` as a two-column grid of stats (with the difference) and events (harsher/gentler/different event, also marked by bold plus text, not colour). One delegated handler (`on_past_runs_event`) serves every note box, tick and Archive button, because the cards are rebuilt on each render. Tests: `tests/test_past_runs_tools.py`; older tests read `#past-runs-list` instead of the panel.

## Improvement streak (GE-22, 2026-10-09)

`record_flags()` / `improvement_streak()` work on `run_history` scores in completion order: a run is a record when it strictly beats every earlier run (the first never is, a tie does not count); the streak is how many of the latest runs in a row were records. `#improvement-streak-display` (in `#status`) shows from 2 up; `streak_log_indexes()` marks the same trailing runs in `run_log_history` so their Past Runs cards get a flame in the title and `past-run-card--streak` (a static glow, so no reduced-motion case). Derived data only, nothing saved. Tests: `tests/test_improvement_streak.py`.

## Closing line / epitaph (GE-21, 2026-10-09)

`EPITAPHS` (six buckets: ruin, flawless, rich, resilience, growth, steady; 36 lines) plus `SCENARIO_EPITAPHS` (heat season, coastal, urban). `epitaph_kind()` picks the bucket in a fixed order (ruin at 0 resources or at or below `VERY_BAD_RUN_SCORE`, then flawless, rich, resilience, growth, steady) and `epitaph_text()` picks the line deterministically from the run number (a scenario line replaces every third non-ruinous run of that scenario), so it never changes between renders. The ruin bucket is tested for a list of harsh words. It is a plain `.run-epitaph` paragraph inside the run summary panel; Settings checkbox `#hide-epitaph-checkbox` (settings.js, key `aftermath-hide-epitaph`, cleared by Reset to Default) hides it. Changes no number. Tests: `tests/test_epitaph.py`; the summary-panel child count in an older test went up by one.

## Batch 2 (2026-10-10, planning/TODO.md "GE + E. Aftermath": E-19, E-25, E-30, E-9, E-4, E-13, E-3, E-5)

All in `game.py` (the block headed "Round-3 batch 2" before the GE-18 handlers, plus the changes listed below), `index.html` (new panels, run-code script, `seed.py` and `run_code.py` written into Pyodide), `style.css`, `ui.js`, `pc-config.json`/`pc.css`/`pc.js` (Desktop windows) and `tests/test_batch2_oct10.py` (75 tests; the 41 new element ids are in `tests/conftest.py`). Nothing in `shared/` was edited.

- **E-19 tree search and filters.** `#skill-search-input` plus chips built once in `build_skill_filter_chips()` (so keyboard focus survives renders): status (All, Affordable = can be unlocked right now, Pinned, Owned) and type (Any, Weather, Social, All events, Starting build; `SKILL_GROUP`). Every search word must appear in a skill's name, effect, real-world note or type. Rows get ids `skill-<id>-row` and are hidden through `hidden`; `#skill-filter-summary` (polite live region) says how many are showing, "Clear filters" appears only while a filter is active. View state only, nothing saved.
- **E-25 allocation presets.** `meta["presets"]` (up to 8, name 24 characters, 0 to 20 units each; sanitised on load and carried in the progress export; no new storage key; "per profile" = per browser until E-10 profiles exist). `RunState.invest_preset()` buys resilience first (stops at the 85% cap like x5/Max) then growth, limited by resources, as ONE allocation record of kind `"preset"` so U undoes it as one click. Quick-apply row (`#preset-apply-row`: select plus Apply) inside the docked action bar, hidden at 640px and narrower because the dock already fills about 40% of a phone (each preset's Apply button in the Allocation presets panel does the same there); the panel (`#presets-panel`) creates, fills from "Use this turn", applies and deletes.
- **E-30 save health badge.** Every `localStorage.setItem` in game.py now goes through `_storage_write()` (never raises, remembers the last good write and the failed keys); `probe_storage()` runs at start and when recovering. `storage_health()` says `failed` (a write threw: "Not saved: ... storage is full or blocked"), `unsaved` (`unsaved_progress()` finds the skill tree, run history or meta in memory differing from what is stored, for example cleared from another tab), `saved` ("Saved Ns ago", kept fresh by a 5 s timer in `ui.js` from `data-saved-at`) or `ready`. State is words plus a mark, with a dashed border for the two warnings; a separate `sr-only` polite region is written only when the state changes. The one-click button (`#save-health-export-button`, shown only in the two warning states) shows the progress code selected in a box and tries the clipboard. The per-run save-widget state is outside this (it is not localStorage).
- **E-9 difficulty-adjusted score.** `adjusted_score(score, event_log)` = score + sum(damage x (1 - 1/severity)) over the stored entries (never below 0): "what you would have scored had every event struck at the typical 1.00x". The severity already contains the skill-strength and lifetime widening, so both are normalised away, and it needs only fields already stored, so every old run can be adjusted. Shown as `adjusted_text()` in the end-of-run stats, each Past Runs card title, the toughest-run line, the toughest-run badge tooltip (`toughest_badge_title()`), the copied summary and a new "Adjusted score" Past Runs sort.
- **E-4 run codes (shared/run_code.py + run-code.js fit, so built).** Fields: game `aftermath`; **mode** = a scenario word (`SCENARIO_CODE_WORD`: classic, coastal, inland, urban, sanfran, houston, phoenix, chicago, heatsea) plus a trailing `x` for an Extended Run, or `custom`; **seed** = the severity draw (the sender's run number, base 31 in the seed alphabet) or, for `custom`, the schedule itself (a leading 1 then each event in base 8, `EVENT_CODE_ORDER` is append-only, at most 7 events); **score** = resources left; **stats** = [adjusted score, damage taken]. `run_code_fields()` (finished runs only) feeds the shared copy box mounted from `index.html`; the shared paste box's "Play this seed" calls `start_challenge(code)`. A **challenge run** is a `RunState(normalised=True)`: no starting bonuses, no skill or societal-memory mitigation (the bonus helpers gained an optional `unlocked`/`memory` argument and `RunState._unlocked()/_memory()/category_bonus()/severity_at()` route everything through the run), severity from the code's draw at the un-widened band (`event_severity(draw, i, 0, 0)`, so both players face the same numbers). It is only allowed between runs (never throws away a run in progress), earns no knowledge and writes nothing to history, achievements' run records or the leaderboard (`_note_challenge_result()` only counts it: `meta["challenge_runs"]` plus the best score per code, 40 codes), and shows a banner, a "Leave this challenge" button and a neutral comparison ("friendly note, not a ranking"; the sender's number came from their own build). Saves: a challenge run writes `challenge_code`, rebuilt on load. A finished challenge never takes a run number: the next real run is `highest_awarded_run + 1`. Codes are client-trusted (said in the panel).
- **E-13 schedule builder.** `#builder-panel`: event library buttons (built once), a draft (3 to 7 events, move up/down, remove), save by name (`meta["custom_schedules"]`, up to 12, same-name replaces), Run it (only between runs; your tree applies), Edit, Code (a schedule-only code through E-4) and Delete. `RunState(custom_events=, custom_name=)`; the log entry gets `custom_schedule`, so Past Runs labels it "Custom schedule: name" and the new "Custom schedules" filter finds it (even when the events equal a scenario). Because the player chooses the events, knowledge is scaled by `custom_knowledge_factor()` = min(1, total base damage / Classic's 265) (built-in scenarios and Extended runs stay 1.0), custom runs are never reported to the hardest-schedule board and do not advance the curriculum. Saves write `custom_events`/`custom_name`; a malformed list falls back to a normal run.
- **E-3 purchase route planner.** `purchase_route()` visits the pinned skills in pin order, prerequisites first, skipping owned ones and duplicates; `route_rows()` gives cost, running total, the knowledge still short of what is in hand and the runs needed at `average_knowledge_per_run()` (None until a run is complete); `#route-planner` (hidden with no pins) updates on every render.
- **E-5 (finished).** Focus management for the Classic layout in `ui.js` (a panel takes focus with `role=region` and a label when it opens, the toggle button gets it back when it closes by any route including Esc; the Desktop shell already does this for its windows, so it is skipped there); arrow keys, Home/End move between visible skills (each row is a labelled group), Enter on a row unlocks, P pins (listed in the `?` overlay); a plain-text schedule (`schedule_plain_text()`, in a `<details>` under the strip). The aria-live announcer from the first pass already covered event resolutions.

Desktop: Allocation presets and Schedule builder are Menu > Game windows, Run codes is Menu > Records, the save badge is in the stage zone; the three panels are `<details>` that `pc.js` opens by default (their summary line is hidden in a window). `pc.html` regenerated.

Not done / notes: the skill tree map (E-2) and ranks (E-11) need W-3's UI wired in and were not part of this batch. The quick-apply preset row is hidden on phones (above). `sw.js` was not touched: `shared/run-code.js`, `shared/seed.py` and `shared/run_code.py` are new fetches for this game, so they belong in the precache list (main session). Tests 477 -> 552.

## N-2: the first seasonal event, Halloween "Night of Storms" (2026-10-10)

The first event built end to end on the shared W-4 groundwork. An inline script in `index.html` (after `last-played.js`) calls `NoyvjSeasonal.init({game: "aftermath", events: {halloween: {...}}})`: the banner shows only inside the Halloween window (about 25 Oct to 1 Nov; `?event-date=2026-10-31` tests any day), the task is "finish one run with resources left" (goal 1). `game.py` calls `window.aftermathRunFinished(resources_left)` once when a real run completes (inside the `run_number > highest_awarded_run` guard, so replaying a stale save cannot count twice); the page counts it in `localStorage["aftermath-season:<badge id>"]` and the shared script grants `halloween-<year>` (hub contract R2-Z23b, also written to `event_badges_v1` for the hub). `onGrant` calls `set_event_badges(json)`, so the badge list lives in `game.py`'s `event_badges` and rides the save as `event_badges` (only when non-empty); `load_state()` validates it (`_clean_event_badges`: lowercase slug ids up to 64 characters, label 1 to 80, at most 40) and hands it back to `window.aftermathAdoptBadges`. Tests: `tests/test_seasonal_event.py` (6) and `shared/tests/test_aftermath_halloween_browser.py` (4). No numeric reward and no backend.

## AN-13: Move a point (2026-10-11)

`SkillTreeState.move_check(from_id, to_id)` / `move()` swap one owned skill for one not owned for `SKILL_MOVE_FEE` (1) knowledge plus the price difference (a cheaper skill hands the difference back). Refused, with a plain-words reason, when: either id is unknown or they are the same, the first is not owned, the second already is, another owned skill needs the first (`prereqs`), the second needs the first, or the balance would go negative (the message says how many knowledge short). `lifetime_knowledge` never changes and the new set is saved at once. UI: the `<details id="skill-move">` above the skill filters (two selects, a button, a polite status line; hidden until something is owned), rendered by `render_skill_move()` from `render()`. It is the only way to change an owned skill: there is still no refund and no reset. Tests: `tests/test_skill_move.py` (10).
