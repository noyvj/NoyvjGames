# Shared Station (slug `shared-station`, TODO QI-32) - Groundwork Plan

Source: the Quick ideas round (E2), owner-approved: "friends' finished puzzles light up rooms in a shared space station you can visit." Checked against `PLAYER-PROFILE.md`: space stations over forests, collecting and completionist, a bigger picture that grows, optional friend ties, friends leaving gifts or short notes with no chat, no mandatory leaderboard, "hide my score" style privacy, nothing lost, no timers. Personal project, no BCM tag, working title. One-line pitch: a dark orbital station whose rooms light up as you finish things in the other games, with a visitor mode that lets a friend walk through yours from a link.

## 1. Concept
Your station, **Lantern Ring**, has 60 rooms in six rings. Each room is tied to one **deed** in one of the site's games ("restore 10 rooms in Hull Repair", "finish chapter 3 of Logic Gates", "earn 5 achievements in Canopy"). When a deed is done on your account or device, its room lights up and gets a small plaque. Nothing is played inside the station itself except looking, moving the camera between rooms and reading plaques. It is a trophy hall made as a place.
- 2-minute session: open the station, see which new rooms lit since last time ("new arrivals"), read two plaques.
- 20-minute session: tour all six rings, pick the next deeds from the "Next lights" list, then visit a friend's station by link or one of three sample crews.
- **Visitor mode:** your station has a **Station Card** link. It carries a compact snapshot of which rooms are lit (a bitmask), your chosen display name from a closed word list or a short safe text, and a checksum, in the link itself, like `shared/run-code.js`. A friend opens it and walks your station read-only, "as of" the date in the link. No account, no server, no chat. Visitors see nothing but lit rooms and plaques. Sending a link is a deliberate act; nothing is public by default.
- Look: dark, calm, faceted low-poly station as a cutaway SVG with rings; lit rooms warm, unlit rooms drawn with a dashed outline and a number so state is never colour alone.
- Solo is the whole game: three **sample crew** stations (invented crews) are built in so a player with no friends can still "visit".

## 2. Rules (a pure function of the deed table and the player's game data)
- The **deed table** (`deeds.json`) lists 60 deeds. A deed has a game slug, a type (`achievements_count`, `achievement_id`, `chapter_done`, `stat_at_least`), a threshold and a plaque text. A room is lit when its deed is true in the reader's data.
- Data comes from the same sources the Climate Steward page and My Stats already use: the signed-in account's saves, with local saves as fallback. Read-only. Lit rooms never go dark: the station remembers the highest state seen (stored locally).
- Station Card: `KSTN-<name>-<60-bit lit mask in base 32>-<date>-<checksum>`. Decode shows the mask, name and date only, never executes anything and says it is unverified.
- A **gift** is optional and tiny: a visitor can leave one of 12 fixed "waves" (for example "Lamp left on for you") that appears as a preset line on the owner's guest shelf if the visitor sends a return link. No free text, no chat.
- No clock, no randomness.

## 3. Content size
- 60 rooms in six rings of ten (one per game family: Climate, Systems, Language and Story, Puzzles, Craft and Code, Sandbox), 60 deeds, 60 plaques of one quiet line.
- 3 sample crews with 20 to 45 lit rooms each. 12 waves. 14 achievements.

## 4. How fairness is PROVED (tests)
- Deed validation against the repo: every deed's game slug, achievement id and chapter key exists (tests read `games/*/achievements.json` and `game-manifest.json`), and every deed is achievable (the same fixtures that make each game's own 100% reachable).
- Card codec: round trip over thousands of masks and names, checksum catches single edits, a decoded card never has a display name outside the allowed set, and a tampered or over-long card is rejected.
- Determinism: the lit set is a pure function of the data (test with fixture saves); lit rooms never go dark (monotone test).
- Reader test: only reads; no write to any save.

## 5. Bigger picture, goals, hints
- The **Lantern Ring** is the bigger picture: six rings, 60 rooms, an overall percentage bar, and a "Next lights" list.
- Three goals always visible (any order): the three nearest unlit deeds, each with a count ("Hull Repair: 7 of 10"). Stats strip: Rooms lit, Rings complete, Visits made, Guest shelf.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (which game is closest), Hint (names the deed), Answer (a link to the game and the exact place to start).
- Everything open from the start; nothing needs a friend.

## 6. Achievements (14; computed from facts)
1 First Light (1 room); 2 Ten Lights; 3 Ring Lit (a whole ring); 4 Three Rings; 5 Whole Station; 6 Thirty Lights; 7 All Games Seen (a room lit in 10 games); 8 Card Sent (create a Station Card); 9 First Visit (open a card or sample); 10 All Three Crews (visit the samples); 11 Guest Shelf (receive a wave); 12 Waved Back (send a wave); 13 Quiet Corner (view every plaque); 14 Second Opinion (all three hint rungs on one deed).

## 7. Real-world facts
None, fiction. The station and its crews are invented. Each plaque names only a game and a deed.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step, no server. Modules: `deeds.py`, `reader.py` (reads saves the way `steward.js` does), `station.py` (lit set, rings), `card.py` (codec), `crews.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses `shared/run-code.js` and `run_code.py` pattern for the card, `profile.js` data, `game-manifest.json`, `goals-panel.js`, `hint-ladder.js`, `save-widget.js`.
- Save: the highest lit set, visits, waves, hint rungs, flags.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Deed table, reader, lit-set rules, validation against the repo, ring layout with tests |
| 2 | Station UI | SVG station, camera moves between rooms, plaques, save contract. Playable slice |
| 3 | All 60 rooms | Full deed table and plaques, Next lights, percentage bar, hint ladder, three-goals strip. First complete game |
| 4 | Visitor mode | Station Card codec, sample crews, waves and guest shelf |
| 5 | Standard kit | Opening screen, tutorial, settings, About with the privacy note, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Shared Station and Space Museum both celebrate what you have done on the site (rooms lit versus objects placed). Keep both as separate games, or merge them? Default: keep both; the station shows status, the museum shows arranging.
2. Should visitors be able to leave one of 12 fixed "waves", or no gifts at all in v1? Default: waves in, free text never.
3. Should the Station Card include a display name, or only the lit rooms? Default: a name from a short closed word list.
