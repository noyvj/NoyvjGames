# Thaw — Permafrost Feedback Loop Game

**Built following the shared conventions in `planning/archive/climate-quartet-2-plan.md`** (moved there 2026-09-22 once all four second-set games shipped; was `climate-quartet-2-plan.md` at the games root while build order still mattered). This file is Thaw-specific only. Built second in this set.

## Concept

The player manages a northern region while global temperature rises on a fixed background trajectory they don't fully control. As it rises, permafrost gradually melts, releasing stored methane — which accelerates the same warming trajectory further. The player's regional choices (land management, local emissions) can nudge the timeline, but the core experience is watching a slow problem tip into a runaway feedback loop if nothing meaningfully intervenes.

## Function tag: Futures on the current path

This game exists to simulate what happens if things continue as they are. Unlike Grid or Herd, the player isn't the primary driver of the central meter — the background trajectory moves largely on its own, and the player's job is to understand and respond to a system bigger than their direct control. This is deliberately different from the other games' "your choices are the whole story" framing.

## Climate issue & hope angle

**Issue:** permafrost thaw and the methane-release feedback loop.
**Hope angle:** this is the game in the whole hub most at risk of reading as pure doom, because feedback loops are inherently runaway-danger mechanics — treat the hope angle here as a hard design requirement, not a nice-to-have. Give the player a real, visible lever (regional emissions reduction, permafrost-preserving land management) that measurably slows the loop's acceleration, even if it can't fully stop the background trajectory. The message should land as "intervention changes the slope, and the slope matters enormously" — not "nothing you do matters."

## Core loop

- Turn-based rounds. Background global temperature rises on a fixed schedule each round, independent of the player.
- As temperature crosses thresholds, permafrost in the player's region begins melting, releasing a methane pulse that adds to the background warming rate (this is the feedback — warming causes melt causes more warming).
- Player allocates regional resources between: local output/growth (immediate benefit, adds marginally to global emissions), permafrost-preserving measures (slows local melt rate), and monitoring/early-response infrastructure (reduces damage from melt events when they happen).
- Feedback loop is visible as an accelerating rate, not just a rising number — the meter's *slope* should visibly steepen once the loop kicks in, so players feel the moment it tips.
- No hard fail-state, but a region that lets the loop run unchecked should end a session in a visibly worse, harder-to-manage state than one that intervened early — same "delay compounds cost" pattern as Grid, but framed around a feedback mechanism instead of a linear meter.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Background trajectory + core loop | Fixed-schedule temperature rise, regional resource allocation across rounds. Tests: temperature progression, allocation logic | Done |
| 2 | Permafrost melt + methane feedback | Melt triggered by temperature thresholds, methane pulse feeds back into warming rate. Tests: melt-threshold logic, feedback-rate calculation | Done |
| 3 | Intervention measures | Preserving/monitoring investments that measurably slow the feedback loop's acceleration. Tests: slope-reduction formula per measure | Done |
| 4 | Visible acceleration | Surfacing the loop's steepening slope to the player clearly (not just a bigger number, a visibly faster-rising one). Tests: slope-calculation and threshold-crossing detection | Done |
| 5 | Hope-angle payoff | End-of-session comparison showing early intervention produced a meaningfully flatter trajectory than inaction. Tests: comparison calculation across sample playthroughs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual/UI pass + hub integration | | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: this is the most doom-prone game in the hub by design (a runaway feedback loop), and the exact moment the loop "kicks in" risked being lost in a gradually rising number rather than landing as a distinct moment.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a one-tick screen-flash cue at the moment the feedback loop crosses its tipping threshold. The end-of-session "no-intervention" ghost-line comparison was already substantially covered by Milestone 5's `counterfactual_temperature`/`temperature_saved` and was verified as sufficiently clear rather than rebuilt. Audio sting was considered and skipped — no audio system in the stack.

**Open testing question:** can players correctly identify, after a session, what caused the tipping point? Is the intervention lever discoverable without being told about it directly?

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected addition: A (multi-region comparison).**

- **Multi-region comparison:** the player manages a small handful of regions (2–3) simultaneously, each allowed a different strategy, so the feedback-loop consequences of intervention vs. neglect are visible side-by-side within a single session rather than only across separate playthroughs. Directly strengthens the hope-angle requirement flagged in Pass 1 — seeing an unmanaged region's steep curve next to a managed region's flatter one in real time is a stronger proof than an end-of-session ghost-line comparison alone.
- **Visual polish for this pass:** each region needs its own compact, clearly labeled mini-graph, laid out so the divergence between regions is the dominant visual read of the screen — this feature only works if the comparison is immediately obvious, not something the player has to hunt for across tabs or panels.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** already flagged as the most doom-prone game in the hub (Pass 1); this pass adds the research-backed version of that concern — a feedback-loop mechanic without a legible efficacy payoff is close to the exact setup the Klim:S21 study found risked "fuelling fear" rather than "strengthening trust." Concretely: investing in preserve/monitor silently increased `feedback_dampening_fraction()`, but pre-melt that number had zero effect on anything else visible — the "Feedback dampening: X%" line ticked up with no perceptible consequence until the feedback loop actually kicked in, which could be many rounds away (or never, in a short session). That's exactly the immediate-feedback gap Flow principle #2 warns against.

