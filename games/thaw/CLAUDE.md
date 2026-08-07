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

## Tech notes

- Python/Pyodide, per root conventions.
- The feedback-loop math (melt rate feeding back into warming rate) is the trickiest logic in this set — isolate it in its own well-tested function early, since everything else in the game depends on getting this right and legible.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag thaw-milestone-0N`.
- Update the milestone table Status as work happens.
