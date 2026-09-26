# Heist Committee — Groundwork Plan (Round 3 M1)

Status: PLAN ONLY. No `games/heist-committee/` folder exists yet. Once approved, this becomes the seed for `games/heist-committee/CLAUDE.md` (per `game-template.md`).
User answer (Round 3, M item 1): "yes". Taste rule (standing): fun first, funny, no lesson. No BCM tag (personal project). Working title only.

**Shared baseline:** everything in `overclock-plan.md` section 4 (save, settings, achievements, changelog, tutorial, confirm dialog, mobile dock/HUD, colorblind rules, test harness, feedback) and section 5 (hub integration) applies here with slug `heist-committee`. Section 11 of this file lists only what differs.

## 1. One-line pitch
Pick a target, hire five oddball specialists who do not get along, drag their actions into a timeline, then watch the job play out beat by beat while complications and personality clashes chain into each other, and see whether your plan soaked them up or fell over.

## 2. Concept
The fun is the plan-versus-reality gap. You never control the heist itself. You control the plan, and the plan is a grid: five crew lanes by 6-10 beats. During playback the game resolves each beat in order and narrates what happened in short funny lines. Complications are not random noise: each one has a trigger, a set of tags it emits, and known counters. A good plan leaves slack, pairs the right people, and holds a standby person for the thing you scouted. A greedy plan works until one small thing (a sneeze, a dog, a chatty driver) sets off a chain.

Design pillars:
1. **Readable cause and effect.** Every playback line names why it happened ("Dot's nervous trait fired because the alarm went off"). No hidden dice the player cannot reason about.
2. **Scouting gives partial information.** Before planning you see some, not all, of the target's complication pool. Missing one is funny, not unfair.
3. **Personality is the puzzle.** Crew traits interact (rivals, mentors, allergic-to-each-other). Placing two people in the same beat or adjacent beats changes outcomes.
4. **Failure is comedy, not punishment.** No permadeath, no game over. A botched job still pays something and produces a story.
5. **Short.** One heist is 5-10 minutes: recruit (1-2), plan (2-4), playback (1-2), payout screen.

## 3. Stack
- Default: Python via Pyodide, plain HTML/CSS, no build step, run via `python -m http.server`. No deviation.
- All rules are pure turn logic in `game.py` (split into `engine.py`, `content.py` later if needed, as Continuum did). No timers in the sim. Playback is a "Next beat" button plus an optional auto-advance that only calls Python once per beat at a human pace. No real-time precision is needed anywhere.
- **Honest limit, drag and drop:** native HTML5 drag-and-drop is unreliable on touch. The timeline uses pointer events for drag, plus a tap-to-select then tap-a-slot path that is the always-supported method (also the keyboard path). Test both at 375px.
- Timeline and crew cards are DOM/CSS grid (buttons in cells), not canvas, for accessibility, text scaling and fake-DOM testing.

## 4. Core constraints (do not violate without asking)
1. The heist resolution is a **pure function of (state, plan, seed)**. Same inputs give the same event log, byte for byte. Tests depend on it.
2. **No hue-only encoding.** Action types, crew roles, complication severity and success/fail carry an icon and a text label as well as color.
3. No timers gate or race play (no "you have 30 seconds to plan"). Planning time is unlimited.
4. Chain reactions have a hard depth cap (default 6 links per beat) so a loop cannot run forever; tests enforce that every complication terminates.
5. Humor is about the crew and the situation, never about real groups of people. No real brands, real banks or real people. Targets are invented.
6. The player can always fully undo and re-plan before pressing **Start Heist**; after that the playback is fixed.
7. Nothing violent is depicted. The "heist" is capers-style: alarms, disguises, cats, escalators, awkward small talk.

## 5. Game design

### 5.1 Structure of a run ("Career")
There is no roguelike permadeath. A **career** is a series of jobs, each one standalone:

1. **Contract board:** 3 targets offered, drawn by seed from the target pool (rotating pool; later ones unlock by reputation). Each shows tier, payout range, number of beats, and how much **intel** you can buy.
2. **Scout (optional, spends a small "prep" budget, not real time):** reveals some of the target's complication pool and one guard/lock detail.
3. **Recruit:** choose 5 crew from 8 offered candidates. Each candidate card shows role, two skills, and one **trait** (the clash source). Their **quirk** (a second, hidden-until-seen trait) can be learned by scouting them or by hiring them.
4. **Plan:** fill the timeline.
5. **Playback:** the heist resolves beat by beat.
6. **Payout:** loot, heat, crew relationships change, a funny one-paragraph write-up ("The Fountain Incident").

