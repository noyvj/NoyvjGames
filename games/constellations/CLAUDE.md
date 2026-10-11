# Constellations (working title)

Seed: `planning/constellations-plan.md` (Quick ideas round A8, TODO QI-8). Personal project, no BCM tag. Milestones 1 to 3 built 2026-10-12 by a background agent (engine and prover, the playable chart page, seasons 1 to 3 with the Sky Atlas). NOT yet linked from the hub or registered anywhere (no `sw.js` precache, no `game-manifest.json`, no `offline-manifest.json`, no site-settings key): hub registration is the separate step QI-8-R.

## One-line pitch
A night-sky logic puzzle: numbers on stars say how many lines must touch them, and the figure that falls out is a real constellation that you then keep in your Sky Atlas.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only (it draws SVG and turns input into requests). Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code. No Node is available in this repo's tooling: check JS in the browser.
- Runs from any static server. No audio, no image files (every star, line and the atlas is drawn as SVG by the page).

## Core constraints (do not violate without asking)
1. The engine is pure and deterministic: no clock, no randomness (a test scans every engine module). Whether a figure is valid is a pure function of the chart and the lines drawn.
2. Nothing is timed, nothing can fail, nothing is lost. Lines are free to erase, undo and redo. A constellation in the atlas stays there. A wrong figure is described in words ("2 numbered stars still need more lines"), never called a failure.
3. No luck and no guessing: every chart is PROVED to have exactly one valid figure, equal to the traditional one, and to be finishable by line logic (at most one what-if step). A chart that fails is redrawn, never shipped.
4. Never colour alone: a numbered star is a badge with its number; a number that holds has a double ring and a tick, one with too many lines a dashed ring and "!"; a given line is a thick double rail; a crossed-out pair has an "x"; two crossing lines are dashed and marked with an "x"; a held star has a halo and its neighbours get dotted rings; the keyboard star has a heavy ring. Everything visual has a text version (cursor line, status line, "Chart as text").
5. Effects toggleable (star glow, the shine when a constellation is found); reduced motion honoured; light and dark theme; high contrast; text size.
6. Stars are real (HYG star database, drawn flat); figures are the traditional IAU/Stellarium ones. No generated or downloaded images.
7. A chart's name, its stars' names and its note stay out of the view until the chart is finished (a test checks); unfinished atlas places show only a dashed ring.

