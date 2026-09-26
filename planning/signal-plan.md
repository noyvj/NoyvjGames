# Signal — Groundwork Plan (round-2 M3)

Status: PLAN ONLY. No `games/signal/` folder exists yet. Once approved, this becomes the seed for `games/signal/CLAUDE.md` (per `game-template.md`).
User answer (round 2, M3): "may as well try it, it seems very simple but that can be good." Taste rule (M answers): fun over teaching. Nothing here teaches anything.

**Shared baseline:** `overclock-plan.md` section 4 (full checklist) and section 5 (hub integration) apply with slug `signal`; the "Shared infrastructure checklist" below lists what is specific to this game.

## Decisions (2026-09-27, from Round 3 answers)
Source: `IMPROVEMENT-IDEAS-ROUND-3.md` Part 4, section P. Where these contradict text further down, this section wins and the affected text below has been revised to match.

| # | Question | Decision |
|---|----------|----------|
| 1 | Plain JS or Pyodide | **Pyodide, decided by me** (the user wants Python "as much as physically possible" and declined to make the call). See "Stack decision" below. The old plain-JS exception and JS/Python parity tests are dropped. |
| 2 | Theme | **Retro radio-room**, confirmed. |
| 3 | Daily reset | **UTC daily reset, plus an archive** of every past puzzle so people can play the backlog. |
| 4 | Endless practice | **Yes:** a non-daily endless practice mode. |
| 5 | Launch date | **Not tied to a special day.** Puzzle #1 is whatever UTC day the game first ships. |
| 6 | Mechanic | **Option A, "Triangulate"**, kept. **Add some modes with a bigger board.** Option B (Tuner) is not prototyped. |

