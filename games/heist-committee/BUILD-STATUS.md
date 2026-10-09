# Heist Committee build status (handoff file)

Last updated: Milestone 9. ALL NINE FOLDER MILESTONES ARE DONE. Nothing half-finished.

## Done
- M1 Engine core, M2 Plan UI, M3 Playback + payout, M4 Launch content, M5 Career and meta, M6 Standard kit, M7 Achievements + story, M8 Balance and bots, M9 Own-folder wrap-up (favicon, Desktop boot with pc-config.json/pc.js/pc.css/pc.html, game CLAUDE.md, changelog).
- Tests: `cd games/heist-committee && python3 -m pytest -q tests` (about 165, about a minute; the browser smoke tests skip offline). Lint: `python3 -m flake8 --max-line-length=140 .`. Shared check: `python3 -m pytest -q shared/tests -k heist`.

## Next (not for this folder's agent)
- M-1b-11: hub registration, blocked on the session owning the hub/shared files (see CLAUDE.md "Not in this folder"). Also add `games/heist-committee/pc.html`, `pc.css`, `pc.js`, `content/*.json`, all `*.py` to the sw.js precache / offline manifest there.
- M-1b-10 Daily Job (optional, user said yes to Daily Job later): date-seeded job, archive, opt-in leaderboard.
- Dev logs for BCM114/BCM206 were not written (outside this folder's brief).

## Open problems
- None known. A skill-maximising crew can contain a trap quirk (Allergic Pip in the flower dome): intended discoverable puzzle.
