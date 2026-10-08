# Heist Committee (working title)

Plan: `planning/heist-committee-plan.md`. TODO items M-1b-1 to M-1b-9. Personal project, no BCM tag. Fun first, funny, no lesson. Cozy caper tone (plan question He1 recommendation), invented crew names, Daily Job later (He2 recommendation).

## One-line pitch
Pick a target, hire five oddball specialists who do not get along, drag their actions into a timeline, then watch the job play out beat by beat while complications and personality clashes chain into each other.

## Stack
Python via Pyodide, plain HTML/CSS, no build step. `engine.py` is the heist resolver (pure function of content, crew, plan, gear and seed). Content is data in `content/*.json`, loaded by `content.py` (which also validates it). `app.js` is glue only.

## Core constraints
1. The heist is a pure function of (content, target, crew, plan, gear, seed). Same inputs, same event log, byte for byte. Every die is `roll(seed, label...)`, so editing one cell never reshuffles another.
2. No hue-only encoding: roles by shape + letter + word, outcomes by icon + word, odds as words (Solid / Risky / Long shot / No chance).
3. No timers anywhere. Planning time is unlimited; playback is a Next button (auto-advance is optional).
4. Chains are capped at 6 links a beat and every complication fires at most once a heist.
5. Fiction only: invented targets and people, nothing violent, no real brands.
6. Undo and re-plan freely before Start Heist; playback is fixed afterwards.

## Milestones
| # | Milestone | Status |
|---|-----------|--------|
| 1 | Engine core | Done |
| 2 | Plan UI | Done |
| 3 | Playback + payout | Done |
| 4 | Launch content | Done |
| 5 | Career and meta | Done |
| 6 | Standard kit | Done |
| 7 | Achievements + story | Not started |
| 8 | Balance and bots | Not started |
| 9 | Own-folder wrap-up | Not started |

## Working conventions
Commit and tag each milestone (`heist-committee-milestone-0N`). Hub registration is NOT part of this folder's milestones (TODO M-1b-11, blocked on the session that owns the hub files).
