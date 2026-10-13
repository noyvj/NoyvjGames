# Radio Decode

Seed: `planning/radio-decode-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (A11), owner-approved: "decode binary, hex and simple ciphers from a drifting signal, each message a short log entry." Checked against `PLAYER-PROFILE.md`: computers and coding as interests, a radio-signal story sketch, quiet tragic-but-gentle characters, notebook-style collecting, short wins forming a story, a hint ladder, working things out themselves, no timers, nothing lost. Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Codecs and checks | Encoders and decoders, noise function, band data, band 1 (10 messages) with round-trip and uniqueness tests | Not started |
| 2 | Receiver UI | Dial, scope, decoder bench, helper tools, Logbook entry, save contract. Playable slice | Not started |
| 3 | Bands 2-3 | 20 more messages, Morse, shift wheel, Atbash, Toolkit shelf | Not started |
| 4 | Bands 4-5, hints, goals | 20 more (50), rail, reverse, two-step, keyword ciphers, hint ladder, three-goals strip. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag radio-decode-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/radio-decode/register.json`, then `scripts/register_game.py radio-decode`).
