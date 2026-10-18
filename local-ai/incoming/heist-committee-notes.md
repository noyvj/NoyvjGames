# Heist Committee: LA-8 notes (s3b, drafted 2026-10-19)

Steps are in `local-ai/incoming/heist-committee.txt` (lint: 0 problems). 4 open items labelled `[local AI: after split]`.

## A list
None.

## B list (chains)
- R4-HCPC-5 (3 steps): playback film strip, kept to what the page can do without a new engine action (the engine has only `step`, `skip` and `finish`; there is no "go back"). Step 1: a strip of beat buttons under the status line; picking one outlines that beat's lines in the log and says "Looking at beat N of M" (outline plus words, never colour alone); a new Next beat clears the pick. Step 2: keys J (previous beat), L (next beat; at the newest beat it plays the next one), K (play or pause), plus a help line in `index.html`. Step 3: a speed key F and a button (normal 2.8 s, fast 1.4 s, slow 5.6 s, not saved) and a native range input as the "draggable playhead" (a real mouse-drag gesture on a custom element would be a failure-prone task type; the slider is draggable and keyboard-operable). The browser test needs a whole planned job to reach playback; the steps tell the model to copy the click sequence of `drive()` in `tests/test_browser_smoke.py`.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-HCMO-1 one crew row at a time with swipe and bottom sheet | `[Claude: design]` | A different phone layout of the timeline (`plan.js`, `timeline-zoom.js`, `mobile-tray.js` already exist) with swipe between rows and a bottom sheet to pick an action; bottom sheets and swipes failed in earlier audits. |
| R4-HCMO-4 full-screen story cards, tap anywhere for the next beat | `[Claude: design]` | A new full-screen playback mode: the card text for each beat type, how it coexists with the log, and tap-anywhere against scrolling and accessibility are all undecided. |
| R4-HCMO-10 swipe a past job to replay it | `[Claude: design]` | The game has no list of past jobs: the view carries only the count `jobs_done`, and replay exists only as `retry` of the current job. It needs a new saved job history (new save key, engine) before there is anything to swipe. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-HCPC-5 | B | 3 |
| R4-HCMO-1 | C | 0 |
| R4-HCMO-4 | C | 0 |
| R4-HCMO-10 | C | 0 |

Totals: A 0, B 1 item (3 steps), C 3. No `index.html` size cap test exists in this game.
