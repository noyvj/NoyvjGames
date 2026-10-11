# Zero-G Shift build status (handoff file)

Updated after every milestone. Read `planning/zero-g-shift-plan.md`, `CLAUDE.md` here, then this file. Hub registration is NOT part of this build.

## Done
- M1 Engine and solver: rules.py, solver.py, tools/gen.py + build_bays.py + texts.py, deck 1 (8 bays) with proofs; tests green.

## Next
- M2 Bay UI: play.py, render.py, game.py, index.html, app.js, style.css, settings.js, favicon, save contract.

## Open problems / notes
- Local Python is 3.9: engine code avoids 3.10+ syntax.
- To rework a deck: edit its profiles in `tools/texts.py`, run `python3 tools/build_bays.py N`, run the tests.
