# Lexis (working title)

Seed: `planning/lexis-plan.md` (decisions section at the top, ladder in 6b). Started 2026-10-06. Not tied to a BCM assessment. Hub registration (card, thumbnail, favicon, hub lists, offline cache) is done by the main session, not in `games/lexis/`.

## One-line pitch
A sci-fi language-deduction puzzle: a message arrives as bare pulses; learn each language by watching what its signs do, then use it. Deduction first, the story is what pulls you forward.

## Story
You are the communications officer on a survey ship making first contact with new planets; each planet is one language rung (planet 1 is Pulse, a beacon on a quiet world). Original ship, crew, planets and species only: nothing from any existing franchise. The crew voices carry the story between planets and reward each decoded language.

## Stack
Python via Pyodide, engine modules with no DOM (the Signal pattern: a thin view later, `handle(json) -> json` plus `get_state()` / `load_state()` for the save widget). No build step. Glyph art is drawn by code as SVG (project rule: no generated images).

## Core constraints (do not violate without asking)
1. Every word must be DEDUCIBLE from the scenes shown before the player is asked to rely on it. `deduce.py` proves this; `tests/test_deducibility.py` runs it over every curriculum prefix. A new scene or language is not done until its prefixes pass.
2. Scenes are produced by running the real world (`world.react`), never written by hand, so what is watched cannot disagree with what the language means.
3. Guesses are free. The notebook never marks an entry; confirmation says how MANY chosen entries are right, never which.
4. A signal the language cannot say is answered in-world (a stable `reason` code and a line of world text), never an error or a generic "wrong".
5. Everything is deterministic: no random state in play or in the save. Easy to 100%; effects (pulses, shakes) get off switches. No roguelike or deck mechanics.
6. The structure must grow: more languages and districts are new data and rules on the same shapes (`lang.Language`, `Word`), not new code paths (Recommended three languages now, Large five later).

