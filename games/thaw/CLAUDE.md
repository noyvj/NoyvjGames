# Thaw — Permafrost Feedback Loop Game

**Read `../climate-quartet-2-plan.md` first for shared conventions.** This file is Thaw-specific only. **Build second** in this set.

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

## Tech notes

- Python/Pyodide, per root conventions.
- The feedback-loop math (melt rate feeding back into warming rate) is the trickiest logic in this set — isolate it in its own well-tested function early, since everything else in the game depends on getting this right and legible.
- Space-theme visual pass (Sep 2026): adopted the site-wide starfield/nebula background (`shared/space-bg.css`) and SOL's glass-panel language — `#game`, `.section`, `.region-card`, `.context-blurb` moved from flat solid backgrounds to translucent gradient + backdrop-blur + violet-tinted borders; `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy inset highlight and an added `:hover` brighten (on top of the existing `:active` darken); `.meter-fill--temperature` gained a matching glow via `box-shadow` only. `game.py` was not touched — CSS/HTML only. Deliberately left alone: `.melt-status--active`'s red, `.mini-temp-line`'s stroke color, and both the `tipping-point-flash`/`intervention-flash` keyframes (red tipping cue and green dampening cue) — these are meaningful game-state/feedback colors and animations, not chrome, so only their surrounding panels were restyled. `shared/info-page.css` also left untouched (shared across all 8 climate-quartet games, out of this game's scope). Full pytest suite (110 tests) green before and after.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag thaw-milestone-0N`.
- Update the milestone table Status as work happens.
