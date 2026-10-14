# Undersleep

Seed: `planning/undersleep-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Run one slightly overcommitted person's day (and, in story mode, the days of the people around them): slot work, food, friends and naps into a schedule while a gentle body clock keeps time, in a cozy home you make feel like yours.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 3 | Tracker hidden at first run? | **Pending the user's answer** (they did not understand the question). Plain version: "when someone opens the game for the first time, do they see the optional check-in feature straight away, or is it tucked away in Settings until they switch it on?" **Recommendation: hidden by default** ("Just play"). Everything below assumes hidden. | Not started |
| 4 | Tone | **Cozy and "Unpacking"-esque, not deadpan-absurd.** See "Tone" below. | Not started |
| 5 | One character or a roster | **Multiple characters**, plus a **story mode in which several characters' stories interconnect.** See "Cast and story mode" below. | Not started |
| 6 | Journal gate / framing | The answer reads as a framing instruction: **frame the game as one you add personal touches to, so a character feels like you, NOT as a journal or tracker.** (The question actually asked about a one-time "not medical advice" acknowledge gate; the answer did not address that. Recommendation for the gate: no modal gate; keep the persistent footer line. Flagged in the report as a small open point.) | Not started |
| 7 | Extra journal tags | **None.** Keep only the plan's default tags (stress, exercise, caffeine, screen-late). | Not started |
| 8 | Story mode | **Yes, built out:** the player chooses a preset that represents "them" and still plays other characters around it. | Not started |
| 1 | Circadian sim core | Curve function, meters, day step, sleep debt; text-only harness playable in tests | Not started |
| 2 | Schedule ring UI | 24-hour SVG ring, block placement (drag + keyboard), curve overlay, Run Day and debrief | Not started |
| 3 | Rhythm + entrainment | Rhythm meter, phase shift, chronotypes, multiplier feedback and visible curve change | Not started |
| 4 | Cozy events | ~40 events written in the cozy tone, soft margin-note voice, chained events, rough-day handling | Not started |
| 5 | Progression + home scene | Currencies, unlocks, home objects placed in the room scene (environment storytelling), workplaces, seasons | Not started |
| 6 | Standard kit | Save widget, `settings.js`, changelog, tutorial, mobile dock/HUD, info page, confirm dialogs, achievements v1 | Not started |
| 7 | Single-character ship | Sandbox and challenge modes, copy lint (incl. the journal/tracker ban), colorblind audit, hub integration. **First complete, playable game** | Not started |
| 8 | Roster | Schema 2 with per-character state and migration, character switching, 5 authored characters, per-character home scenes | Not started |
| 9 | Story mode | Anchor preset choice (3 presets), roles, thread engine (invitation, ripple, shared object, both sides), 4 launch threads, hand-off rules, bond values, story achievements, story toggle wiring | Not started |
| 10 | Make it you | Personal touches (name, portrait, home objects, favourites, pet, usual wake), preset customisation, "Personal Touch" achievements | Not started |
| 11 | Check-in (optional, hidden by default) | Quick check-in, backfill, default tags only, export/delete, pause, not-medical footer, mirror mode and capped Rhythm import behind toggles, separability tests. No sync | Not started |
| 12 | Polish + hub update | Thread balance, more threads, copy lint pass, colorblind and 375px audit, dev logs, tag | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag undersleep-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/undersleep/register.json`, then `scripts/register_game.py undersleep`).
