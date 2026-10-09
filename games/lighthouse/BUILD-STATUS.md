# Lighthouse build status (handoff file)

Seed plan: `planning/lighthouse-plan.md`. TODO items M-2b-1 to M-2b-9 in `planning/TODO.md` section M.
This session owns ONLY `games/lighthouse/`. Hub registration is M-2b-10 (blocked on Noy2), not done here.
Run tests: `python3 -m pytest -q games/lighthouse`. Lint: `python3 -m flake8 --extend-ignore=E501 games/lighthouse`.
Text harness: `python3 games/lighthouse/harness.py [seed] [nights]`.

## Decisions taken (open plan questions Li1-Li3 unanswered, plan recommendations used)
- No on-screen death, ever, for anyone. Ships are delayed or damaged ("everyone aboard is safe"), never lost.
- Eerie details sub-toggle default ON, with a content note and an always-visible off switch.
- Tick pacing: one tick = 10 in-game minutes; 1x = one tick per 4 s (a night is about 3 minutes), 2x and 4x faster. The plan text said "4 ticks per second", which contradicts its own "3-5 minutes per night"; the minutes figure was kept.
- Everything random is a pure function of (seed, night, tick, label) in `rng.py`; no generator state is ever saved.
- One extra deliberate rule: the 20th night of every year is a festival (no ships, calm, no incidents), so "Nothing Happened" is never luck-gated.

## Done
- M1 Sim core (commit 8e34656, tag lighthouse-milestone-01): engine, harness, 78 tests.
- M2 Night UI: index.html, style.css, app.js, settings.js, SVG scene (sky by hour, beam, ships by silhouette, weather layers), HUD, evening plan, night controls, morning report, speed/pause via shared time-controls, favicon, changelog. Verified live at 1440x900 and 360x740, 104 tests.

- M3 Day loop + upgrades: day panel (mend, rest, tidy, tideline, greenhouse, rescue), workshop with 9 upgrades and a confirm for dear ones, supply-boat order form, seasons, barometer, three standing goals (goals.py), 111 tests.
- M4 Complete Quiet mode: year-end screen and endless continue verified live, copy-result button, welcome-back toast, abandon/reset confirms, whole-year handle test. 112 tests. FIRST COMPLETE PLAYABLE GAME.
- M5 Cast, letters, gifts: lore.py (10 sailors, 23 letters, 11 gifts), cast.py (labels ships, never changes the sim), story.py, Letters panel with sailors/gifts/room SVG, reply choices, story toggle wired, quiet runs skip it all. 137 tests. Hesper and Berit are written for in M6 (mystery characters).
- M6 The Unease: mysteries.py (6 mysteries, 35 beats, 8 small oddities), unease.py (pure year schedule with fog preference, the odd-streak rules, hidden meter), beats shown in the log/report/scene (off-chart light, phantom ferry, ghost board entry, turning chair, extra cup), notebook of odd things, Eerie details toggle (toolbar, settings, per-device), content note, dread-ledger tests over 1000 seeds. 157 tests. Mystery 1 was prototyped and checked live before the others were written.

## Next
Milestone 7: Standard kit: tutorial (shared tutorial.js steps), mobile dock/HUD (mobile-hud.js, mobile-dock.js), info panel (About the Light, sourced facts), feedback, light theme and colourblind audit, story chapters optional.

## Open problems
none yet

## Update 2026-10-09 (after the usage-limit reset)
- User answered Li1-Li3: yes to all recommendations. Li1 extra: maybe later add missing ships for dramatic effect, but NONE for now (a ship may be delayed or damaged only).
- Skimmed planning/PLAYER-PROFILE.md (private; never quoted in the game). Consequences for the design: no hard-fail, no timers, easy to 100%; a collector's notebook (logbook of ships, sailors, gifts, odd details); three standing goals visible at all times; sailors are flawed people, not all-good heroes; dark but never absurd humour; a welcome-back line on return.
- Milestone 2 files (index.html, style.css, app.js, settings.js, changelog.json, icons/) were uncommitted at the cutoff; being verified live now.
