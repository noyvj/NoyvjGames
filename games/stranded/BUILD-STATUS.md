# Stranded build status (handoff file)

Updated after every milestone. Read `planning/stranded-plan.md`, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine and the whole story: kit.py (S/C builders and the text shorthands), walker.py (pure deterministic stepper, state = scene + three stats + flags, replayed from a string of choice numbers), explore.py (search over every reachable state with dominance pruning, route_to, loose_end, peek), lore.py (days, narrator, 29 collectables), story_1..4.py (59 scenes, 12 days, 9 endings), game.py (handle/get_state/load_state, validated save), info.py, achievements.py, render.py (SVG strings). 48 tests (graph reachability, walker determinism, exact rewind, save validation, pledge lint); flake8 clean.

- M2 Comms UI: index.html (full shared includes in the standard order), style.css (dark and light themes), app.js (chat, stats, choices, ending card, rewind buttons, one-message-per-tap setting, keyboard 1 to 4), settings.js, icons/favicon-stranded.svg, changelog.json. 68 tests incl. shell and accessibility; checked live at 1440x900 and 360x740 (choose, rewind, tap mode, no horizontal scroll); `shared/tests -k stranded` passes.

- M3 Branch map and what-if: Branch map panel (overview svg, endings list, per-day list with Go there, Show me a loose end), What if button and rows, engine `loose` action. 71 tests; checked live.

- M4 Archive, goals, hint ladder: Archive panel (three sections, hint where to look), three-goals strip, hint box (nudge, hint, answer, take me there), Tally details. First complete game. 73 tests; checked live.

- M5 Standard kit: Tutorial (9 steps, Tutorial button), About (fiction notice, pledge, how it works, two sourced facts dated 2026-10-10), What's New panel, keyboard help and Esc through the shared helper, confirm dialog on reset, light theme checked. 76 tests; checked live (tutorial, About, light theme).

- M7 Desktop boot: pc-config.json, pc.css, pc.js (8-step Desktop tutorial), generated pc.html, desktop tests, CLAUDE.md for the game. 91 tests; `scripts/generate-pc-pages.py --check` and `shared/tests -k stranded` (13) pass; checked live at 1440x900 (pc.html) and 360x740 (classic, no horizontal scroll with the map or achievements open).

## Next
- Nothing in this folder. Hub registration is the hub session's job (title card, sw.js, offline-manifest, game-*.json, site-settings key map, share cards, root CLAUDE.md row; the favicon may be copied to the hub's icons/ if the hub wants one there). The plan's last section lists questions for the owner.

## Open problems / notes
- Local Python is 3.9: no match statements, no `X | Y` types.
- Edges are (scene, choice, target) triples: a reply with a conditional route has one edge per target, so "paths walked" and the loose-end finder cover conditional variants. Tests prove every edge reachable.
- Favicon lives in games/stranded/icons/ (the hub's root icons/ folder is not ours).
- AN-7/8/9/10 (2026-10-11): tap default, Harbour's quick-reassurance flaw, tenth ending Left in the Window, narrator day-note off by default; 93 tests. Not yet done elsewhere: AN-11 (Signal streak) was NOT started.
