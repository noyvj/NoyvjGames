# Constellations (slug `constellations`, TODO QI-8) - Groundwork Plan

Source: the Quick ideas round (A8), owner-approved: "connect stars by rules to complete real sky maps, collecting each constellation with a short sourced note." Checked against `PLAYER-PROFILE.md`: spatial and logic puzzles first, collecting "one of each", space and a dark moody look, a sticker-book shelf plus percentage bar, no timers, facts accurate but fun-first. Personal project, no BCM tag, working title.

Pitch: a night-sky logic puzzle where numbers on stars say how many lines touch them, and the figure that falls out is a real constellation you then keep in your sky atlas.

## 1. Concept
- You are the keeper of a dim observatory on a ridge (invented: Hollin Ridge). Each chart shows a patch of sky: stars at their real positions with bright ones larger. Some stars carry a number (how many lines must touch it). You draw lines between stars to make one connected figure where the numbers all hold and no lines cross. The finished stick figure is the traditional constellation shape.
- 2-minute session: one small figure (Crux, Triangulum). 20-minute session: a quarter of the atlas or a big one (Orion, Ursa Major) built carefully.
- Look: dark sky, faceted low-poly star points with a soft glow (effects toggleable), lines drawn thin and bright. Stars are told apart by number and ring shape, not just brightness. Quiet voice: the keeper's one-line log.

## 2. Core rules (pure functions)
- A chart is a set of stars with 2D positions (sky projected flat), a set of allowed edges (only pairs within a neighbour distance, so there are not hundreds of choices), and clues: a number on some stars (degree), some edges marked "must" or "never" as fixed given lines or crossed-out pairs.
- Valid figure: every number is met exactly, no two chosen edges cross, the chosen edges form one connected figure that includes all stars that have a number, and any star without a number may have any degree (including 0 for a spare star shown as "outside the figure").
- Drag from star to star to draw a line; tap a line to remove it; a ghost shows the allowed neighbours when a star is held. Done is available when valid. Nothing can be failed.

## 3. Content size
40 charts in 5 sky seasons (chapters) of 8: Winter Sky, Spring Sky, Summer Sky, Autumn Sky, Southern Sky. Sizes from 5 stars (Crux) to 14 (Orion, Ursa Major). Chapter n+1 opens at 5 of n; any order inside.

## 4. How correctness is PROVED
- Dev tool `tools/figures.py` takes a constellation's real star positions and line list, derives the clues (degrees plus a minimal given-lines set) and runs an exhaustive solver counting all valid figures. Tests assert exactly ONE valid figure per chart and that it equals the stored traditional figure.
- Clue minimality: removing any single clue makes the solution count rise above one (so no clue is padding), checked in tests for each chart.
- Geometry tests: crossing detection on exact integer coordinates, projections frozen in data; no clock, no random.
- Data tests: each chart has a source note and a catalogue id for every star.

## 5. Collection and 100%
- The Sky Atlas: a wide planisphere panel that gains each figure when solved, shown in its place in the sky, with a card (name, short note, brightest star, best season to see it, the source and read date). A dim ghost outline for each unfound figure shows how much is left. 100% = all 40 charts finished. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Constellations, Stars joined, Atlas pages, Seasons done. The tally counts lines drawn and erased.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (one star whose number forces its lines), Hint (one forced line shown as a ghost), Answer (the full figure as a ghost with a "Draw it" button). Free, on request.

## 7. Achievements (14)
First Figure; Ten Figures; Twenty Figures; Forty Figures; Winter Done; Spring Done; Summer Done; Autumn Done; Southern Done; The Hunter (Orion); The Bears (Ursa Major and Ursa Minor); Southern Cross (Crux); No Hints Needed (10 figures with none); Long Night (draw 500 lines).

## 8. Real-world facts
Star positions and magnitudes are read live from the HYG star database (github.com/astronexus/HYG-Database) and the traditional line figures from the Stellarium constellation data (stellarium.org), each noted with its read date; the short constellation note is written for the game from the IAU constellation list (iau.org). A bundled dated snapshot is the offline fallback. Fun first, accuracy second, sources on the About page.

## 9. Reuse
Grid and graph validator patterns from Hull Repair (`rules.py`, `play.py`, `render.py`); solver-in-`tools/` pattern; `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `space-bg.css`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine and prover | Star data, edge validator, crossing test, uniqueness solver, season 1 (8 charts) with proofs |
| 2 | Chart UI | SVG sky, drag lines, pointer and keyboard, done card, save contract. Playable slice |
| 3 | Seasons 2-3 | 16 more charts, Sky Atlas panel and cards, season gating |
| 4 | Seasons 4-5, hints, goals | 16 more charts (40), southern sky, hint ladder, three-goals strip, live data. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Western (IAU) constellations only, or also a few figures from other sky traditions with their sources? Default: IAU only for now.
2. Should the atlas show the real sky for the player's hemisphere? Default: no, one fixed atlas.
