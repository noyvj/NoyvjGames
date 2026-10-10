# Stranded build status (handoff file)

Updated after every milestone. Read `planning/stranded-plan.md`, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine and the whole story: kit.py (S/C builders and the text shorthands), walker.py (pure deterministic stepper, state = scene + three stats + flags, replayed from a string of choice numbers), explore.py (search over every reachable state with dominance pruning, route_to, loose_end, peek), lore.py (days, narrator, 29 collectables), story_1..4.py (59 scenes, 12 days, 9 endings), game.py (handle/get_state/load_state, validated save), info.py, achievements.py, render.py (SVG strings). 48 tests (graph reachability, walker determinism, exact rewind, save validation, pledge lint); flake8 clean.

- M2 Comms UI: index.html (full shared includes in the standard order), style.css (dark and light themes), app.js (chat, stats, choices, ending card, rewind buttons, one-message-per-tap setting, keyboard 1 to 4), settings.js, icons/favicon-stranded.svg, changelog.json. 68 tests incl. shell and accessibility; checked live at 1440x900 and 360x740 (choose, rewind, tap mode, no horizontal scroll); `shared/tests -k stranded` passes.

- M3 Branch map and what-if: Branch map panel (overview svg, endings list, per-day list with Go there, Show me a loose end), What if button and rows, engine `loose` action. 71 tests; checked live.

## Next
- M4 Archive, goals, hint ladder: Archive panel (logs, items, recordings), three goals strip, hint ladder box (nudge, hint, answer + button), tally details; achievements panel is M6.

## Open problems / notes
- Local Python is 3.9: no match statements, no `X | Y` types.
- Edges are (scene, choice, target) triples: a reply with a conditional route has one edge per target, so "paths walked" and the loose-end finder cover conditional variants. Tests prove every edge reachable.
- Favicon lives in games/stranded/icons/ (the hub's root icons/ folder is not ours).
