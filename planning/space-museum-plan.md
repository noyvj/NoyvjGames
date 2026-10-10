# Space Museum (slug `space-museum`, TODO QI-24) - Groundwork Plan

Source: the Quick ideas round (C4), owner-approved: "curate a museum of objects you have collected across the site, arranged in rooms." Checked against `PLAYER-PROFILE.md`: collects everything, a shelf or sticker book for collections, completion percentage bars, pictures and scenes over numbers, Unpacking-style calm placing (small, heavily changed), short wins that build a bigger picture, space and science fiction, dark moody, no timers, nothing lost. Personal project, no BCM tag, working title. One-line pitch: a quiet museum in a decommissioned orbital ring where every achievement you earn anywhere on the site becomes an object you can place, label and arrange in themed rooms.

## 1. Concept
You are the new curator of the Meridian Collection, a dim museum with 12 empty rooms. Objects come from two places: (a) **Site objects**, one for every achievement in every game, minted from the achievement lists the hub already keeps (a coin for First Spark, a lantern for Lantern, a small brass compass for a Dead Reckoning one) and (b) **Museum finds**, 40 objects you earn inside the museum by small curating jobs, so a brand-new visitor with no other progress still has a full game.
- 2-minute session: open the Atrium, drag three objects onto plinths, read the card, light the room's lamp when its brief is met.
- 20-minute session: refit a whole wing, reorder shelves, write labels from a short word list, and catch up on objects newly earned in other games (a "new arrivals" tray).
- Look: dark, calm, low-poly rooms drawn as SVG (plinths, shelves, a glass case, a hanging rail), objects as small faceted icons told apart by shape and a name, never colour alone. Quiet; optional generated sound only through `shared/sfx.js`.
- Nothing can be broken or lost: objects are never consumed, a removed object returns to the tray, and an earned object never goes away.

## 2. Rules (a pure function of the catalogue, the collection and the layout)
- 12 rooms, each with 4 to 9 slots (plinth, wall, case, shelf). Every object has tags: its game, a theme (Quiet, Machines, Sea, Stars, Numbers, Words, Weather, Crew), a size (small, medium, large) and an era word. Placing is free and instant.
- Each room has a **brief**, a plain sentence the layout either meets or does not ("Three objects from three different games", "Large ones on the floor, small ones in the case", "One object of every theme"). Meeting a brief lights the room's lamp and adds a **visitor note** (a short quiet line from an invented visitor). Briefs are written as checks over tags.
- Each room can be re-themed once met; nothing is locked. No scoring, no ranking of layouts, no penalties for mismatch (a mismatch just shows which part of the brief is unmet).
- Determinism: brief checks are pure functions of the layout; there is no clock and no randomness.

## 3. Content size
- 12 rooms and 12 briefs; each room also has two optional "arrangements" (a pair of extra briefs), 36 in all, giving the short wins.
- 40 museum finds (earned by the 12 briefs, the arrangements and a "label a room" job each) and about 300 site objects (one per achievement in `games/*/achievements.json`, count changes as games change; a build step regenerates `catalogue.json`).
- Object cards: a name, a one-line description written once per achievement from its title (template-driven with a hand-written override list for about 60), the game it came from and the date it was earned.

## 4. How fairness is PROVED (tests)
- A solver (`tools/brief_solver.py`) shows every brief is satisfiable from **museum finds and the starter set alone** (a fresh visitor can light all 12 lamps and meet all 36 arrangements with no site objects), and that no brief needs a specific site object.
- Catalogue lint: every achievement file in the repo maps to exactly one object; ids are unique and stable; removing a game's achievement never invalidates a saved layout (missing objects drop out of slots into the tray).
- Layout save round trip and tampering tests (unknown objects, duplicate objects, over-full rooms are rejected or repaired). Determinism: brief evaluation is order independent.
- Reading other games: a test loads the saves reader against fixture saves for every game and checks `achievements_earned` is read read-only and never written.

## 5. Bigger picture, goals, hints
- The **Floor Plan** is the bigger picture: 12 rooms as a ring, dark until met, lit when met, with an overall museum percentage bar (rooms lit, arrangements met, finds earned). Site objects show as a separate **Donations shelf** counter (a soft bonus, not part of the 100%).
- Three goals always visible (any order): the next three unmet briefs or arrangements, each with a count such as "Atrium: 2 of 3 games".
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which tag the brief is about), Hint (names two objects you own that would help), Answer (shows a full layout as a ghost with a "Place these" button).
- Everything open from the start; a visitor with a full site history just starts with more in the tray.

## 6. Achievements (14; computed from facts)
1 First Plinth (place 1); 2 Lamp On (light 1 room); 3 Half the Rings (6 rooms); 4 Whole Floor Plan (12 rooms); 5 Arranged (12 arrangements); 6 All Thirty-Six (all arrangements); 7 Forty Finds (all museum finds); 8 Well Labelled (label every room); 9 Many Games (one object from 10 games on display); 10 Every Theme (all 8 themes on display); 11 New Arrivals (place an object earned in another game); 12 Donor (50 site objects held); 13 Second Opinion (all three hint rungs on one brief); 14 Closing Time (every room lit and every case labelled).

## 7. Real-world facts
None, fiction. The museum and its visitors are invented. (The object names come from the games' own achievement titles, so they carry no real-world claims.)

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `catalogue.py`, `briefs.py`, `layout.py`, `solver.py`, `reader.py` (reads saves and achievement progress, the same way `steward.js` and `my-stats.html` do, signed-in account saves with local fallback), `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses `shared/profile.js` data, `game-manifest.json`, `shared/goals-panel.js`, `hint-ladder.js`, `save-widget.js`, `confirm-dialog.js`, `shared/export_progress.py` pattern for the layout code.
- Save: the layout, labels, finds, hint rungs, flags. Site objects are recomputed each load from the other games' saves, never stored as authoritative.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Catalogue builder, tags, brief checks, layout rules, solver proof that every brief is satisfiable from finds alone, 4 rooms |
| 2 | Room UI | SVG rooms, drag and keyboard placing, object cards, lamp, tray, save contract. Playable slice |
| 3 | All 12 rooms and finds | Remaining rooms, 36 arrangements, museum finds, labels, Floor Plan, three-goals strip, hint ladder |
| 4 | Site objects | Reader for other games' saves, donations shelf, new-arrivals tray, missing-object repair. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should the museum percentage count only the museum's own finds and rooms (so 100% never needs other games), with site objects a separate bonus shelf? Default: yes.
2. Should an object name be taken straight from the achievement title, or should I hand-write a nicer object for every achievement (about 300 short lines)? Default: titles with about 60 hand-written overrides.
3. Should visitors see someone else's museum (an invite-link snapshot, like Shared Station)? Default: no, that stays in Shared Station.
