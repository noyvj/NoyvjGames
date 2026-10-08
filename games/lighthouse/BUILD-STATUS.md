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
(updated after each milestone)

## Next
Milestone 1 commit, then Milestone 2 (Night UI).

## Open problems
none yet