**Built in response:**
- `RegionState` gained a one-tick `just_invested_intervention` flag, set whenever a preserve or monitor investment succeeds (not output — that's not the intervention lever) and consumed by the next `render()`, mirroring the existing `just_started_melting`/tipping-flash pattern from Pass 1. It drives a new `.dampening-flash` CSS cue on the dampening readout — deliberately green, the opposite tone of the red tipping-point flash, so a good action visibly reads as good news.
- A new `intervention_feedback_message()` method gives an explicit, legible efficacy readout ("Preservation & monitoring investment is already dampening the feedback loop by X% — that protection is in place now, whether or not melt has started yet.") that's true and specific from the very first investment — unlike `trajectory_message()`/`acceleration_message()`, it doesn't need melt to have started to say something real. Rendered into a new `intervention-feedback-display` element, right under the dampening line.
- Considered and rejected: an instant numeric nudge to `temperature` itself on investment (the design doc's suggested example). Milestone 1's `test_temperature_rise_is_identical_with_or_without_investment` explicitly locks in that investment never touches temperature before melt — that's a deliberate invariant (mirrored by Milestone 3's "background rise is never dampened" test), so the fix stayed purely representational: a real, already-true number surfaced immediately and legibly, not a new numeric effect.
- The in-game feedback prompt gained a second yes/no question specific to this game's highest-risk-in-hub status: "Did your preservation/monitoring investments feel like they were actually working?" Both answers fold into the existing single `response` string field sent to the shared ratings backend (`understanding=...; intervention_worked=...`), so no schema change was needed.
- Scope: the fix was applied to the primary region only, not the Pass 2 secondary regions (B/C) — those exist for cross-region comparison, not as the tutorial intervention lever, and Pass 2's zero-regression discipline argued against touching more surface than necessary.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is game-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Arctic permafrost holds thousands of years of stored carbon and methane, and as it thaws that store starts releasing — a feedback loop where warming causes more warming. But real climate scientists describe it as a dimmer switch, not an on/off switch: every bit of avoided warming keeps more permafrost frozen. That framing is the backbone of Thaw's whole design.

**Mechanic tie-in:** Thaw's tipping-point moment is grounded in real observed evidence of accelerating Arctic methane emissions, not a purely speculative mechanic.

**Sources:**
1. [MIT Climate Portal — Is methane release from the Arctic unstoppable?](https://climate.mit.edu/ask-mit/methane-release-arctic-unstoppable) — the clearest source for Thaw's hope angle: the feedback loop as a dimmer switch, not an on/off switch.
2. [Nature Climate Change — Seasonal increase of methane emissions linked to warming in Siberian tundra](https://www.nature.com/articles/s41558-022-01512-4) — real observational evidence of the feedback loop already measurably happening.
3. [WWF Arctic — Thawing permafrost](https://www.arcticwwf.org/the-circle/stories/thawing-permafrost/) — accessible explainer connecting permafrost thaw to real Arctic communities' lived experience.
4. [PMC/NCBI — 21st-century modeled permafrost carbon emissions accelerated by abrupt thaw beneath lakes](https://pmc.ncbi.nlm.nih.gov/articles/PMC6093858/) — a more technical source on abrupt thaw mechanisms, tying to Thaw's tipping-point moment.

All four links verified live before merging. Source 1 (MIT) returns 403 to automated fetchers (bot-protection) but was confirmed loading correctly, with a matching page title, in a real browser. Source 4's URL was updated to NCBI's current canonical domain (`pmc.ncbi.nlm.nih.gov`) after the original `ncbi.nlm.nih.gov/pmc` address redirected there.

## Post-launch improvement pass (`planning/TODO.md` G1-G20, implemented)

G7/G8 stayed parked in `planning/LATER.md` per that doc — everything else in the range landed in one pass:

- **G1/G6 (richer secondary-region readouts):** Region B/C now render the same dampening/acceleration/trajectory readouts Region A already had (`render_secondary_region()`) — all pre-existing `RegionState` methods, so no new game logic, only new elements to write them into. G6's `temperature_saved`-style stat rides the same `trajectory_message()` call.
- **G2/G15 (best-region comparison):** `best_region_identifier()`/`best_region_message()` compare current temperature across the three player-managed regions (never Region D — see G13) and render an always-visible comparison line. G15 folds the same identifier into the ratings-backend feedback payload as an aggregate stat via a hidden `#best-region-hidden` span the plain-JS submission script reads back.
- **G3 (critical melt status):** a third, distinct `_melt_status_label()` state — "critical" once `acceleration_factor()` clears `CRITICAL_ACCELERATION_FACTOR` (2.0x background rate), on top of the existing binary melting/stable read, with its own `.melt-status--critical` CSS class. Deliberately left `.melt-status--active`'s existing red alone (Sep 2026 visual pass already called that color load-bearing game state) — critical gets its own distinct treatment instead of overriding it.
- **G4 (region strategy labels):** an optional, freely-typed `strategy_label` per Region B/C, purely descriptive and never read by game logic — persisted through save/load like every other region field.
- **G5:** already covered pre-pass by the existing background-rise info-toggle; extended its copy to also mention the new "critical" tier.
- **G9 (meter-cap clarity):** a note appears once `temperature` exceeds `TEMPERATURE_METER_MAX` explaining the bar is visually capped at +30° while the real number keeps climbing — without it a maxed bar read as "capped for real."
- **G10 (milestone-delay callout):** a second, higher warming milestone (`SECOND_WARMING_MILESTONE`, +15°) past the original melt threshold. The first time a region's real temperature lags behind its own undampened counterfactual crossing it, a one-tick banner announces the delay — concrete proof intervention bought time, not just a slowed rate in the abstract. Needed genuine new state (`dampening_at_melt_start`, snapshotting dampening at the exact moment melt starts) to let the `early_investor` achievement ask "was protection already in place *before* melt" rather than "is it in place right now."
- **G11 (preset strategies):** one-click Growth/Preservation/Balanced presets for Region B/C (`apply_preset()`), each spending as much of the region's current funds as it can afford toward a named weighting — approximates the ratio deterministically since fractional investments don't exist.
- **G12 (invest forecasts):** small inline previews next to each invest button (funds/round or dampening %) showing what a click would do, rather than requiring a trip to How to Play's constants tables.
- **G13 (worst-case Region D):** a fourth, always-auto-played region that spends every affordable unit on Output only and never touches Preservation/Monitoring — its trajectory is numerically identical to Region A's own `counterfactual_temperature` (both use the undampened feedback formula), making "what if nobody intervened" a concrete, playable region rather than only an abstract number on Region A's card. Hidden behind a reveal toggle so it never clutters the default screen; revealing it doubles as the `worst_case_witnessed` achievement's tracked state.
- **G14 (melt-threshold gridline):** `mini_temp_graph_svg()` draws a faint dashed reference line at `MELT_THRESHOLD` whenever it falls within the graph's visible range.
- **G16 (region flavor lines):** one static descriptive sentence per region (`REGION_FLAVOR`) — coastal tundra for B, boreal interior for C, "no steward" for D — cosmetic only, never read by game logic.
- **G17 (next-round preview):** a hover tooltip on Advance Round previewing all three player-managed regions' next warming rate, rather than a permanent on-screen line.
- **G18 (dampening-tiered feedback message):** `intervention_feedback_message()` now varies its phrasing ("a modest start" / "a meaningful buffer" / "a strong shield") by dampening magnitude instead of one fixed sentence regardless of how much protection is actually in place.
- **G19 (personal best):** a per-browser "best `temperature_saved()` ever reached" persisted via `localStorage`, deliberately outside `get_state()`/the save-code system — it tracks the best this *browser* has seen across every session/save, the same distinction Canopy's B14/Tide's D13 personal-best features already draw. Degrades to "no personal best recorded" on any storage failure (private-browsing mode, etc.) rather than crashing the module.
- **G20 (intervention free-text):** a dedicated optional textarea for "what specifically felt like it was (or wasn't) working," separate from the general closing-thought comment box, folded into the same `response` string sent to the ratings backend.

Full pytest suite (114 tests) green after the pass.

## Achievements (implemented)

18 achievements added per the hub-wide framework (`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md`), following SOL's reference integration: `achievements.json` catalog, `game.py`'s `ACHIEVEMENT_CHECKS`/`ACHIEVEMENT_PROGRESS`/`achievement_ids_earned()`/`achievements_summary()`, an in-game toggle + panel, an unlock toast, a hub-dashboard link, and `achievements_earned` riding `get_state()` (never read back on load). Span first-investment/all-three-categories milestones, dampening thresholds (25/50/85%), the tipping-point-witnessed and early-investor (dampening already in place before melt started) moments, `temperature_saved` thresholds (5/10/20°), a slow-burn achievement (accelerated melt for 15+ rounds while staying under 1.5x acceleration), funding/longevity targets, and three achievements new to this pass's own G-item mechanics: `beat_both_regions` (G1/G2's comparison), `preset_strategist` (G11), and `worst_case_witnessed` (G13). Two module-level flags (`preset_used_ever`, `worst_case_region_revealed`) and one new `RegionState` field (`dampening_at_melt_start`) exist purely to make "has the player ever done X" / "was this true at some past moment" derivable, since neither can be recovered from present-only state. Hub-side `script.js` registration (`GAMES_WITH_ACHIEVEMENTS`) is out of scope for this games/thaw/-only dispatch, per the pattern already established for Grid/Canopy/Continuum/Herd/Drift's own rollouts.

## Colorblind-safety audit (audited, no change needed)

Audited as part of the site-wide colorblind-safety audit (`planning/TODO.md`, Okabe-Ito-palette method per Continuum's Phase 5, redundant-cue method per Canopy's B9, audit-only method per Tide/Aftermath/Herd's own precedent). The one real red/green pair in this game is the `tipping-point-flash` (red, fired on `#game` the instant melt starts) vs. `intervention-flash`/`.dampening-flash` (green, fired on the dampening readout the instant a preserve/monitor investment lands) — explicitly designed as an intentional color contrast (see the Pass 3 note above: "deliberately green ... vs. the tipping-flash's red").

Checked whether this is a real hue-only encoding a colorblind player would need to tell apart, the same question Tide's D11 asked of its land/flooded pair — concluded no fix is needed, for reasons distinct from Tide's:

- The two flashes never need to be told apart from each other: they're one-shot 900ms animations fired by two different actions at two different times, never shown side by side the way Continuum's log rows or Grid/Drift's trend-graph lines are — there's nothing to visually *confuse* one for the other.
- Each flash is redundantly, fully described by text that changes in the exact same render pass: the tipping-flash co-occurs with `melt-status-display`'s text changing to an explicit sentence ("Permafrost is actively melting — methane feedback is accelerating warming." / the critical variant), plus the permafrost hero illustration visibly cracking and venting methane bubbles (a shape/texture change, not a color one). The dampening-flash co-occurs with the dampening percentage number itself increasing and `intervention-feedback-display`'s text updating. A player who can't perceive the flash's hue at all still gets the same information from the text and (for the tipping event) the crack/bubble animation.
- Everything else checked was already safe by construction: `.meter-fill--temperature` is a single-hue bar (no red/green counterpart, matching Continuum's own "single-hue bars aren't a paired confusion" finding), `.melt-status--critical` currently carries no color of its own (text-only), and the feedback survey's `.selected` button state uses one green highlight applied uniformly to whichever button (Yes or No) was clicked — the button's own label text, not color, carries the meaning, the same pattern SOL's audit found for its own selection states.

No CSS or `game.py` change made. Full pytest suite (unchanged) stays green since nothing was touched.

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A-/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`, following Aftermath/Herd's
own `settings.js` builds) and a reduced-motion checkbox — toggled from a new
"⚙️ Settings" button in the top toolbar alongside Tutorial/How to Play/
Achievements, rendered into a `.section`-styled panel matching the existing
`#howto-panel`/`#achievements-panel` hidden-until-opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely — it
has no Python dependency and works even if `game.py` never boots, and it's
wired up in `<head>` before `game.py`'s own `<script>` runs. `style.css`
gained a `:root { --text-scale: 1 }` custom property read by `html
{ font-size: calc(16px * var(--text-scale, 1)) }` (every font-size in this
file is already in rem, confirmed by grep) and a blanket
`html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant, additive to the existing
`prefers-reduced-motion` media-query-gated rules already in this file.
Deliberately only the *timing* of the tipping-point-flash/intervention-flash
animations collapses — their colors (red/green, meaningful game-state cues
per this game's own colorblind-safety audit above) are untouched.

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (`planning/LATER.md`'s standing "what can you actually do with
audio" question), so a sound control here would control nothing real.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`thaw-text-scale`, `thaw-reduced-motion`), never touching
`get_state()`/`load_state()`.

Verified live via a local server on a fresh port (sidesteps an unrelated
browser heuristic-caching quirk in the dev-server setup, unrelated to this
game's own code): text-scale increases the whole page's font size correctly
(confirmed via computed `font-size` on `<html>`), the reduced-motion
checkbox collapses `button.primary`'s `transition-duration` to ~0, and both
settings persist correctly across a full page reload. Zero new console
errors — the pre-existing ServiceWorker-registration quirk and a report-only
AdSense-iframe CSP notice are both already present on the unmodified page.
Full pytest suite (114 tests, unchanged — `settings.js` is plain frontend JS
with no Python surface) stayed green throughout.


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

## "What's New" changelog panel (K16, planning/TODO.md, site-wide goal)

A small in-game highlights panel — a curated `changelog.json` (flat list of
`{"date", "entry"}` objects, fetched into the Pyodide boot sequence exactly
like `achievements.json` already is) rendered into a hidden-until-opened
"📋 What's New" panel — same toggle+panel idiom as the achievements panel,
with a plain date+text-card layout (no earned/unearned styling, since a
changelog entry has no checkable condition). `CHANGELOG` is sorted
newest-first at load time and degrades to an empty list on a
malformed/missing file, matching `ACHIEVEMENTS`'s own defensive pattern.

Populated with 9 real highlight entries pulled from this file's own
milestone table and iteration notes above, newest first (2026-09-19 back
to the 2026-08-07 all-milestones-shipped entry). Covered by
`tests/test_changelog.py` (catalog sanity, newest-first ordering, toggle
open/close, panel content, no state mutation as a side effect — same
suite shape as Herd/Aftermath's own `test_changelog.py`). Full pytest
suite (114 → 123 tests) stayed green throughout; verified live via a
local server — the panel opens, shows all 9 real entries in the correct
order, and there are zero new console errors (the pre-existing
ServiceWorker-registration quirk on this dev setup is unrelated and was
present before this change).

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited whether a returning player who's skipped or forgotten the
tutorial (`THAW_TUTORIAL_STEPS`) can still make sense of the permanent
UI's non-obvious parts. Confirmed via `shared/tutorial.js` that the
"How to Play" panel is literally rendered *from* `THAW_TUTORIAL_STEPS`
(`renderHowTo()`), not separate copy — so "covered by the tutorial" and
"covered by How to Play" are the same claim here, and anything the
walkthrough doesn't mention has zero permanent, reachable-any-time
explanation unless something else on the page carries it. `game.py` had
zero `title=`/`aria-label` attributes going in, so this was a real
investigation, not an assumption.

Most of the permanent UI already covers itself well:
- Every non-obvious status readout in `#status` (background-rise
  compression, melt threshold + critical tier, dampening's scope and
  "does nothing pre-melt" caveat, acceleration multiple, and the
  trajectory/temperature-saved comparison) has its own permanent
  `.info-toggle` `<details>` disclosure right next to it.
- `melt-status-display`, `intervention-feedback-display`,
  `temperature-cap-note`, and `milestone-delay-callout` are all live,
  always-current status text driven by `render()` every tick — a
  stronger form of explanation than a static tooltip, matching Trade
  Empire's `ship_status_text()` precedent.
- The Output row's `.info-toggle` already explains the
  output-vs-preserve/monitor split ("Preservation and Monitoring below
  do the opposite...") on behalf of all three investment rows, so
  Preserve/Monitor don't need their own copies.
- Region B/C's mirrored dampening/acceleration/trajectory readouts and
  Region D's worst-case panel reuse mechanics already explained for
  Region A — not new mechanics needing their own explanation, the same
  reasoning Trade Empire's audit applied to its Rift Colonies.
- G12's invest-forecast spans and G17's Advance-Round hover tooltip
  already preview each investment's/round's effect inline.

**Real gap found and fixed:** the three per-preset buttons on Region
B/C (`Preset: Growth` / `Preset: Preservation` / `Preset: Balanced`,
G11) were added after the tutorial copy was written and are never
mentioned in `THAW_TUTORIAL_STEPS` or anywhere else permanent. Reading
`apply_preset()`/`PRESET_WEIGHTS` confirmed the actual behavior is
genuinely non-obvious from the label alone: a click immediately spends
*everything the region can currently afford* toward that weighting, in
one go — not a standing policy a player can toggle on/off, which a
returning player could easily assume given every other investment
control in this game is an incremental per-click spend. Exactly the
"forgot a mechanic" shape this audit exists to catch.

**Fixed:** added `game.py`'s `preset_tooltip_text()`, built directly
from `PRESET_WEIGHTS` (so the copy can't drift from the real ratio if
it's ever retuned), and wired it to each preset button's `.title` once
in `setup()` (static per-preset text, not state-dependent, so it
doesn't need to live in `render()`). Growth's tooltip reads "Spends
everything this region can currently afford right now, on Output — a
one-time action, not an ongoing policy."; Preservation/Balanced list
each category's approximate percentage the same way.

Verified: full pytest suite (123 tests, unchanged — this is `.title`
only, no new game logic) stayed green. No `index.html`/CSS change
needed; no other permanent control was found undocumented.

## UI decluttering pass (2026-09-20, planning/TODO.md closing task — audited, no change needed)

Audited as the last open item in `planning/TODO.md`'s "Big standalone features" section (the user's own crowding note: "everything looks very crowded... making sections either collapsible or other 'screens' within a game could help"). Read `index.html`/`style.css` section by section, then compared directly against Loop's own audit from the same pass (see `games/loop/CLAUDE.md`, which did find and fix a real issue) to calibrate what "genuinely crowded" means in practice, since both games share the same climate-quartet-2 status-block layout pattern.

**Findings:** `#status` is long — round/funds/temperature, melt status, dampening, intervention feedback, acceleration, trajectory, the mini-graph, personal best, roughly a dozen lines — but unlike Loop's `#status`, nearly every one of those lines is a load-bearing per-turn mechanic readout that a specific iteration pass explicitly built to be always visible, not supplementary context: `melt-status-display` and the tipping-flash (Pass 1), `dampening-display`/`intervention-feedback-display` (Pass 3's specific fix for the "silent number with no felt consequence" risk), `acceleration-display` (Milestone 4's "visible acceleration" requirement), and `trajectory-display` (Milestone 5's hope-angle payoff) are each the direct subject of a design pass that wanted exactly this always-on visibility — collapsing any of them behind a disclosure would undo that design intent, not just tidy the screen. The five inline `.info-toggle` "i" bubbles already interspersed through the section are the existing collapsed/supplementary layer; the stat lines themselves aren't candidates for a second layer of collapsing on top of that. The one line that reads as genuinely supplementary, `personal-best-display`, is a single line — not enough density on its own to justify a `<details>` wrapper.

Region B/Region C's comparison cards are dense (a mini-graph plus six stat lines plus investment/preset buttons plus a label input, times two), but Pass 2's own design note calls for exactly this: "the divergence between regions is the dominant visual read of the screen" — this section is supposed to be visually heavy, since side-by-side comparison is the whole point of the addition. Region D (the worst-case comparison) is already collapsed behind `#worst-case-toggle-button`/`#worst-case-panel`, so the site's disclosure pattern is already applied exactly where it fits.

**Conclusion: no crowding problem found that isn't either intentional (region comparison) or already addressed by the existing `.info-toggle` layer.** No `index.html`/`style.css`/`game.py` change made. Full pytest suite (123 tests, unchanged) stays green since nothing was touched.

## Tech notes

- Python/Pyodide, per root conventions.
- The feedback-loop math (melt rate feeding back into warming rate) is the trickiest logic in this set — isolate it in its own well-tested function early, since everything else in the game depends on getting this right and legible.
- Space-theme visual pass (Sep 2026): adopted the site-wide starfield/nebula background (`shared/space-bg.css`) and SOL's glass-panel language — `#game`, `.section`, `.region-card`, `.context-blurb` moved from flat solid backgrounds to translucent gradient + backdrop-blur + violet-tinted borders; `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy inset highlight and an added `:hover` brighten (on top of the existing `:active` darken); `.meter-fill--temperature` gained a matching glow via `box-shadow` only. `game.py` was not touched — CSS/HTML only. Deliberately left alone: `.melt-status--active`'s red, `.mini-temp-line`'s stroke color, and both the `tipping-point-flash`/`intervention-flash` keyframes (red tipping cue and green dampening cue) — these are meaningful game-state/feedback colors and animations, not chrome, so only their surrounding panels were restyled. `shared/info-page.css` also left untouched (shared across all 8 climate-quartet games, out of this game's scope). Full pytest suite (110 tests) green before and after.

## Hidden-panel display bug fix (2026-09-21)

Found during a site-wide sweep after Aftermath's own Z12/panel-hiding
fixes surfaced the same pattern elsewhere: the changelog panel (`.changelog-panel`) set `display:
grid` as a plain class rule with no `[hidden]` override. Author-origin
CSS always beats the browser's own `[hidden] { display: none }` UA rule
regardless of specificity, so once that class applied, the panel stayed
visible as an empty box before its first open, and stayed visible with
its last-rendered content forever after being toggled closed. Fixed by
adding a `.<class>[hidden] { display: none; }` override right after each
affected rule, the same pattern SOL/Trade Empire/Continuum's own
achievements CSS already used correctly. CSS-only; no Python change
needed. Full test suite green, unaffected (pure CSS change).

## Exponential-slowdown bug fix (2026-09-21)

Found by the Z25 save-payload audit while measuring a long simulated
session, then confirmed directly: `_auto_play_worst_case_region()` spent
Region D's funds on Output one unit at a time, via `while region_d.invest
("output"): pass`. Region D's whole premise is neglect — every round's
income (`capacity["output"] * OUTPUT_INCOME_PER_UNIT`) gets reinvested
straight back into more output at a flat per-unit cost, which compounds
capacity by roughly 30% every round. That exponential growth in Region
D's capacity is the intended "look how much worse doing nothing gets"
story — but spending it down one `invest()` call at a time meant the
loop's iteration count grew exponentially with round count too, not just
the number it was simulating. A real session's Advance Round click could
balloon to multiple seconds by round 50-60 and keep climbing from there.

**Fix:** compute the affordable unit count directly (`funds // cost`) and
apply it in one step, instead of looping. Produces the exact same
end state `invest()` would have one unit at a time (same flat per-unit
cost, no partial-unit spend) — verified in `tests/test_worst_case_perf.py`
against a hand-computed expected outcome, plus a regression guard timing
400 simulated rounds (was minutes and climbing; now ~2ms). 152 -> 156
tests, flake8 clean.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag thaw-milestone-0N`.
- Update the milestone table Status as work happens.

## Round-2 build notes (2026-09-20)

Done (planning/TODO.md "Per-game: Thaw"): G2 (Region A flavor subtitle), G4 (worst-case toggle tooltip), G6 (labelled melt-threshold gridline), G8 (warning icon on critical tier via CSS), G10 (combined three-region next-round tooltip with projections), G12 (one-time pre-emptive dampening callout), G14 (preset purchase previews in hover tooltips, computed on a scratch region), G16 (shape-coded trend arrows), G18 (tier icons in intervention message), G19 (collapsible scientist's log, capped at 40, persisted), G20 (tooltip + info toggle on the +15 milestone), G22 (personal best now spans A/B/C and records the region), G24 (acceleration pulse on entering critical), G26 (strategy-label placeholder example), G28 (rounds-since-tipping-event counter), G30 (first-reveal note for Region D). New state: per-region `just_became_critical`, `rounds_since_tipping_event`, `tipping_events`, `just_preempted_melt`; top-level `worst_case_intro_seen`, `science_log` (all default safely for old saves). Tests: `tests/test_round2_items.py`, 137 total.
Left: G3, G5, G7, G9, G13, G15, G17, G21, G23, G27, G29 (larger mechanics). G11 built later — see its own note below.

## G11 — community "average acceleration factor" comparison (2026-09-21)

`planning/TODO.md`'s Per-game: Thaw section: "G11: A community 'average
acceleration factor' comparison, reinforcing the hope-angle message that
intervention is common and effective *(needs Z1)*." Z1's shared
aggregate-stats backend (`app/stats.py`, `app/main.py`) is built and
deployed; this pass also registered `region.average_acceleration_factor`
in its `STATS_FIELDS` whitelist for `"thaw"` (previously only
`round_number`/`funds`/`temperature` were exposed).

Built byte-for-byte the same optional-hook architecture as Grid's own
C15 (`_request_comparison()`/`window.gridCompare`, the reference
integration for this feature in this hub): `game.py`'s
`_request_community_comparison()` does a lazy, guarded `from js import
window` (no-op under pytest) and calls `window.thawCompare(accel)` if
that hook exists; `index.html`'s own inline `<script>` defines the hook,
fetches `GET /stats/games/thaw/percentile?field=region.average_
acceleration_factor&value=<x>`, and fills `#community-compare-display`
with a sentence — or leaves the fallback text in place on any error,
unreachable backend, or the endpoint's own `suppressed` flag.

**Metric: a new `RegionState.average_acceleration_factor`**, a lifetime
running mean of `acceleration_factor()` across every round played,
updated incrementally each `advance_round()` via Welford's mean formula
(`_record_acceleration_sample()`) rather than a second unbounded history
list the way `temperature_history` already tracks the raw trajectory.
Region A only, matching this game's own established convention (Pass 3's
note already scoped the primary intervention lever to Region A, not the
B/C comparison regions or D's auto-played worst case). Rides `get_state()`/
`load_state()` as a plain field (`acceleration_samples` alongside it, so
the running mean can keep being updated correctly after a load), safe-
defaulting for older saves that predate this field.

**Wording — the real judgment call this item asked for.** G11's own
framing is explicit that this should reinforce the hope angle ("intervention
is common and effective"), not just report a bare percentile the way
Grid's C15 does. `index.html`'s hook branches on which side of the
community average the player falls: beating most other players' rate
("your warming has accelerated less than N% of them — real proof that
intervention slows the slope, and most players are managing to slow it
at least some too") and *not* beating most of them are both phrased as
evidence intervention works, never as a scolding "you're doing worse"
message — the second branch reads as "look how much further this can
still go," using the very fact that other players did better as proof the
lever itself is real and available, not a comparison to feel bad about.

Tests: `tests/test_community_compare.py` (14 new, Thaw 137 -> 151) —
covers the running-average calculation itself (Welford update across
several rounds, save/load round-trip, old-save default), the panel
toggle/fallback text, the hook firing with the right value, safe no-op
without a hook, and re-asking on every render while the panel stays open
(mirrors Grid's own C15 coverage shape). flake8 clean.

Verified live against the shared `hub-dev-server`: the panel opens,
shows the fallback text, and `window.thawCompare` is defined and
callable with zero code-level console errors. The actual round-trip to
the deployed production endpoint could not be exercised from this
sandboxed browser pane — external fetches to that host fail at the
network layer here regardless of game code, the same environment
limitation this session's Herd F7 build note documents in more detail.
Once a production deploy picks up the `app/stats.py` whitelist change,
this starts showing real percentiles with zero further code changes.

- 2026-09-21: G2 -- `best_region_message()` now names the winning region's preserve/monitor/output mix.

## G5 — concrete years-per-round calibration (2026-09-21)

`planning/TODO.md`'s completion audit (V-E-2) found G5's original ask —
a concrete "each round ≈ X years of real-world warming" line — was never
actually built; only the vague info-toggle wording ("stylized several
years") existed. User's call when asked: "may as well design a real
number behind it, you pick what makes the most sense."

**The math:** `BASE_TEMP_RISE_PER_ROUND = 1.0` (this game's fixed
per-round background rise, displayed to the player as `+1.0°`). NOAA
Climate.gov ([Climate Change: Global Temperature](https://www.climate.gov/news-features/understanding-climate/climate-change-global-temperature))
states the recent-decades rate as "0.36°F (0.20°C) per decade" since
1982 — i.e. 0.02°C/year. Dividing the fixed per-round rise by that
real-world annual rate: `1.0 / 0.02 = 50` real-world years per round.
Used the recent-decades rate rather than the long-run since-1850 average
(NOAA's own "0.06°C/decade" figure) because it's the pace the game's own
existing sentence already frames as "today's" — the long-run figure would
roughly triple the years-per-round number and undersell how much faster
warming has gotten.

**Change:** `index.html`'s warming-rate info-toggle (`#rise-rate-display`'s
`.info-toggle`) now states this concretely — "At today's warming pace
(NOAA: about 0.20°C per decade since 1982, i.e. 0.02°C/year), this
game's fixed +1.0°/round works out to roughly 50 years of real-world
warming compressed into one round" — replacing the old "several years"
hand-wave, while keeping the original 1.1°C-over-150-years historical
anchor sentence and the stylization/"not a literal calendar unit"
caveat. `index.html`-only: confirmed no `game.py` logic or test reads
this string, and every other `.info-toggle` disclosure in this game
(melt threshold, dampening, etc.) is likewise static prose in `index.html`
rather than Python-rendered, so this stayed consistent with that existing
pattern rather than becoming a computed value in `game.py`. `changelog.json`
got a matching entry. Full pytest suite (156 tests, unchanged — no logic
touched) stayed green; verified live via the shared `hub-dev-server`, the
new text renders correctly with zero console errors.
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

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`.

**Real bug found and fixed:** `.region-strategy-label-input` (a plain
`<input>` with no CSS width of its own) fell back to the browser's default
intrinsic size (~20 characters), which — unlike every other child of its
flex-item `.region-card` — doesn't shrink with its container. At 320px
that pushed the card (and the page, by a few px) past the viewport edge.
Fixed by sizing it to its own container (`width: 100%; max-width: 100%;
box-sizing: border-box`) instead of relying on the browser default.

No other overflow found at 320px. `flake8`/tests unaffected (pure CSS).

## Difficulty-aware achievements audit (Z27, site-wide goal)

Checked `game.py` for a difficulty/hard-mode toggle. The only candidate
that came up in an initial grep was `worst_case_region_revealed`
(Region D, the "what if nobody intervened" comparison) — read its own
comment and implementation directly: it's a pure visibility reveal for a
counterfactual comparison panel (and doubles as the tracked state for the
`worst_case_witnessed` achievement itself), not a toggle that changes any
numeric constant, multiplier, or game-balance behavior anywhere. **Thaw
has no player-facing difficulty/hard-mode toggle — not applicable.** No
code touched.

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
`localStorage["whats-new-seen:thaw"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="thaw">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Narrative log migrated to shared component (Z11, site-wide goal)

G19's scientist's log (`science_log`, capped at `SCIENCE_LOG_MAX = 40`) now
delegates its append-and-cap bookkeeping to a new `shared/narrative_log.py`
module, generalized from Continuum's own "Chronicle" log pattern (that
game's `log.py` is the reference integration; this is the second). Only
the cap/append logic moved -- `_record_round_events()` still appends each
event's own `{"region", "round", "text"}` dict directly, then calls
`narrative_log.cap_entries(science_log, SCIENCE_LOG_MAX)` once after the
loop, matching this game's own pre-migration behavior exactly (a single
unconditional trim per round regardless of how many regions had something
happen that round, not a trim-per-append -- an early attempt to call the
shared module's own `add_entry()` per event inside the loop changed this
behavior in a test-caught regression, since it only trims on the calls
that actually appended something). `science_log_html()`'s own rendering
(an HTML-string builder feeding a `<ol>`/`<li>` list inside a `<details>`
disclosure) was deliberately left as-is rather than forced onto the
shared module's DOM-based `render()` -- a different, already-shipped,
already-tested markup shape with no real duplication left to extract once
the cap/append logic moved out. `index.html`'s boot script fetches
`shared/narrative_log.py` the same way it already fetches
`shared/info_page.py`. All 156 tests pass unchanged in substance; `flake8`
clean. Verified live: advancing rounds until melt started still produced
the correct three-region log entries, rendered in the same `<li>` markup
as before, with zero console errors.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...]})` call at the
end of `index.html`, listing this game's real toggle-button + hidden-
panel pairs: How to Play, Achievements, What's New, Community Compare,
Settings, the Info Page, and the Worst-Case Region reveal
(`worst-case-toggle-button`/`worst-case-panel`). `?` opens a small
floating shortcuts-help overlay; `Esc` closes it and clicks the toggle
button of whichever listed panel is currently open, reusing each panel's
own open/close logic.

## Region rescue (G21, 2026-09-26)

A last-resort lever for a region that has tipped into the critical tier (melting with acceleration at or above 2x). Once per region, ever, the player can pay `RESCUE_COST` (200 funds) for `RESCUE_DURATION_ROUNDS` (5) rounds of extra feedback dampening (`RESCUE_DAMPENING_BONUS` 0.5, capped at `RESCUE_MAX_DAMPENING` 0.95, which deliberately exceeds the normal 0.85 investment cap). It buys breathing room, not a fix: when it lapses only real preserve/monitor investment holds the loop, and the region can read as critical again.

- `RegionState.effective_dampening_fraction()` (investment plus any active rescue) is what `feedback_bonus()` uses. `feedback_dampening_fraction()` stays investment-only on purpose, so the dampening achievements, the Dampening readout and `dampening_at_melt_start` can't be inflated by a temporary emergency boost.
- The rescue lowers the acceleration reading, so `is_critical()` goes false while it runs; the status line handles that by checking "rescue active" first. Re-entering critical after it lapses counts as another tipping event, which is the honest reading.
- UI: an "Emergency rescue" button and status line in Region A, B and C (Region D is auto-played and has none). The button is shown only while the region is critical and the rescue unspent, and disabled until funds cover the cost; the status line is hidden on a stable region.
- Save: `rescue_used` and `rescue_rounds_left` are written only once a rescue has been used (older saves and untouched regions are byte-identical), and validated on load (a bool, an int in 0..5, never a bool-as-int; an active countdown implies used).
- 156 -> 172 tests (`tests/test_region_rescue.py`); verified live: the button appears disabled or enabled by funds, a click spends 200 and the warming rate drops from 1.85 to 1.52 then counts down, zero console errors.

## Starting policy stance (G13, 2026-09-26)

An optional, once-only framing for Region A, chosen before round 1 (and before anything is invested): Growth-led (+100 starting funds), Balanced (+40 funds, +3% dampening) or Mitigation-led (+6% dampening). Deliberately modest and roughly value-equivalent, so no stance is clearly best ("subtly weighting starting dampening"). Region B/C already express strategies through presets and Region D is the unmanaged baseline, so only Region A gets one.

- `POLICY_STANCES` holds the table; `RegionState.policy_stance` (key or None) and `policy_dampening` (derived from the key) add into `feedback_dampening_fraction()` and so obey `MAX_FEEDBACK_DAMPENING`.
- A stance is not an investment: it doesn't earn `first_intervention`, and the pre-emptive-investment callout now requires real preserve/monitor capacity (it used to key off any nonzero dampening). With nothing invested, `intervention_feedback_message()` says the head start comes from the policy stance.
- Save: only the key is written (and only when set); the dampening is re-derived on load, and an unknown or wrong-typed key loads as no stance. Locked once round 1 passes or anything is invested.
- 172 -> 187 tests (`tests/test_policy_stance.py`); verified live, zero console errors.

## Permafrost restoration (G15, 2026-09-26)

The late-game payoff for a region whose feedback loop is contained. A melting region that holds its acceleration at or under `RESTORATION_MAX_ACCELERATION` (1.3x) for `RESTORATION_STREAK_ROUNDS` (3) consecutive rounds starts restoration: each round, every Preservation unit pulls back `RESTORATION_PER_PRESERVE_UNIT` (0.05) degrees of melt-driven warming, up to `RESTORATION_MAX_PER_ROUND` (0.5), and never below the melt threshold. It removes real accumulated temperature but can't outrun the fixed background rise, so it slows the climb rather than reversing it (which fits "reverses some melt", and keeps the game's "background warming is outside your control" rule intact).

- The streak is judged on `_investment_acceleration_factor()` (investment dampening only), so a temporary emergency rescue never counts as "stabilized". Losing control (acceleration back above 1.3x) resets the streak; restored degrees stay counted.
- Stats: `stabilized_rounds` and `restored_total`; a per-region status line ("Restoration under way / paused, N degrees pulled back") appears only once relevant, and the first restoring round is logged in the scientist's log.
- Save: both fields written only when nonzero; validated on load (int in range, finite non-negative float, never a bool). 187 -> 202 tests (`tests/test_restoration.py`); verified live, zero console errors.

## Thaw forecast mini-game (G27, 2026-09-26)

Before advancing, the player may lock in a guess of Region A's temperature after the coming round; on Advance it is scored against the real figure (within `FORECAST_TOLERANCE`, 0.2 degrees, is a hit) and the guess clears. The reward is purely cosmetic: a running record and a title (Apprentice, Seasoned at 5+ forecasts and 50%, Master at 10+ and 75%). Nothing in any mechanic reads it. The game is deterministic, so a careful player can hit every forecast from the displayed warming rate, which is deliberate: the mini-game exists to make that number worth reading (restoration and rescue make the arithmetic less obvious).

- Module-level `forecast_guess`/`forecast_total`/`forecast_hits`/`forecast_last`; `lock_forecast()` rejects blank, non-numeric, non-finite and out-of-range (-100..1000) input; `resolve_forecast()` runs right after Region A advances.
- Save: a `forecast` dict (`total`, `hits`) written only once one has been scored, validated on load (non-negative ints, hits never above total, bools rejected); the locked guess and last result are per-session and reset on load.
- 202 -> 216 tests (`tests/test_forecast.py`); verified live, zero console errors.

## Global vs. regional framing toggle (G29, 2026-09-26)

One button (`framing-toggle-button`) flips a summary line between two readings of the same numbers: "regional" (default) reads Region A as the player's own choices (its temperature and degrees saved), "global" reads Regions A-C together as one planet (average warming, how many of the three are melting, average degrees saved). Presentation only: nothing in any mechanic reads `framing`, and Region D (the unmanaged what-if) is never part of either summary. Only the non-default framing is saved; a wrong-typed or unknown value loads as "regional". 216 -> 226 tests (`tests/test_framing.py`); verified live, zero console errors.

## Climate archive (G23, 2026-09-26)

A "Climate archive" panel (toggle under the personal-best line) with one row per player-managed region (A/B/C): the most degrees saved versus no action, the furthest round reached and the highest dampening built, across every session on this device. It generalises the single overall personal best (G19/G22) to a per-region, three-stat record. Stored in `localStorage` (`thaw_climate_archive_v1`), deliberately not part of `get_state()` or the save code (it is a per-browser record, the same distinction the personal best draws), and only written when a record is actually beaten. Every stored value is cleaned field by field on read (`_clean_archive_entry()`): non-finite, negative, wrong-typed or out-of-range values fall back to that field's default, and malformed JSON or a non-object loads as a blank archive. Region D (the unmanaged what-if) has no entry. 226 -> 237 tests (`tests/test_climate_archive.py`, with a fake `localStorage`); verified live: records written, then read back after a reload into a fresh round-1 game.

## "Four regions, one story" (G17, 2026-09-26)

A light narrative thread across the four regions without merging their mechanics: a collapsed "Four regions, one story" disclosure showing one shared research station. Every Monitoring & Response unit funded in Regions A, B or C adds to a common pool of observations (`shared_research_units()`); at 3, 8 and 15 units a new chapter appears (`SHARED_RESEARCH_CHAPTERS`), and the last one writes Region D in as the unfunded control every paper cites. It is derived entirely from live capacity, so it has no state and nothing to save, and it never feeds back into any region (verified by test), so the four stay independent. 237 -> 247 tests (`tests/test_shared_research.py`); verified live (3 monitors unlocked Chapter 1), zero console errors.

## Permafrost carbon bank (G3, 2026-09-26)

A shared bank that turns sustained good play in one region into a push in another. After each Advance Round, every one of Regions A-C that has at least one Preservation unit and holds acceleration (on investment dampening alone, so a temporary rescue can't farm it) at or under `CARBON_BANK_MAX_ACCELERATION` (1.2x) banks one credit, up to `CARBON_BANK_CAP` (50). `CARBON_CREDITS_PER_GRANT` (10) credits can be spent, via one button per region, on a one-time `CARBON_GRANT_FUNDS` (+120) grant to that region only. Region D never earns or receives. Save: `carbon_bank` written only when above zero, validated on load (int 0..cap, bools rejected). 247 -> 262 tests (`tests/test_carbon_bank.py`); verified live (10 rounds banked 10 credits, spending gave Region B +120), zero console errors.

## Tipping cascade (G5, 2026-09-26)

When Region A or Region B starts melting, there is a `CASCADE_CHANCE` (25%) chance the shock spreads down the chain (A to B, B to C) as a one-time `CASCADE_BUMP` (0.5 degrees). The game has no random source (every round is reproducible), so the chance is a fixed pseudo-random roll from the round and source region (`cascade_roll()`): a given run always cascades the same way, but a player can't predict or reroll it. The bump is added to the receiving region's temperature, its counterfactual and its latest history point, because no intervention could have prevented it, so "degrees saved" is unchanged. The chain is deliberately one-way and never reaches Region A or Region D, which keeps Region D numerically identical to Region A's counterfactual (tested). Only the round a source first melts can cascade, and the hit is logged in the scientist's log. Nothing new is saved (the effect lives in the saved temperatures). One existing test (`test_regions_diverge_with_different_strategies`) had a thin margin that a cascade could flip, so it now invests eight Preservation units instead of three. 262 -> 274 tests (`tests/test_tipping_cascade.py`); verified live with the chance forced on, zero console errors.
