# Signal — Groundwork Plan (round-2 M3)

Status: PLAN ONLY. No `games/signal/` folder exists yet. Once approved, this becomes the seed for `games/signal/CLAUDE.md` (per `game-template.md`).
User answer (round 2, M3): "may as well try it, it seems very simple but that can be good." Taste rule (M answers): fun over teaching. Nothing here teaches anything.

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
- **Deliberate exception to the Pyodide default: plain vanilla JS** for the play surface. Rationale: a daily puzzle must open instantly (Pyodide load time is bigger than the whole game), and the logic is ~200 lines. Flag this in `games/signal/CLAUDE.md` as a documented exception.
- **Keep a Python reference implementation of the generator + solver in `games/signal/tests/`** (pytest) and a parity test: the JS generator's output for 365 fixed dates must equal the Python reference's output (fixtures generated once, committed as JSON). This preserves the repo's "real tested Python logic" convention without shipping Pyodide.
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
accept only if the puzzle is *solvable*: a brute-force solver over all
C(49,3) candidate sets, given a fixed reference ping sequence of 8 cells
(chosen by the same rng), leaves exactly 1 consistent set.
```
- Version string `v1` in the seed lets us fix generator bugs later without silently changing past days' puzzles (past days are frozen by version).
- UTC (not local) so everyone shares a puzzle number; the UI shows "next puzzle in HH:MM" computed only on render.
- Puzzle number = days since 2026-10-01 (launch date placeholder).
- Easy: 9x9, 2 transmitters, 10 pings, live "possible cells" shading toggle. Hard: 9x9, 4 transmitters, 8 pings, no shading assist, min spacing 2.

## Data model / state shape
`get_state()` (JS `getState()` mirror; this is what the save widget stores):
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
  - Generator + solver (JS + Python reference): Claude.
  - Flavour strings (win/lose/near-miss lines, ~40 of them, per-mode): Claude drafts, user vetoes tone.
  - Archive: any past date from launch is playable as practice, generated on demand.
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
| `shared/info-page.css` / `info_page.py` | Partial | "About Signal" page via the CSS; `info_page.py` is Pyodide-oriented so use static HTML |
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
- pytest (repo convention) for the Python reference: generator determinism (same date -> same board), spacing/edge rules, solver uniqueness for every date across 3 years of seeds, both modes, scoring/par, streak recompute, merge rule, state round-trip.
- **Parity fixtures**: JSON of 365 dates x 2 modes generated by Python; a Node (or headless-browser) script asserts the JS generator matches. Any generator change forces a `v2` seed bump.
- Fake-DOM-style UI tests only for the reading -> glyph mapping and share-text builder (pure functions, no DOM needed).
- Manual/live verification via the shared `hub-dev-server`: keyboard-only playthrough, 360px mobile view, high-contrast, reduce-motion, a midnight-UTC rollover (mock the clock).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Generator + solver | Python reference + JS port, seeded RNG, uniqueness check, parity fixtures. Demo: CLI prints today's board and solves it | Not started |
| 2 | Playable board | Grid, ping, reading display (number + glyph + fill), ping budget, mark + commit, win/lose reveal. Local only, easy mode | Not started |
| 3 | Daily loop + stats | UTC daily rollover, one-per-day rule, stats/histogram, streaks derived from `days`, localStorage persistence | Not started |
| 4 | Share + hard mode | No-spoiler share text (+ ASCII fallback), hard mode, mode toggle, per-mode stats | Not started |
| 5 | Save system + settings | Save widget integration with merge rule, `settings.js` (contrast, motion, text scale), confirm dialogs | Not started |
| 6 | Achievements + changelog | 14 achievements, in-game panel/toast, `changelog.json` panel, tutorial tour, info page | Not started |
| 7 | Archive + polish | Practice archive, assist shading, keyboard/mobile audit, colorblind audit, favicon, flavour text pass | Not started |
| 8 | Hub integration | Title card, thumbnail, manifests, feedback/report button, dev-log entries, tag | Not started |

Per repo rule: commit + tag each as `git tag signal-milestone-0N`.

## Risks
- **Solvability is the whole game.** A puzzle that is technically unique but needs 12 pings is unfun. Mitigation: the solver reports a par (minimum pings a greedy-optimal strategy needs) and we reject seeds whose par exceeds budget-2.
- **Genre sameness.** Might read as "Minesweeper with sums" to some. Mitigation: playtest the summed-field feel early (M2) before investing in the shell.
- **JS/Python drift.** Two implementations can diverge; parity fixtures are the guard.
- **UTC vs local midnight** can feel wrong at 6pm for some players (UTC-based rollover). Mitigation: show countdown clearly; consider a setting later.
- **Clock tampering** for streaks: accepted, it's a local toy; no leaderboard, so no cheating incentive.
- Share glyphs may render badly in some chat apps (ASCII fallback covers it).

## Open questions for the user
1. Plain-JS exception OK, or do you want Pyodide anyway for consistency (costs a multi-second first load on a "quick daily" game)?
2. Theme: retro radio-room (recommended) or something else (submarine sonar, alien SETI)?
3. UTC daily reset acceptable, or prefer each player's local midnight (then different time zones get different puzzles, killing "same puzzle for everyone" share talk)?
4. Want an optional non-daily "endless" practice mode beyond the archive?
5. Should the launch date (puzzle #1) be tied to a specific day for the 2-week visibility cadence?
6. Is Option A the mechanic you want, or should we prototype B briefly first?
