# Pattern Match (slug `pattern-match`, TODO QI-36) - Groundwork Plan

Source: the Quick ideas round (G3), owner-approved: "learn regular expressions by filtering garbled transmissions." Checked against `PLAYER-PROFILE.md`: coding and logic puzzles (yes), space and computers, short wins, a notebook or shelf that fills, hint ladder, "more game than teaching", working it out themselves, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: signals arrive from the dark half-eaten by noise; write a short pattern that catches the real messages and lets the static fall through.

## 1. Concept
The listening post **Needle** gets bursts of text: coordinates, call signs, dates, and static. Each **Tape** shows 8 to 14 lines. Some are **keep** lines (good transmissions), some are **drop** lines (noise or near misses). You type a pattern into one field and the tape marks, live, which lines it catches, in a calm way (a check mark and the matched part underlined; a miss is a dash and a word, never colour alone). When your pattern keeps every keep line and drops every drop line, the tape is **cleared** and the clean messages scroll into the log.
- 2-minute session: one tape, pattern `ZX\d+`, the call signs fall out of the static.
- 20-minute session: a chapter of six tapes that add one new tool each, ending with an **extract** tape where groups pull out the time and place.
- Look: dark, clean low-poly receiver frame with phosphor-dim monospace text; large matches with underline and bold, a status word per line. Quiet; optional generated clicks only.
- Safe by construction: the game uses its **own small matcher** (not the browser's or Python's engine) so a bad pattern cannot freeze the page: it has a step budget and a plain message ("that pattern is too tangled; try something simpler").

## 2. Rules (a pure function of the tape and the pattern)
- Supported teaching syntax, introduced chapter by chapter: literals and `.`, character classes `[abc]` `[a-z]` `[^x]`, `\d \w \s`, quantifiers `* + ? {n,m}`, anchors `^ $` and `\b`, groups `( )`, alternation `|`, and (last chapter) capture groups for extraction with a labelled output. Unsupported syntax is refused kindly (it lists what is supported), so the matcher is fully testable.
- A tape is cleared when: every keep line matches, no drop line matches, and for extract tapes the captured groups equal the expected values. A hidden **second tape** with extra lines of the same kind must also pass, so hard-coding the visible lines fails.
- **Par:** each tape stores the shortest known pattern length; matching or beating par earns a small mark, never required.
- Free retries and a free Reset; the last pattern is kept per tape. No clock, no randomness.

## 3. Content size
- 36 tapes in six chapters of six: Letters (literals), Any Of (wildcard and classes), How Many (quantifiers), Edges (anchors and boundaries), Either Or (groups and alternation), Pull It Out (capture).
- About 380 authored lines (call signs, times, grid references, serials) plus a seeded **Practice Static** generator that makes new tapes from a seed with a solver gate.
- A **Toolbox** of 18 pattern tools, collected the first time you use each correctly.

## 4. How fairness is PROVED (tests)
- **Matcher conformance:** over tens of thousands of generated (pattern, line) pairs in the supported subset, the game's matcher agrees with Python's `re` on match, start and end, and on captures. Unsupported syntax is rejected.
- **Budget test:** a battery of nasty patterns (nested quantifiers, huge repeats) are refused or stopped within the step budget; the page stays responsive.
- **Tape tests:** every tape has a stored reference pattern that clears both the visible and hidden tapes; a list of 3 to 6 tempting wrong patterns per tape (too greedy, missing an anchor) must **fail**; each keep and drop line is necessary (removing it lets a wrong pattern pass), so no filler.
- Practice generator: for 2,000 seeds, the solver confirms at least one pattern in the allowed subset separates keep from drop, or the seed is discarded.
- Determinism and source scan: no clock, no randomness (except seeded), no network.

## 5. Bigger picture, goals, hints
- The **Signal Log** is the picture: every cleared tape adds its clean messages to a growing log of 36 transmissions; a sky map of 36 stars dims or lights per tape; a completion percentage bar sits above. The Toolbox fills.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Tapes cleared, Tools known, Par marks, Practice tapes.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (what the keep lines share), Hint (which tool to use), Answer (the pattern, with a Use it button; clearing still counts).
- Every chapter and tape is open from the start; the order is a suggestion.

## 6. Achievements (14; computed from facts)
1 First Catch (clear 1); 2 Ten Tapes; 3 Chapter Clear; 4 Whole Sky (all 36); 5 Par (5 par marks); 6 Thirty Par (all authored par marks); 7 Toolbox Half (9 tools); 8 Toolbox Full (all 18); 9 No Hints (a chapter with no Hint or Answer rung); 10 Edge Case (clear a tape with an anchor); 11 Either Way (clear a tape with alternation); 12 Pulled Out (first extract tape); 13 Practice Ten (10 practice tapes); 14 Second Opinion (all three hint rungs on one tape).

## 7. Real-world facts
Short About-page cards read live from named, dated sources: the history of regular expressions (Kleene's regular events, Ken Thompson's early text editors) and the Python `re` HOWTO. The game's matcher teaches a subset that matches Python's `re` on its cases (stated on the page). More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS, no build step. Modules: `matcher.py` (parser, backtracking matcher with step budget), `tapes_*.py`, `gen.py` (Practice Static), `check.py`, `toolbox.py`, `signals.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Repair the Ship's Code's "own sandbox module with its own proof tests" idea, `shared/seed.py` and `run-code.js`, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`.
- Save: best (shortest) pattern per tape, hint rungs, toolbox, practice seeds, flags. Saved patterns are re-checked on load, not trusted.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Matcher with step budget, conformance tests against `re`, tape checker, chapter 1 (6 tapes) with tempting-wrong proofs |
| 2 | Receiver UI | Pattern field, live marking, status words, signal log, save contract. Playable slice |
| 3 | Chapters 2-4, toolbox, hints | 18 more tapes, Toolbox, hint ladder, three-goals strip |
| 4 | Chapters 5-6 and Practice Static | 12 more tapes (36 in all), extract tapes, seeded practice. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. The game uses its own matcher for safety, which supports a clearly listed subset of regular expressions. Is that fine, or should it use the full Python engine with a hard cap on pattern length? Default: own matcher.
2. Par marks reward the shortest pattern. Keep them as an optional small mark, or drop them to keep it pure puzzle? Default: keep, optional.
