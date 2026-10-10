# Stranded build status (handoff file)

Updated after every milestone. Read `planning/stranded-plan.md`, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine and the whole story: kit.py (S/C builders and the text shorthands), walker.py (pure deterministic stepper, state = scene + three stats + flags, replayed from a string of choice numbers), explore.py (search over every reachable state with dominance pruning, route_to, loose_end, peek), lore.py (days, narrator, 29 collectables), story_1..4.py (59 scenes, 12 days, 9 endings), game.py (handle/get_state/load_state, validated save), info.py, achievements.py, render.py (SVG strings). 48 tests (graph reachability, walker determinism, exact rewind, save validation, pledge lint); flake8 clean.

## Next
- M2 Comms UI: index.html, style.css, app.js, settings.js, icons/favicon-stranded.svg, changelog.json (app.js ENGINE_MODULES must list every engine module: kit, story_1..4, story, walker, explore, lore, info, achievements, render, game last).

## Open problems / notes
- Local Python is 3.9: no match statements, no `X | Y` types.
- Edges are (scene, choice, target) triples: a reply with a conditional route has one edge per target, so "paths walked" and the loose-end finder cover conditional variants. Tests prove every edge reachable.
- Favicon lives in games/stranded/icons/ (the hub's root icons/ folder is not ours).
