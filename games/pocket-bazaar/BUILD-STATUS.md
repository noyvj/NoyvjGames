# Pocket Bazaar build status (handoff file)

Updated after every milestone. Owner of this folder: the Noyvj build agent. Hub registration (M-4b-10) and the
Daily Market (M-4b-9) are NOT part of this build.

## Done
- M1 Board engine: goods.py, rng.py, board.py, textplay.py, 38 tests, flake8 clean (commit e340787, tag pocket-bazaar-milestone-01)

- M2 Board UI: game.py (practice counter), index.html, app.js, style.css, settings.js, favicon placeholder; 84 tests; checked at 1440x900 and 360x740 (crates + Sell/Broom visible without scrolling at 360x740)

- M3 Customers and orders: orders.py, days.py, day.py, game.py rewritten around a Day, queue UI, closed/summary card; 141 tests incl. a greedy bot fairness test; checked at 360x740 (everything incl. crates fits without scrolling) and desktop

- M4 Market day loop: festival.py, shop.py, day start/summary cards, shop UI, campaign line, 160 tests; first complete playable game. Days tuned so a greedy bot loses about one customer a day from day 6

- M5 Combos, streaks, festivals: renown.py, combo x1-x3 + pips, chain bonus, wildcards, 6 festivals, child/tourist/crowd archetypes, renown unlocks (spices, sweets), personal-best lines; 189 tests; checked at 360x740 with 5 crates

## Next
- Milestone 6: standard kit + pledge tests: confirm dialog (reset, sell T4/T5), tutorial, opening screen, save widget, keyboard shortcuts help, changelog + What's New banner, about/info panel with the pledge list, mobile dock/HUD decision (not needed so far: everything fits at 360x740), pledge tests (no clock, no banned words, no timestamps in save)
- Player-profile notes (private): keep objectives visible without a strict order (a 'goals' list in M7), no tutorial wall, friendly welcome back, leaderboards optional (none here)

## Open problems / notes
- Local Python is 3.9 (Pyodide runs 3.12): engine code avoids 3.10+ syntax.
- flake8 command: `python3 -m flake8 games/pocket-bazaar --extend-ignore=E501`
- The plan's "5-link cascade" is impossible with 5 tiers (the longest chain is 4 merges: T1+T1, T2, T3, T4), so
  the Chain Master achievement and the perf test use 4.
