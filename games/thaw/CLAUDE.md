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

## Tech notes

- Python/Pyodide, per root conventions.
- The feedback-loop math (melt rate feeding back into warming rate) is the trickiest logic in this set — isolate it in its own well-tested function early, since everything else in the game depends on getting this right and legible.
- Space-theme visual pass (Sep 2026): adopted the site-wide starfield/nebula background (`shared/space-bg.css`) and SOL's glass-panel language — `#game`, `.section`, `.region-card`, `.context-blurb` moved from flat solid backgrounds to translucent gradient + backdrop-blur + violet-tinted borders; `button.secondary`/`button.primary` moved from flat fills to two-stop gradients with a glossy inset highlight and an added `:hover` brighten (on top of the existing `:active` darken); `.meter-fill--temperature` gained a matching glow via `box-shadow` only. `game.py` was not touched — CSS/HTML only. Deliberately left alone: `.melt-status--active`'s red, `.mini-temp-line`'s stroke color, and both the `tipping-point-flash`/`intervention-flash` keyframes (red tipping cue and green dampening cue) — these are meaningful game-state/feedback colors and animations, not chrome, so only their surrounding panels were restyled. `shared/info-page.css` also left untouched (shared across all 8 climate-quartet games, out of this game's scope). Full pytest suite (110 tests) green before and after.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag thaw-milestone-0N`.
- Update the milestone table Status as work happens.
