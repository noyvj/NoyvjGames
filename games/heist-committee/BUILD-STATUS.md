# Heist Committee build status (handoff file)

Last updated: Milestone 5. The user answered He1-He3: yes to all recommendations (cozy caper tone, Daily Job later, invented crew names). planning/PLAYER-PROFILE.md read: no hard-lose states, no timers, predictable and retry-friendly, optional leaderboards, dark/moody look, three visible goals, short wins.

## Done
- M1 Engine core. M2 Plan UI.
- M3 Playback + payout: game.py start_heist/step/skip/finish/retry, writeup.py + content/writeups.json, play.js (beat-by-beat log with why-lines, optional auto-advance, payout screen with chain diagram, retry pays only the improvement). Verified live at 1440 and 360.

- M4 Launch content: 3 targets (Pigeon Museum, Affineur's Cellar, Lucky Barge), 25 complications, 12 crew, 3 gear, board shows all three, tests that every complication can fire. First complete playable game.

- M5 Career and meta: reputation (gain only for improvements), unlocks by reputation (jobs, crew, gear), board of up to 3 rotating by career seed, friends/feud relationships from pair scores, hat-passing safety net, 5 targets, 20 crew, 56 complications, 7 gear.

## Next
- M6 Standard kit: save widget check, confirm dialogs (done for start/abandon/clear/new career), tutorial, mobile dock/HUD, keyboard-shortcuts help, info panel (info.py), changelog.json, story toggle, opening screen, copy-result.

## Open problems
- Mobile dock for the tray is wired in M6.
