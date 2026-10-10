# Anomaly Catalogue (slug `anomaly-catalogue`, TODO QI-21) - Groundwork Plan

Source: the Quick ideas round (C1), owner-approved: "a fixed set of odd rooms or screens where you spot what changed and file it in a field catalogue (the kind of anomaly games you like to watch)." Checked against `PLAYER-PROFILE.md`: horror and anomaly games, collecting one of each, a notebook being filled in, investigation that gets easier with learning, dark moody look, calm, no timers, nothing lost, no jump scares or on-screen death. Personal project, no BCM tag, working title. Different from Evidence Hunt (deduce a spirit from readings): this is visual comparison and filing.

Pitch: walk through a fixed set of quiet, slightly wrong rooms, spot what is different from how it should be, and file each anomaly in your field catalogue.

## 1. Concept
- You are a surveyor on a night inspection of an empty facility (invented: Station Ninefold). Each room is shown as a clean reference frame (Last Survey) and a Now frame. Look for what changed: a clock with no hands, a door in the wrong wall, a shadow with no object. Tap an anomaly to File it: choose its kind from the catalogue and the entry is added.
- 2-minute session: one room. 20-minute session: a floor of eight rooms.
- Look: dark, moody low-poly rooms drawn as SVG scenes built from scene data (no generated or photographed images). Differences are told apart by outline and label as well as light. Calm, quiet tone: the facility is odd, never aggressive.

## 2. Core rules (pure functions on scene data)
- A room is a scene description: objects with a shape, position, scale, light and a state. The Now scene is the Last Survey scene with a list of changes. Anomaly kinds: Missing, Added, Moved, Changed (size or shape), Wrong Light, Impossible (physics or geometry), Sound-mark (a visible noise glyph). Each room has 3 to 6 anomalies.
- Tap an object (or hold to place a Look-closer lens at 3x). On a hit the anomaly opens a short field note and asks for its kind; the right kind files it, a wrong kind just says "not that, try another" with no penalty and no counter. Misses cost nothing and do not log.
- A room is Surveyed when all its anomalies are filed. A Compare toggle flips between frames (never a timed flash). A room can be re-visited freely.

## 3. Content size
24 rooms in six floors of 4 (Lobby, Canteen, Control, Dormitory, Greenhouse, The Sublevel), about 100 anomalies and 100 catalogue entries. Floor n+1 opens at 3 of 4; any order inside. Every room is fixed; there is no random room.

## 4. How correctness is PROVED
- The declared anomaly list is derived from a scene diff: tests compute the set of differences between the Last Survey and Now scenes with an automatic comparer and assert it equals the declared list exactly (no hidden, undeclared differences, no duplicates), so the game is always fair.
- Visibility lints: each anomaly has a hit area of at least 44x44 screen pixels at the smallest layout (or a flagged Look-closer target at 3x) and a minimum contrast against its background, checked by a geometry test.
- Catalogue entries each map to a kind; determinism: pure functions, no clock, no random.

## 5. Collection and 100%
- The Field Catalogue: about 100 entries in a ring-binder, grouped by kind, each with a drawn thumbnail (re-drawn by code from the room scene), the room it was found in, a dry two-line note and a "have I seen this before" cross-reference (many anomalies repeat across floors with a twist). 100% = every room Surveyed and every entry filed. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with bars. Stats strip: Rooms surveyed, Entries filed, Kinds seen, Floors done. The tally counts taps and compares; every tap that hits or misses moves a visible number.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which part of the room, as a quadrant, still has something), Hint (the kind of the next unfiled anomaly), Answer (circles it and names it). Free, on request.

## 7. Achievements (14)
First Entry; Ten Entries; Fifty Entries; Full Catalogue; Lobby Done; Canteen Done; Control Done; Dormitory Done; Greenhouse Done; The Sublevel; Seven Kinds (one of each kind filed); Sharp Eyes (a room with no hint); Lens Out (10 uses of Look closer); Floor Walker (all six floors started).

## 8. Real-world facts
None, fiction. The About page notes the genre (spot-the-difference and anomaly-detection games) as inspiration and lists the visual-perception topic "change blindness" with a named source (a Wikipedia REST summary, read date shown, bundled copy fallback).

## 9. Reuse
Scene renderer in the pattern of Hull Repair's SVG station map; Evidence Hunt's notebook and field-guide panels and hint ladder; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `ambient-bg.css`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Scene engine and checks | Scene data model, diff comparer, anomaly kinds, geometry lints, floor 1 (4 rooms) with proofs |
| 2 | Room UI | SVG scene view, Compare toggle, Look closer, filing dialog, save contract. Playable slice |
| 3 | Floors 2-4 | 12 more rooms, more kinds, Field Catalogue binder |
| 4 | Floors 5-6, hints, goals | 8 more rooms (24), cross-references, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should a few late rooms be gently unsettling (a figure that is there only in the Now frame) or stay strictly odd objects? Default: odd objects only, nothing that harms or chases.
2. Is a hold-to-zoom lens enough for accessibility, or should every room offer a list-view of objects too? Default: add the list view as the screen-reader path.