### Stack decision: Pyodide with an instant static shell and a lazily loaded engine
- **What ships:** `index.html` is a static shell (header, empty grid of buttons, stats block, share button, all styled and readable with no script beyond a few dozen lines of DOM glue). Pyodide and `game.py` load after first paint (started on `DOMContentLoaded`, and also kicked off early on the first pointer or key event). All rules live in Python: generator, solver, scoring, streak recompute, save merge, share text. JavaScript is glue only (render, events, the loader) and contains zero game rules.
- **What is instant:** first paint of the page, the saved-state view (a returning player's board, readings and stats render from the saved JSON without the engine), the archive calendar, and settings.
- **What waits:** the first ping of a session on a cold start needs the generator, so it waits for the engine. Taps made before the engine is ready are queued and applied once it loads, with a plain "Receiver warming up..." line, never a blocked or dead UI.
- **Offline:** Pyodide comes from the same CDN as the other games, and `sw.js` serves cross-origin requests cache-first, so after one visit it starts fast and works offline. Verify at Milestone 2 that the Pyodide files really are cached.
- **The trade-off, stated honestly:** the original plan chose plain JS because a daily puzzle should open instantly and Pyodide's load is larger than the whole game. That is still true for the first ping on a cold cache. The shell removes the "blank page while loading" problem but not the wait. I have not measured the cold and warm start times for this game; Milestone 2 must record first paint and time to first ping on cold and warm cache in the dev log. **Reopen this decision** (fall back to the original JS port plus parity fixtures) only if warm-cache time to first ping is worse than about 3 seconds on a mid-range phone, or the user says the cold wait is unacceptable.
- **What we gain:** one implementation instead of two, no parity-drift risk, the solver and generator can be as capable as needed (bigger boards need a real search, see below), and the game stays consistent with the site and the user's preference.
- **What we lose:** a few seconds of warm-up on the first ping of a cold session, and Python speed limits on the generator (no threads, single-threaded interpreter in the browser tab). Bigger boards therefore have a generation budget that must be measured.

### Daily, archive and practice
- **UTC daily:** puzzle for date D and mode M is a pure function of `(D, M)` as before. Puzzle number = days since the launch date + 1, where the launch date (`EPOCH`) is a constant set in the release commit (not the old 2026-10-01 placeholder) and never changed afterwards.
- **Archive:** any date from `EPOCH` up to today's UTC date is playable (dates after today are refused by the shell and the engine; a tampered clock is accepted risk, same as streaks). The archive screen is a month calendar with per-day, per-mode status ticks (not played / in progress / won / lost). Archive results are recorded in a separate bucket and **never touch the streak**: a puzzle counts as a daily only if its first ping happens on its own UTC date. The archive is free to generate on demand because puzzles are pure functions of the date.
- **Endless practice (non-daily):** a "New puzzle" button generates a puzzle from a fresh random seed shown as a short code (`P-xxxxxx`) that can be re-entered or shared. Player picks a preset (Easy, Hard, or one of the big boards) or sets size, transmitter count and ping budget within limits. Practice results go to their own stats bucket; no streak, no share text with a puzzle number (it says "practice").
- **Bigger boards:** launch presets: **Classic** 9x9 (Easy: 2 transmitters, Hard: 4), **Wide** 13x13 with 4 transmitters, **Big Sky** 15x15 with 5. The signal radius grows with the board (about 4 on 9x9, 5 on 13x13, 6 on 15x15, tuned by the solver, not fixed here) and ping budgets are set from each preset's measured par. The bigger boards start as practice-only; each becomes a daily mode only once its generation time fits the budget below.

### Solver and generator consequences
- **Correction to the original text:** the daily-seed section below said the solver enumerates `C(49,3)` candidate sets. A 9x9 grid has 81 cells, so the count is `C(81,3)` = 85,320 (Easy uses 2 transmitters, far fewer) and Hard's 4 transmitters is `C(81,4)` = 1,663,740, before the spacing and edge rules cut it down. The tested range is still fine for Pyodide but is no longer trivial.
- The big boards cannot be brute-forced (`C(225,5)` is in the billions). The solver must be a constraint search: rule out every cell a zero reading excludes, bound each cell's possible contribution by the readings, and branch on the most constrained ping. Milestone 1 must produce timings for every preset and set generation and uniqueness budgets (proposed: daily generation well under a second on a mid-range phone; anything slower stays practice-only). I have not measured this yet.
- Because generation runs in the player's tab, the archive calendar must not generate puzzles just to draw ticks; it reads results from saved state only.

### Data model additions
```
days:     key "YYYY-MM-DD:mode" (was "YYYY-MM-DD"; a player can play both modes on the same day)
          value adds "kind": "daily" | "archive"
archive_stats / practice_stats: same shape as stats.<mode>, separate buckets, never feed streaks
practice: {"code": "P-xxxxxx", "preset": "...", "state": {...}} | null
settings adds: "last_preset"
```
Streak recompute (from `days` where `kind == "daily"` only) and the union merge rule are unchanged apart from the key change.

### Tests changed
- Dropped: the JS generator and the 365-date Python-versus-JS parity fixtures.
- Kept and repurposed: a **frozen fixture** of 365 dates x modes generated by the Python generator and committed as JSON. A test asserts the generator still reproduces it exactly, so an accidental change cannot silently alter past daily puzzles; any intentional change bumps the seed version to `v2`.
- Added: per-preset generation-time ceilings, archive rules (no future dates, no streak effect), practice code round-trip, queued-tap replay (taps before the engine is ready produce the same state as taps after).

## One-line pitch
A five-minute daily deduction puzzle: hidden transmitters are broadcasting on a small grid, you can only "listen" at a few spots, and you have to work out where they are from the summed signal strengths.

## Mechanic options (pick one)

**Option A — "Triangulate" (RECOMMENDED).** 9x9 grid, 3 hidden transmitters. Each turn you drop a receiver on a cell and get one number: the *sum* of every transmitter's signal at that cell (signal = max(0, 4 - manhattan distance), so 0-12 total). You get 8 pings, then must commit the exact positions of all transmitters. Why it's distinct: Wordle is symbolic feedback on a word, Mastermind is peg counts on a code, Minesweeper is neighbour counts on a fixed board. Here the feedback is an *analog sum over overlapping fields*, so a reading of 5 could be one close transmitter or three far ones. The fun is the "aha" when two readings clip together. Simple to build, hard to clone by accident.

**Option B — "Tuner".** A hidden waveform built from 2-3 sine components; you set frequency/amplitude sliders and see your wave overlaid on a faded target's *envelope only*. Feels great (radio-dial tactility) but sliders are poor for keyboard/colour-blind play, scoring is fuzzy (how close is "solved"?), and share-text is awkward.

**Option C — "Relay Chain".** Rotate/place relay pieces to route a signal from A to B through a daily obstacle field. Easy to generate, but reads as a pipes/Flow-Free clone.

**Recommendation: A.** Deterministic, exact-answer (clean win/lose, clean share text), pure logic in Python with a real solver we can unit-test, and the hard mode is just a parameter change.

## Concept
Every UTC day the whole world gets the same board. You have a "listening budget" of pings. The result strip (see Share text) tells friends how efficiently you cracked it without revealing where anything was. Streaks, a stats screen, and an archive of your past days live locally; the hub save system can carry them across devices.

Flavour: retro radio-room / signals-intelligence. Terse, dry humour in the status line ("Static. Someone is out there.").

## Stack
- **REVISED (2026-09-27): default Pyodide Python, no exception.** Static HTML shell for instant first paint, engine (`game.py`: generator, solver, scoring, streaks, merge, share text) loaded lazily after first paint. JS is glue only. See "Stack decision" in the Decisions section above. (The earlier plain-JS exception and the JS/Python parity tests are dropped.)
- Plain HTML/CSS, no build step, local `python -m http.server`.

## Core constraints (do not violate without asking)
1. Puzzle is a **pure function of the UTC date string** (`YYYY-MM-DD`). No backend, no fetch, works offline.
2. No timers in play (per user's note that time-based things are unreliable in this loader). Only the daily rollover check on load/visibility change reads the clock.
3. **Never colour-only feedback.** Every reading shows a number AND a bar-height glyph AND a fill pattern.
4. One puzzle per day counts for the streak; archive/practice puzzles never touch the streak.
5. Share text contains no positions, no numbers per cell, nothing that helps a friend who hasn't played.
6. Fully keyboard playable and thumb-playable at 360px wide.
7. No accounts required. Signing in only adds cross-device sync.

## Daily-seed design
```
seed  = fnv1a32("signal:v1:" + utcDateString + ":" + mode)     // mode = easy|hard
rng   = mulberry32(seed)
place transmitters by rejection sampling on rng:
  - min manhattan spacing 3 between transmitters (no stacking)
  - none on the outer ring (keeps readings informative)
accept only if the puzzle is *solvable*: a solver over the candidate sets
(C(81,k) on 9x9 by brute force, a pruned constraint search on the bigger
boards, see Decisions), given a fixed reference ping sequence of 8 cells
(chosen by the same rng), leaves exactly 1 consistent set.
```
- Version string `v1` in the seed lets us fix generator bugs later without silently changing past days' puzzles (past days are frozen by version).
- UTC (not local) so everyone shares a puzzle number; the UI shows "next puzzle in HH:MM" computed only on render.
- Puzzle number = days since `EPOCH` + 1, where `EPOCH` is the actual UTC launch date, fixed in the release commit (not tied to any special day; the old 2026-10-01 placeholder is void).
- Easy: 9x9, 2 transmitters, 10 pings, live "possible cells" shading toggle. Hard: 9x9, 4 transmitters, 8 pings, no shading assist, min spacing 2.

## Data model / state shape
`get_state()` (Python; this is what the save widget stores; the `days` key format and the `kind` field changed, see Decisions):
```json
{
  "schema": 1,
  "stats": {
    "easy": {"played": 0, "won": 0, "streak": 0, "best_streak": 0, "last_played_utc": null, "pings_hist": [0,0,0,0,0,0,0,0,0,0]},
    "hard": {"...same...": 0}
  },
  "days": { "2026-10-01": {"mode": "easy", "pings": [[r,c,reading],...], "guess": [[r,c],...], "result": "won|lost|inprogress", "pings_used": 6} },
  "settings": {"mode": "easy", "high_contrast": false, "reduce_motion": false, "text_scale": 1, "assist_shading": true},
  "achievements_earned": {},
  "onboarding_seen": false
}
```
- `days` is capped to the most recent 400 entries on save (size guard for the save code).
- Merge rule for cross-device sync (last-write-wins is bad for streaks): on load, union `days` by date (prefer entry with a result over `inprogress`), then *recompute* streaks from `days`. Streaks are derived data, never trusted from the blob.

## Content needs
- **No word lists.** All content is generated. Who writes what:
  - Generator + solver (Python): Claude.
  - Flavour strings (win/lose/near-miss lines, ~40 of them, per-mode): Claude drafts, user vetoes tone.
  - Archive: any past date from launch is playable (recorded separately, never affects the streak), generated on demand. Endless practice puzzles use random seeds.
- Optional later: hand-authored "featured" puzzles for holidays (fixed override table keyed by date), zero extra infrastructure.

## UI sketch (words)
- Header strip: puzzle #, mode toggle (Easy/Hard), pings left as filled dots, streak flame count.
- Centre: 9x9 grid of large square tap targets. Empty cell = plain dark tile. A pinged cell shows the reading as a big numeral plus a small bar glyph in the corner and a fill height (bottom-up) so 12 vs 3 reads without colour. Cells are also given row/column labels A-I / 1-9 for screen readers and keyboard ("press D4").
- Below the grid: a "waterfall" column listing readings in order pinged (a scrolling strip of bar glyphs) so patterns are easy to eyeball.
- "Mark" tool: toggle to stamp cells as "suspected transmitter" (a diamond icon). Commit button enables when marks == transmitter count.
- End screen: reveal board (transmitters as pulsing rings, disabled under reduce motion), result strip, Share button (copies text), stats/histogram, "next puzzle in".
- Keyboard: arrows move cursor, Enter pings, M marks, Enter on Commit submits, `?` help, Esc closes panels.

## Share text (no spoilers)
```
Signal #37 hard  5/8 ⚡
▁▃▅▇▅ ✔
```
Glyph strip = the bar-height of each reading in order pinged (8 levels quantised from 0-12), final glyph = result. Reveals effort and rhythm, not positions or cell values. Plain text with a fallback ASCII form (`.:+#`) toggle for platforms that mangle block glyphs.

## Shared infrastructure checklist
| Module / convention | Applies? | Note |
|---|---|---|
| `shared/save-widget.js` | Yes | Standard integration; `getState/loadState` as above with the merge rule |
| `shared/hub-auth.js` | Yes (via save widget) | Sync is optional |
| `shared/confirm-dialog.js` | Yes | Confirm before "Commit answer" and before clearing stats |
| `shared/tutorial.js` | Yes | 4-step first-run tour: ping, read the number, mark, commit |
| `shared/mobile-dock.js` / `mobile-hud.js` | Probably not | Grid game with 3 controls; a fixed bottom action bar is enough. Revisit in M7 |
| `shared/info-page.css` / `info_page.py` | Partial | "About Signal" page via the CSS; the game is Pyodide-based now so `info_page.py` is usable, but Signal has no "Real Story" sources, so the CSS-only About panel is still enough |
| `shared/personal-best.css` | Yes | Fewest-pings-ever badge |
| `shared/ambient-bg.css` / `space-bg.css` | Optional | Subtle static-noise background, must respect reduce motion |
| Per-game files | Yes | `achievements.json`, `settings.js`, `changelog.json`, own `icons/favicon-signal.svg`, in-game feedback/report button, ad bar partial |
| Hub wiring | Yes | Title card + thumbnail class, `game-manifest.json`, regenerate `game-last-updated.json`/`game-added.json` via `scripts/generate-last-updated.py` |
| Colorblind rule | Yes | Number + glyph + fill pattern; no hue carries meaning (cell tint is decoration only) |

## Achievements (14)
1. First Contact — complete any puzzle.
2. Clean Signal — solve in the fewest pings the solver says is possible (par).
3. Under Par — beat the reference ping count (should be near impossible on hard; that's the point).
4. Lucky Guess — commit correctly with 4+ pings unused.
5. Three in a Row / Week on Air (7-day streak) / Month on Air (30-day).
6. Hard Copy — win a hard puzzle.
7. Both Bands — win easy and hard on the same UTC day.
8. Last Gasp — win using your final ping.
9. Static — lose a puzzle (kindly worded: "Everyone loses one").
10. Archivist — play 10 archive puzzles.
11. Overlap — ping a cell with a reading of 9+ (two fields stacking).
12. Silent Night — get a 0 reading three times in one puzzle (wasteful, funny).
13. Show Off — use the share button.
14. Puzzle #100.
Follows `ACHIEVEMENTS-SYSTEM-DESIGN.md`: `achievements.json` manifest + `achievements_earned` in state, no backend change.

## Testing approach
- pytest (repo convention) for the Python engine (the only implementation): generator determinism (same date -> same board), spacing/edge rules, solver uniqueness for every date across 3 years of seeds, both modes, scoring/par, streak recompute, merge rule, state round-trip.
- **Frozen fixtures** (replaces the old JS parity fixtures): JSON of 365 dates x modes generated by the Python generator and committed; a test asserts the generator still reproduces them. Any generator change forces a `v2` seed bump. Plus archive, practice and generation-time tests (see Decisions).
- Fake-DOM-style UI tests only for the reading -> glyph mapping and share-text builder (pure functions, no DOM needed).
- Manual/live verification via the shared `hub-dev-server`: keyboard-only playthrough, 360px mobile view, high-contrast, reduce-motion, a midnight-UTC rollover (mock the clock).

## Milestones
REVISED 2026-09-27 (Pyodide stack, archive, practice, bigger boards). Milestones 1-5 ship a complete daily game.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Generator + solver (Python only) | Seeded RNG, generator, brute-force solver for 9x9, pruned constraint solver for big boards, uniqueness check, frozen fixtures, per-preset timing report. Demo: CLI prints today's board and solves it | Not started |
| 2 | Static shell + engine bridge | Static HTML shell, lazy Pyodide load, queued taps, saved-state view without the engine, cold/warm timing recorded in the dev log, Pyodide cache check | Not started |
| 3 | Playable board | Grid, ping, reading display (number + glyph + fill), ping budget, mark + commit, win/lose reveal. Easy mode | Not started |
| 4 | Daily loop + stats | UTC rollover, daily-versus-archive rule, stats/histogram, streaks derived from `days`, localStorage persistence | Not started |
| 5 | Share + hard mode | No-spoiler share text (+ ASCII fallback), hard mode, mode toggle, per-mode stats. **First complete, playable daily game** | Not started |
| 6 | Archive | Month calendar with per-mode status, archive play, separate stats bucket, future-date refusal | Not started |
| 7 | Endless practice + bigger boards | Practice mode with shareable codes, Wide and Big Sky presets, per-preset ping budgets from measured par, daily eligibility decision per preset | Not started |
| 8 | Save system + settings | Save widget integration with merge rule (new key format), `settings.js` (contrast, motion, text scale), confirm dialogs | Not started |
| 9 | Achievements + changelog | 14 achievements (add archive and practice ones), in-game panel/toast, `changelog.json` panel, tutorial tour, info page | Not started |
| 10 | Polish + hub integration | Assist shading, keyboard/mobile audit, colorblind audit, favicon, flavour text pass, title card, thumbnail, manifests, feedback/report button, dev-log entries, tag | Not started |

Per repo rule: commit + tag each as `git tag signal-milestone-0N`.

## Risks
- **Solvability is the whole game.** A puzzle that is technically unique but needs 12 pings is unfun. Mitigation: the solver reports a par (minimum pings a greedy-optimal strategy needs) and we reject seeds whose par exceeds budget-2.
- **Genre sameness.** Might read as "Minesweeper with sums" to some. Mitigation: playtest the summed-field feel early (M2) before investing in the shell.
- **Cold-start wait (new, replaces JS/Python drift).** With one Python implementation there is no drift risk, but the first ping of a cold session waits for Pyodide. Mitigation: the static shell, queued taps, cache-first Pyodide via `sw.js`, timings recorded at Milestone 2, and the stated criterion for reopening the JS-port decision.
- **Big-board generation cost.** Generation and uniqueness checks on 13x13 and 15x15 boards may be too slow in Pyodide. Mitigation: pruned solver, per-preset time budgets, big boards start practice-only.
- **UTC vs local midnight** can feel wrong at 6pm for some players (UTC-based rollover). Mitigation: show countdown clearly; consider a setting later.
- **Clock tampering** for streaks: accepted, it's a local toy; no leaderboard, so no cheating incentive.
- Share glyphs may render badly in some chat apps (ASCII fallback covers it).

## Open questions for the user
All six were answered in Round 3 (see the Decisions section at the top): Pyodide (decided by me), retro radio-room, UTC plus archive, endless practice yes, launch date not tied to a special day, Option A plus bigger-board modes.
Still open, small: which bigger-board presets (if any) should also be daily modes once the timings are known (Milestone 7 decides).
