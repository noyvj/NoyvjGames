# Pocket Bazaar build status (handoff file)

Updated after every milestone. Owner of this folder: the Noyvj build agent. Hub registration (M-4b-10) and the
Daily Market (M-4b-9) are NOT part of this build.

## Done
- M1 Board engine: goods.py, rng.py, board.py, textplay.py, 38 tests, flake8 clean (commit e340787, tag pocket-bazaar-milestone-01)

- M2 Board UI: game.py (practice counter), index.html, app.js, style.css, settings.js, favicon placeholder; 84 tests; checked at 1440x900 and 360x740 (crates + Sell/Broom visible without scrolling at 360x740)

## Next
- Milestone 3: customers and orders (orders.py, queue UI, patience in beats, delivery, 4 archetypes, reachability test). Mobile dock decision: customers add height, so consider shared/mobile-dock.js for the tools row

## Open problems / notes
- Local Python is 3.9 (Pyodide runs 3.12): engine code avoids 3.10+ syntax.
- flake8 command: `python3 -m flake8 games/pocket-bazaar --extend-ignore=E501`
- The plan's "5-link cascade" is impossible with 5 tiers (the longest chain is 4 merges: T1+T1, T2, T3, T4), so
  the Chain Master achievement and the perf test use 4.