### 5.2 The timeline
- Grid: **lanes = the 5 crew members, columns = beats**. Beats are called by target-specific names (Arrive, Lobby, Vault, Exit...). Beat count: 6 for the first target, up to 10 later.
- Each cell holds one **action** from that crew member's action list (role-based, e.g. Lockpick, Sweet-talk, Distract, Drive, Hack, Lookout, Carry, Improvise), or Wait.
- Each action has: duration in beats (1-2), **noise** (0-3), **suspicion** (0-3), required skill, tags it emits (`noise`, `wet`, `crowd`, `flash`, `alarm`), tags it needs (`clear_corridor`, `unlocked`), and success odds shown as words (Solid / Risky / Long shot), never as hidden percentages.
- **Standby** is a special action: the crew member holds a "cover tag" (chosen from a short list, e.g. `noise`, `alarm`, `crowd`) for that beat and will absorb the first matching complication with a good outcome. Standby is the core resource trade-off: someone standing around costs efficiency.
- **Slack beats:** a beat with no scheduled critical action is where complications land more softly.
- Validation panel (live, plain text): "Vault door needs Lockpick in beat 3 and Lookout in beat 3." Missing requirements are warnings, not blockers; you may run a broken plan on purpose.

### 5.3 Crew
Twenty specialists at launch (8 offered per contract). Each: name, role, 2-3 skills (0-3 pips), 1 trait, 1 quirk, a one-line voice.
Example trait set (about 20): Nervous (fails under `alarm`), Chatty (adds `noise` when idle), Perfectionist (slow but never fails a 2-beat action), Overconfident (skips standby duties), Lucky (rerolls one failure per heist, deterministically from the seed), Allergic (loses a beat near `dust` or `flowers`), Rival-of-X (bad outcome if in the same beat as X), Mentor-of-X (X gets +1 skill when adjacent), Superstitious (refuses Friday-13th-style tagged beats), Sentimental (steals one souvenir, adds `evidence`), Cat Person (distracted by any `cat` tag).
- Clashes are data: `pair_rules` in `traits.json`, each rule naming two trait/role selectors, the geometry that triggers it (same beat, adjacent beat, same lane neighbour), and the tag it emits.
- **Relationships persist across jobs** in `meta`: crew who work together get closer or worse (a small number per pair). Mechanically: a "Friends" pair unlocks a small bonus; "Feud" adds a standing pair rule. It is a comedy engine, so keep it to two states plus neutral.

### 5.4 Targets and complications
- Launch targets (invented): a small museum, a casino barge, a mountaintop observatory vault, a cheese vault ("the Affineur"), a botanical dome. Each has: beat names, an **objective** list (grab the item, cool-down exit), a **security profile** (guards, cameras, lock types) and a **complication pool** of 12-20 entries.
- A complication is data: `{id, name, beat_range, weight, requires_tags, forbids_tags, emits, effects, counters}`.
  - `requires_tags` is what must already have happened this heist (e.g. `noise` before a guard wakes).
  - `emits` is what it adds (`alarm`, `wet`, `crowd`), which can trigger further complications (the chain).
  - `counters` are the things that absorb it: a crew skill, a Standby cover tag, an item, a trait.
  - `effects` change small state: suspicion, time lost, a crew member sidelined for a beat, an action's tags altered.
- Selection each beat: eligible complications get weights; the seeded RNG picks 0 or 1 (occasionally 2 at high suspicion). The RNG is consumed in a fixed order so replay is exact.
- Chain example: Chatty crew member is idle (`noise`) -> sleepy guard wakes -> guard walks to the lobby -> the Distraction action's `crowd` tag is now needed but it was scheduled a beat later -> Distraction happens on time but the guard now stands next to the Lockpick lane -> the Nervous lockpick fails. The player sees the chain in the playback log as five short lines, and on the payout screen a "What happened" chain diagram that highlights the first link (so the lesson is always "where did it start?").

### 5.5 Resolving a beat (pure function)
```
resolve_beat(state, plan, beat_index, rng) -> list[event]
1. Apply scheduled actions for this beat in a fixed lane order (lane 1..5).
   Each: check needs, skill vs difficulty -> outcome in {crit, success, partial, fail}, emit tags.
2. Apply pair_rules (trait/geometry) that fire this beat.
3. Draw complications (0-2) from the target pool given accumulated tags and suspicion.
4. For each complication: look for counters in this order: Standby cover, crew skill, item, trait.
   Counter found -> "absorbed" (funny line, small bonus). None -> effects apply and may emit tags.
5. Process newly emitted tags for chain complications (loop to depth cap).
6. Update heat/suspicion/loot/time; return the event list (each event: type, actors, text key, tags).
```
UI is a pure render of the event list. Achievements and the write-up generator also read the event list.