## Modules
- `lang.py`: `Word`, `Language`, number rules (the true one and the wrong ones the checker rules out).
- `pulse.py`: rung 1, the Pulse language (four-mark tokens; class mark then value; words lamp, door, open, shut, end) and the helpers that spell sentences.
- `parse.py`: marks to `Sentence`, or `SignalError(reason, text)`.
- `world.py`: the station (seven lamps and a door), `react(marks, station, language) -> Reaction`.
- `scenes.py`: the ordered Pulse curriculum, generated from the real world.
- `deduce.py`: every reading of the language (3 number rules x 5^5 word meanings), which still fit the scenes, and whether they all behave the same on every sentence the language can form.
- `notebook.py`: `Notebook` and `LexisState` (the save: notebook, scenes seen, what the player has said).
- `compound.py`, `compound_scenes.py`, `deduce_compound.py`: rung 2, the Compound language. A glyph is a root then a size (opaque letters: k water, m grain, t fire; o small, u big); the world is a tray; four scenes settle all six glyphs although two are never shown; the checker enumerates every assignment of five meanings to five letters (repeats allowed) in both slot orders.
- `glyphs.py`: the Compound language's component strokes as SVG path data (abstract on purpose; nothing resembles its meaning), plus `MARKER_PATHS` for the Bridge markers p, n, q (triangle, wave, diamond) and `all_paths()` for the view.
- `bridge.py`, `bridge_scenes.py`, `deduce_bridge.py`: rung 3, the Bridge language. Nouns are Compound glyphs, numbers are Pulse binary tokens, and three markers after a noun change meaning (p plural + a number, n negate, q ask); the world is a Stock (counts, max 7 each); five scenes settle it (checker over marker roles and slot order). A message is space-separated tokens such as `ku p 0011`.
- `story.py`: the story spine as data. `BRIEF` (ship Marigold, Captain Ines Varga who needs a yes or no, Engineer Dov Mensah who needs a number, Navigator Pell who is calm) and `BEATS`: one per planet unlocked by contact, plus a closing "Heading on" beat that unlocks with planet 3 and leaves planets 4 and 5 as faint receiver signals. `story.view(contact)` gives the brief and the unlocked beats newest first. Rules: beats never name or explain any sign (tests/test_story.py scans every line against a forbidden answer-word list), no em dashes or exclamation marks. The page's Crew log panel and button are hidden by `shared/story-toggle.js` (`data-story-selectors="#crew-log-panel, #crew-log-toggle-button"`); the mission brief opens by itself on first load (`localStorage lexis:brief-seen`).
- `report.py`: the Contact report (after planet 3 contact only): per planet what the signs meant (from the true language data), transmissions received, messages sent, notebook entries right of those written (engine truth), plus totals and achievements earned. The one place the game says which entries were right. Opens by itself on first planet-3 contact in a session; a "Contact report" button shows it again any time.
- `info.py`: the About Lexis page. Six facts, each reworded with a named source and the date read (2026-10-07; all read live that day): Binary number (Wikipedia), Chinese character classification (Wikipedia), Coding of Nominal Plurality and Negative Morphemes (Dryer, WALS Online, chapters 33 and 112), Linear B (Wikipedia), Arecibo message (Wikipedia). Facts about a planet's mechanic unlock with that planet's contact (a locked fact carries only its id) so the page never gives an answer away. No report-an-issue button (the site's version posts to the live backend). Reuses `shared/info-page.css`; ids `info-page-toggle-button` / `info-page-panel` so the opening screen's Info button works.
- `achievements.py` + `achievements.json`: twelve achievements computed from the state (nothing hidden, none luck-gated).
- `game.py`: the one entry point, `handle(json) -> json` (open, next_scene, write, confirm, speak, reset; `planet` is pulse, compound or bridge) plus `get_state()` / `load_state()` for the save widget (load merges, never replaces, never raises on garbage). Planet 3 unlocks after contact with planet 2; its contact goal is exactly five big fire on the counter AND the ask sign used at least once (`flags["asked"]`). Save version 3 (bridge notebook keyed p/n/q, scenes seen, spoken messages, contact, and the counter as `stock`); older saves load unchanged. Every view also carries `story`, `info` and `report` (all derived from contact and state, never saved). 128 tests.

## Milestones
| # | Milestone | Status |
|---|---|---|
| 1 | Engine core: language definition format, the Pulse language, parser, world, scenes, deducibility checker, notebook and save state; 47 tests, with the `handle(json)` entry point | **DONE** (2026-10-06, untagged) |
| 2 | Notebook UI, sentence builder, first scene and dialogue playable (static shell + Pyodide engine, `handle(json)`): `index.html`, `style.css`, `app.js` (glue only; a temporary localStorage save until milestone 5); 52 tests | **DONE** (2026-10-06, untagged) |
| 3 | Rung 2 data and the deducibility checker for it: the Compound language (`compound.py`, `compound_scenes.py`, `deduce_compound.py`); 70 tests. The checker allows repeated meanings (no bijection assumption), which is what makes it honest | **DONE** (2026-10-07, untagged) |
| 4 | Rung 2 in the view: component strokes drawn as SVG (`glyphs.py`), planet tabs, the tray and its scenes, a sign builder, a per-planet notebook, contact goals that unlock planet 2 (`handle` takes `planet`); 79 tests | **DONE** (2026-10-07, untagged) |
| 5 | Save widget, achievements (10, manifest + `achievements_earned`), tutorial, opening screen; hub registration deliberately MOVED to milestone 8 so a half-built game is not listed publicly; 85 tests | **DONE** (2026-10-07, untagged) |
| 6 | Rung 3: the Bridge language (plural, negation, question markers; borrows nouns from rung 2 and binary numbers from rung 1): engine (`bridge.py`, `bridge_scenes.py`, `deduce_bridge.py`), planet 3 in `game.py` (locked until planet 2 contact, notebook by marker letter, in-world errors, contact goal), marker glyph strokes, planet 3 tab and panel (counter chips, transmissions, notebook, message builder), achievements Third Contact and Small Signs; 115 tests | **DONE** (2026-10-07, untagged) |
| 7 | Story spine and ending (Crew log, mission brief, one beat per planet plus a closing beat), Contact report, About Lexis info page with six live-read sources, tutorial steps for planets 2 and 3, the Crew log and the info page; 128 tests | **DONE** (2026-10-07, untagged) |
| 8 | Polish in `games/lexis/`: accessibility pass (non-colour cues, full keyboard, focus kept across redraws, live regions, reduced motion and effects switches), light theme following the site theme, Settings panel, What's New panel and banner, Desktop boot, 320px check; 156 tests. Hub registration (card, thumbnail, favicon, hub lists, offline cache) is done by the main session | **DONE** here (2026-10-07, untagged); registration by the main session |

## Page, accessibility and Desktop boot (milestone 8)
- `index.html` is the Classic page (`<main id="game">`, a skip link, planet panels each wrapped in `.planet-cols` > two `.planet-col`). `settings.js` holds the per-device display settings (`lexis-text-scale`, `lexis-reduced-motion`, `lexis-effects`, `lexis-high-contrast`; never in the save). Reduced motion starts from the system setting until the player chooses. Theme comes from `shared/theme.js` (floating pill plus a Settings button); `style.css` is all colour variables with one light set.
- Non-colour cues: lit lamp is solid-outlined with a written "n of 7 lit", door is open (solid) or shut (double outline) with a word, the chosen planet tab is bold and underlined, earned achievements solid and "Earned", unavailable buttons dashed. Contrast of every text and outline pair is computed in `tests/test_accessibility.py`.
- Keyboard: everything is Tab-reachable. Inside a Transmit panel (`data-builder`): S short, L long (Planet 1), Backspace removes the last item, Delete clears; Left/Right/Home/End move along a row of buttons. Buttons that turn themselves off use `aria-disabled` (kept focusable); notebook rows and button rows are rebuilt only when their contents change (`fillOnce`), so focus survives every redraw. Accessible names are ordinals ("part 2", "small sign 1", "thing 3"), never the internal letters, so they cannot leak p/n/q or any number value.
- Screen readers: a hidden `#announce` live region reads each new transmission and its result; the toast reads achievements, new crew log entries and newly reachable planets.
- What's New: `changelog.json` (`{"changelog": [...]}`), the panel is built by `app.js`, which also sets `window.CHANGELOG_JSON` for `shared/whats-new-banner.js` (included after `app.js`).
- Desktop boot: `pc-config.json` (windows for crew log, report, achievements, what's new, settings, about; icons for crew log, achievements, settings; menu for tutorial, about, report, what's new), `pc.css` (two scrolling columns: world and transmissions left, notebook and Transmit right; a Contact chip), `pc.js` (`window.LEXIS_PC_TUTORIAL_STEPS`; `index.html` picks it through `window.lexisTutorialSteps`), generated `pc.html`. No change to `game.py`.
- Not done here: the site-wide account sync of text size and reduced motion needs a `lexis` entry in `shared/site-settings.js` GAME_KEYS (`lexis-text-scale`, `lexis-reduced-motion`); the theme already syncs.

## Working conventions
Commit and tag per milestone: `git commit -m "Milestone N: <name>"`, `git tag lexis-milestone-0N`. Update the Status column as work happens.

- **Oct 8 wiring (Z-20, Z-27, Y-7, Y-8, Y-29):** `mountCopyResult()` in `app.js` mounts the shared `NoyvjCopyResult` button under the Contact report (`#report-copy-result`; the report only exists after planet 3, before that the button says nothing to copy yet), with notebook entries right, planets contacted, transmissions and achievements. Achievement rows carry `data-achievement-id` / `data-achievement-label` so `shared/achievement-share.js` can add Share to earned ones. The Open Graph block and JSON-LD sit in `<head>` before the shared includes; a `#credits-link` anchor sits above the ad bar (in the Desktop Help menu via `pc-config.json`). Tests: `tests/test_wiring_oct8.py`.