## The rules (`sky.py`)
- A chart is a set of stars at integer positions on a 1000-wide canvas, a list of CANDIDATE lines (the traditional figure plus each star's three nearest neighbours, minus any line that would run closer than 20 units to a third star), and clues: a number on a star (that many lines touch it; 0 means outside), MUST lines (already drawn, cannot be removed), NEVER lines (crossed-out pairs).
- Valid figure: every number holds exactly, no two lines cross, touch or run along each other (exact integer geometry, `edges_conflict`), no never-line is drawn, and all the lines form ONE connected figure. A star without a number may have any number of lines, including none. Given lines count as drawn.
- `analyse(chart, lines)` returns degree per star, over/under, crossing pairs, never-lines used, number of pieces, `valid`.

## How correctness is PROVED (`sky.py`, `tools/`, `tests/test_charts.py`)
- `solutions(chart, limit)`: the exhaustive solver (depth-first over the lines, pruned by the numbers and crossings, connectivity judged on each candidate). `count_by_stars(chart, limit)`: a second counter that shares no search code with it (star by star, line-against-line crossing tests, judged by `analyse`); the tests cross-check the two against brute force on small charts.
- Every chart: exactly one valid figure (both counters) and it equals the stored traditional figure; EVERY clue is needed (take any one number, given line or crossed-out pair away and a second figure appears); line logic finishes it (`logic` 1 = plain line logic, 2 = needs one what-if step). `propagate(chart, lookahead)` is the line logic a person can follow: `full` (a star has all its lines: the rest are out), `forced` (a star needs every line still open at it), `cross` (a line that would cross a drawn one is out), `close` (a line that would finish a piece while numbered stars remain outside it is out), `bridge` (the only way to join stars the figure must reach is in), and with lookahead one "what if I draw it" step. A test checks it never contradicts the figure. Milestone 4's hint ladder reads this.
- Geometry tests: whole-number positions inside the canvas, no two stars closer than 66 units, the figure connected, planar, every star on it; data tests: every star has a Hipparcos id, name and magnitude matching the snapshot; a few facts (brightest star of famous constellations, Orion's belt in a row, east on the left).

## Data pipeline (dev tools, never run by the game)
- `tools/fetch_snapshot.py` reads the HYG star database v4.1 and the Stellarium "modern" sky culture (IAU figures as Hipparcos chains) and freezes the 238 stars and 24 figures used into `data/snapshot.json` (dated 2026-10-12).
- `tools/chart_specs.py` holds the hand-written side: which constellations go in which season, the card note, the stars to drop or the `cap` that trims long figures (Orion drops its faintest outlying shield and club stars; Ursa Major, Gemini and Canis Major are trimmed to 14, 12 and 12 stars).
- `tools/figures.py`: gnomonic projection about the figure's centre (east on the left), scaled onto the canvas, then `spread` pushes stars apart so none is closer than 68 units or sits within 34 units of a figure line it does not belong to (the chart is a drawing, not a survey), candidate lines, and `derive_clues` / `best_clues`: start with a number on every star, add must/never lines only if needed, then take clues away one at a time while the figure stays the only one; several removal orders are tried and the set that line logic finishes with the least reasoning and the most numbers wins.
- `tools/build_charts.py` writes `charts_s1.py`, `charts_s2.py`, `charts_s3.py` (GENERATED, do not edit) and refuses to write a chart that is not uniquely, logically solvable. A test rebuilds three charts and compares.
Adding a season: add it to `chart_specs.SEASONS`, run `tools/fetch_snapshot.py` (needs the two source files or the network), then `tools/build_charts.py`, add the new `charts_sN.py` to `charts._MODULES` and to `ENGINE_MODULES` in `app.js` (a test checks the list), then the tests.

## Content (milestone 3: three of five seasons)
Winter Sky (Auriga, Columba, Monoceros, Canis Major, Gemini, Taurus, Lepus, Orion), Spring Sky (Corvus, Cancer, Ursa Minor, Crater, Leo, Boötes, Virgo, Ursa Major), Summer Sky (Lyra, Delphinus, Sagitta, Corona Borealis, Ophiuchus, Aquila, Cygnus, Scorpius): 24 charts of 5 to 14 stars, each season ordered small to big. Each chart carries the traditional name, meaning, a short note written for the game, the brightest star, "best seen" month (the month it stands highest at 9 pm for northern middle latitudes, from its right ascension) and the atlas position. Still to come (milestone 4): Autumn Sky and Southern Sky (16 more charts, 40 in all; Crux needs a figure of its own because the traditional Southern Cross is two crossing lines).

## Gating
Season 0 is open from the start; season n+1 opens when `OPEN_AT` (5) charts of season n are done (any five); inside a season every chart is open in any order. Derived from the finished set, so it only ever goes up. A save is judged in season order on load, so a hand-edited save cannot skip ahead.

## Engine and page notes
- `game.handle` returns the whole view. Actions: `open`, `pick {chart}`, `next` (next open unfinished chart), `toggle {a, b}` (draw the line between stars a and b, or erase it; one call = one undo step; refuses a pair that is not allowed, a given line or a crossed-out pair, with a message and no count), `undo`, `redo`, `clear` (erase all my lines on the chart, one undo step), `finish` (only when valid), `reset`. Stars are lettered A, B, C ... from left to right.
- Save (`get_state`, only non-default keys besides `schema`): `cur`, `solved {id: line changes}`, `work {id: ["3-7", ...]}` (unfinished chart's drawn lines; given lines are never written), `moves`, `tally {draws, erases}`. Undo history is not saved. `load` checks every field alone, drops charts in closed seasons, keeps only real allowed lines that are not given or crossed-out, and finishes a saved figure that is already complete. A `schema` key (1) is always written; a bad or newer schema gives a fresh game.
- Stats strip: Constellations (x/24), Stars joined (stars in finished figures), Atlas pages (seasons open), Seasons done, Lines drawn (the tally counts lines drawn and erased).
- Page: SVG board drawn by `app.js` (`drawBoard`): stars sized by magnitude, a badge with the number on numbered stars, lines, given lines, never pairs, ghost lines to a held star's neighbours, crossing marks. Input: drag from a star to another (a rubber band follows), or tap one star then another (the second stays held, so a tap chain draws a path), tap a line you drew to erase it, keyboard (arrows move to the nearest star in that direction, Enter/Space picks up a star and on a second star draws or erases and carries on from it, Esc puts it down, a letter key jumps to that star, Home/End, Ctrl/Cmd+Z undo, with Shift redo). A press counts as on a star within 54 units. The board is a square-ish SVG that scales with the width (down to 360 px; the 14-star charts are the tightest at about 24 px between stars on a phone).
- Charts panel (`#charts-panel`): each season with found/total, locked seasons say how many more to finish, a found chart shows its name, an unfound one only "Chart n" and its star count. Sky Atlas (`#atlas-panel`): equirectangular, 4 units per degree, right ascension runs right to left, a finished figure is drawn at its real place with its name, an unfound chart is a small dashed ring labelled "Winter 3"; click or Enter opens the card (finished) or goes to the chart (open season). Cards (`<details>`): season, stars, brightest star, best month, line changes, the note, sources with the read date.
- Settings: star letters (on), star names on finished charts (off), text size, reduce motion, effects, high contrast, theme, reset display, start the atlas over (confirm dialog). About: pledge, how it works, three reworded facts with the Wikipedia source and read date 2026-10-12, plus a live read of the Wikipedia summary of "IAU designated constellations" when About is opened (with a stated fallback). What's New (`changelog.json`), `sources.json` for the hub's sources page.
- Engine modules (loaded in this order by `app.js`): sky, charts_s1..s3, charts, info, then game. A test checks the list.

## Not built yet
Opening screen, tutorial, keyboard-help overlay, difficulty, goals strip, hint ladder, live data read, achievements, Desktop boot (`pc.html`), `layout-pref.js`: see the milestone table.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine and prover | Star data, edge validator, crossing test, uniqueness solver, season 1 (8 charts) with proofs | Done |
| 2 | Chart UI | SVG sky, drag lines, pointer and keyboard, done card, save contract. Playable slice | Done |
| 3 | Seasons 2-3 | 16 more charts, Sky Atlas panel and cards, season gating | Done |
| 4 | Seasons 4-5, hints, goals | 16 more charts (40), southern sky, hint ladder, three-goals strip, live data. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |
| R | Register in the hub | Same steps as the earlier new games (TODO QI-8-R) | Not started |