### 5.6 Scoring and payout
- Loot value (objective completion), minus **heat** (leftover suspicion), minus **damages** (sidelined crew, broken gear). Bonuses: **Clean** (no alarm), **Chaos Theory** (finished with 3+ chain links), **Under Budget**, **Everyone Home** (no one sidelined).
- Payout funds the next job's scouting, better gear (small numeric edges and flavor), and crew hiring fees. There is no fail state; a low payout just slows progression.
- **Reputation** (meta) unlocks tougher targets and rarer crew. This is the meta-progression: unlocks only, no stat treadmill.

### 5.7 Replay value
Rotating target pool per career seed, 20 crew with different trait combinations, pair rules, seeded complication draws. Later: **Daily Job** (date-derived seed, same target/crew offer for everyone, score comparable with friends; reuses Signal's daily-seed and archive pattern if Signal ships first) and an opt-in leaderboard board (`heist-committee/best_daily`) via the existing `app/leaderboards.py` and `shared/leaderboard.js`.

## 6. Data model
```json
{
  "schema": 1,
  "meta": {
    "cash": 0, "reputation": 0, "jobs_done": 0, "jobs_clean": 0,
    "unlocked_targets": [], "unlocked_crew": [], "unlocked_gear": [],
    "relationships": {"dot|vic": "friends"},
    "seen_complications": [], "seen_traits": [],
    "best": {"cash_single_job": 0, "chain_links": 0},
    "achievements_earned": {}
  },
  "career_seed": 0,
  "job": null,
  "settings": {"text_scale": 1, "reduce_motion": false, "story_text": true, "autoplay_speed": "normal"}
}
```
`job` is `null` between jobs, otherwise `{"phase": "board|scout|recruit|plan|playback|payout", "target": id, "offer": [crew ids], "crew": [5 ids], "plan": {"lanes": [[action_id|null, ...] x5]}, "rng": {"seed", "draws"}, "playback_cursor": n, "log": []}`. Mid-playback saves are safe because the log so far and the RNG state are serialised. `load_state` tolerates missing keys and unknown versions. `achievements_earned` is written to state and never read back, per `ACHIEVEMENTS-SYSTEM-DESIGN.md` section 7.

`content/`: `targets.json`, `crew.json`, `actions.json`, `traits.json`, `complications.json`, `gear.json`, `writeups.json` (phrase fragments for the payout paragraph). Ids are stable snake_case, never reused. Loaded like `achievements.json`: fetched in `index.html` `main()`, exposed as window globals, parsed by a Python loader with schema validation.

## 7. Content needs (who writes what)
- Claude drafts: 5 targets, 20 crew, ~25 actions, ~60 complications, ~30 counters/gear, ~120 short lines, the write-up fragments. User vetoes tone.
- Launch minimum for a genuinely playable game (Milestone 4): 3 targets, 12 crew, 20 complications, 3 gear pieces.
- Story text (crew banter, flavor lines, the "Committee" framing device) is switchable via the shared story toggle; mechanical lines (why something happened) are never hidden by it.

## 8. UI sketch (words)
- **Board:** three contract cards. **Recruit:** 8 crew cards in a scrolling row; picked five snap into lane headers. Each card: portrait glyph (letter + shape), role icon, skill pips (numbers too), trait chip, quirk shown as "?" until learned.
- **Plan:** timeline grid centre-screen; action tray below (mobile dock: the tray, plus Start Heist). Cell states: empty, planned, warning (icon + text), conflict (pair rule preview, an icon between the two lanes with a hover/tap tooltip). A left sidebar shows the target's known complications ("Scouted: a night guard, maybe a cat").
- **Playback:** the timeline stays visible, a cursor moves across beats; below it a running log of short lines; a Next / Play / Skip-to-end control (no timers required: Next is the default). Failed cells shake (disabled under reduce motion) and show an icon.
- **Payout:** result banner, loot/heat/damage lines, the "chain diagram", a write-up paragraph, "Retry this target" and "Back to board".
- Keyboard: arrows move a cursor over the grid, Enter picks or places, Delete clears, `S` toggles Standby, `?` help.

## 9. Achievements (14)
1. First Job — finish any heist.
2. Nobody Saw Anything — a job with no alarm.
3. Chain Reaction — a heist with a 5-link chain.
4. Absorbed — absorb 3 complications in one job with Standby/counters.
5. Bring a Buddy / Old Rivals — a Friends pair; work a Feud pair without failing.
6. Everyone Home — no one sidelined.
7. Full House — hire all 5 roles in one crew.
8. The Cat Job — trigger the cat complication in every target.
9. Paid in Cheese — finish the cheese vault.
10. Over-Planner — a job with zero empty cells.
11. Minimalist — win with 3 or fewer actions per beat across the timeline.
12. Fifth Time Lucky — retry the same target 5 times.
13. Rich and Infamous — reputation threshold.
14. Committee Meeting — see 20 distinct complications.
Follows `ACHIEVEMENTS-SYSTEM-DESIGN.md` (manifest + `achievements_earned`, no backend change).

## 10. Testing approach
- pytest, SOL-style fake-DOM harness only for UI glue; the engine is pure Python and tested without a DOM.
- Determinism: same (state, plan, seed) gives an identical event log; different seeds produce different logs across a fixed corpus.
- Chain-depth cap: fuzz 10,000 seeded plans per target; assert every heist terminates and no beat exceeds the cap.
- Content integrity: every complication has at least one counter reachable by some crew/gear combination; every tag it emits is consumed or terminal; every trait id referenced exists; no orphan text keys.
- Bot playtests: a random-plan bot and a greedy-plan bot run 1,000 jobs per target; the test asserts a clean-heist rate and average payout stay inside target bands (catches a broken balance before a human does).
- Save round-trip mid-playback and old-save tolerance; achievements earned from event lists.
- Live checks via the shared `hub-dev-server`: tap-to-place and drag at 375px, keyboard-only planning, text scale, reduce motion.

## 11. Baseline checklist pointer (what differs)
Use `overclock-plan.md` sections 4 and 5, slug `heist-committee`. Specifics:
| Item | Note |
|---|---|
| Save | `get_state()` includes `job` with the RNG state; mid-playback resume must replay identically |
| Confirm dialog | Start Heist (irreversible), Abandon job, Reset career |
| Mobile dock | The action tray and Start Heist button; HUD shows cash, heat, beat |
| Colorblind | Crew roles by shape + letter, outcomes by icon + word |
| Story | Shared story toggle hides banter/flavor only; `story-chapters.js` can carry a "career" thread (the Committee's own subplot) |
| Real-world examples | Not applicable: fiction. The convention (facts read from a live named source) is never triggered; state that in the info panel |
| Light theme | Uses `shared/theme-light-games.css`; verify the timeline cell contrast in both themes |
| Leaderboard | Optional later, opt-in, via `app/leaderboards.py` and `shared/leaderboard.js` |
| Info panel | A short "How the plan works" panel via `shared/info-page.css` (no sources page) |

## 12. Milestones
Commit + tag each: `git commit -m "Milestone N: <name>"`, `git tag heist-committee-milestone-0N`. Milestones 1-4 ship a complete, playable game.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Engine core | `engine.py`: data loaders, `resolve_beat`, tags/chain/counters, seeded RNG, text-only harness that runs one heist and prints the log. Tests: determinism, chain-depth cap | Not started |
| 2 | Plan UI | Recruit cards, timeline grid, action tray, tap-to-place + drag, live validation panel, pair-rule previews | Not started |
| 3 | Playback + payout | Beat-by-beat playback, log lines, payout screen, chain diagram, write-up generator | Not started |
| 4 | Launch content | 3 targets, 12 crew, 20 complications, 3 gear, contract board and scouting. **First complete, playable game** | Not started |
| 5 | Career and meta | Cash, reputation, relationships, unlocks, rotating pool by career seed, more targets and crew (5 / 20 / 60) | Not started |
| 6 | Standard kit | Save widget (mid-playback resume), `settings.js`, confirm dialogs, tutorial, mobile dock/HUD, info panel, changelog, feedback | Not started |
| 7 | Achievements + story | 14 achievements, panel/toast, story toggle wiring, crew banter, career thread | Not started |
| 8 | Balance and bots | Bot playtests, tune bands, second complication pass, colorblind and 375px audit | Not started |
| 9 | Hub integration | Title card, thumbnail, favicon, `sw.js`, manifests, root CLAUDE.md row, dev logs, tag | Not started |
| 10 | Daily Job (optional) | Date-seeded job, archive, opt-in leaderboard board | Not started |

## 13. Risks
- **Drag UI on touch** is the one new interaction. Mitigation: tap-to-place is first-class; prototype at Milestone 2 before content.
- **Chain reactions feeling arbitrary.** Mitigation: every line states its cause; chain diagram; bot tests for termination.
- **Content volume.** 60 complications is a lot to write well. Mitigation: launch with 20; tags make each entry cheap because the combinatorics come from data, not code.
- **Balance blindness with a hidden pool.** Mitigation: scouting always reveals at least the top-weight complication; bot bands.
- **Scope creep into a management sim.** Mitigation: no base building, no per-crew leveling beyond relationships.

## 14. Open questions for the user
1. Cozy-caper tone (recommended: warm, comedic, nothing harmful) or a darker noir-comedy voice?
2. Should a Daily Job (same target for everyone by date) be part of launch or a later add-on (recommended: later, Milestone 10)?
3. Crew named after real archetypes only (invented names, recommended) or any nickname bank you want used?
