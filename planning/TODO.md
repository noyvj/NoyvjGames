# Site-Wide TODO (round 3)

**Progress: 503/1095 items checked off (45.9%).** Recompute with `grep -c "^\s*- \[[ x]\]" planning/TODO.md` (total) and the same with `\[x\]` (done) as items land.

Built from your answers in `planning/IMPROVEMENT-IDEAS-ROUND-3.md` (Part 4). Every Round 3 section is now answered (2026-10-07 below the Warframe section); earlier this list held only: **GB** (Canopy gamified), **M** (new games), **N** (seasonal events), **O** (Trade Empire and Continuum replayability), **P/Q/S/T** (Signal, Undersleep, Overclock, Last Line open questions), **X** (Warframe tracker) and **R** (returning later). GC-GI, A-L, U, Z and Y are unanswered and wait for you. The previous list is archived at `planning/todo-archive/260914_260927.md`; anything from it that was moved here is marked "moved" there.

Rules carried over: "yes" items are here, "later" items are parked in `planning/LATER.md`, "no" items are dropped, questions only you can answer are in `planning/FOR-YOU.md`. Every real-world fact in a feature is read from a live source and named on screen. Nothing is pushed by the AI sessions.

---

## Standing decisions from your Round 3 answers (apply everywhere)

- **Audio:** not being considered yet (R1-R8 all dropped for now), but raise it again in every ideas document until the user says yes (user, 2026-10-06).
- **Roguelikes and card games:** you do not like them, so anything in that genre (Canopy Expedition mode, Overclock) is built on my judgment without expecting your input, kept honest and fun rather than polished to your taste.
- **Level select:** for games that are getting complex, add a level select where every 5 levels is either a game mode or a new mechanic; mechanics that do not belong in the base game (Canopy's poachers and storm fronts) live there.
- **Fast-forward and pause:** wanted in most games that are not turn-based.
- **Skill-tree progression:** where a game has meta-progression (Canopy's Seed Vault, idle crews), build it as a skill tree.
- **Leaderboards:** build them generally, always opt-in (the leaderboard backend from tonight is the base).
- **Events (N):** real big-date events (Christmas, Halloween, New Year, Easter, Hanukkah, Thanksgiving, 4th of July, Valentine's Day and other big ones, internationally inclusive), doable within about 15 minutes of starting a game, with a temporary date-tied stand-in event for games with no natural fit.
- **New-game plan questions (you, 2026-10-07: "yes", go with the recommendations):** Undersleep has no first-launch gate, only a permanent footer line, the daily check-in starts hidden ("Just play") and journal data stays on the device with manual export and import; Lighthouse never shows a death on screen; Pocket Bazaar counts customer patience in beats, not seconds; Signal's Wide and Big Sky boards stay practice-only for now.
- **Multiplayer (you, 2026-10-07):** the level of multiplayer is my call, any ghost or run summary is opt-in, two-player games let the player choose friend-only or open (friend-only recommended), moderation is you plus me if possible; client-trusted versus verified scores is still open (FOR-YOU 5).
- **QA section (you, 2026-10-08):** do NOT work on section QA (code review, bug check, bloat cleanup, load time passes) until closing-tasks time; focus on the feature sections first. Bugs you report (UX, LC-1 style) are still fixed when reported.

---

## W. Cross-game groundwork these answers need (build once, reuse)

- [x] W-1: **Level select framework** (shared component plus per-game level list): a level-select screen where every fifth level is a game mode or a new mechanic; used first by Canopy (GB-13, GB-15, GB-16) and then offered to other games that are getting complex. (Built 2026-10-08 as shared/level-select.js, documented in planning/SHARED-COMPONENTS.md; each game still needs its own level list, GB-13/15/16.)
- [x] W-2: **Fast-forward (1x/2x/4x) and pause** for the real-time (ticking) games: audit which games tick (SOL, Canopy, Tide? Continuum has speed controls already) and add the same control to those that lack it, without touching tick math.
- [x] W-3: **Skill-tree component** (shared UI and data shape) for meta-progression, first user Canopy's Seed Vault and ranger crews (GB-10, GB-26), later Trade Empire's charter tree (O-1). (Built 2026-10-08: shared/skill-tree.js, .css and a Python mirror skill_tree.py; wiring into Canopy and Trade Empire is still open.)
- [x] W-4: **Seasonal events groundwork** (`shared/seasonal-events.js` per Round 3 section N item 11): date-window check, flavour overrides, banner, badge grant through the achievements path, no new backend. (Built 2026-10-08 as shared/seasonal-events.js and .css with hub-contract badge ids; N-2 needs one host game to wire it in.)
- [x] W-5: **General opt-in leaderboards**: extend `app/leaderboards.py` boards beyond the three built tonight, and a shared widget entry per game (the shared `leaderboard.js` already exists); used by Canopy's community plot (GB-19), Last Line and Signal. (Built 2026-10-08 on branch `cloud/leaderboards-w5` as `app/boards.py` plus `NoyvjLeaderboard.addBoard` in shared/leaderboard.js, documented in planning/SHARED-COMPONENTS.md section 4; no game is wired yet and the backend needs the owner's push to deploy.)
- [x] W-6: **Multiplayer scoping document** (R-39): write `planning/MULTIPLAYER-SCOPING.md` covering what the parked community items need (shared coastline, mutual aid, peer-city ghost, 1v1 modes such as Canopy's rival company), so you can decide the pass.

---

## GB. Canopy, gamified (all 30 answered)

- [ ] GB-1: Wildfire season (opt-in via the difficulty select).
- [x] GB-2: Golden seedling pop-up.
- [ ] GB-3: Expedition mode (roguelike run of 12 seasons with boons and a shareable seed), built as a separate game mode on my judgment.
- [x] GB-4: Tend action with cooldown (hotkey T).
- [ ] GB-5: Neighbour synergy layout puzzle.
- [ ] GB-6: Species on replant (pioneer pine, hardwood oak, orchard).
- [ ] GB-7: Blight in monocultures (needs GB-6).
- [x] GB-8: Hidden Heart Tree secret.
- [x] GB-9: Ranger contracts board.
- [x] GB-10: Seed Vault meta-progression (skill-tree style, per W-3).
- [x] GB-11: Fast-forward toggle (1x/2x/4x) plus pause (per W-2).
- [ ] GB-12: Rival logging company, as a possible 1v1 game mode (design it as a mode; park the 1v1 pairing on W-6).
- [x] GB-13: Poacher whack-a-mole, as a level/mode via the level select (not in the base game).
- [x] GB-14: Forest name and adopted-tree nickname with log narration.
- [x] GB-15: Storm front events, as a level/mode via the level select.
- [x] GB-16: Forest spirit narrator, as a story level.
- [x] GB-17: Challenge run set (Pacifist, Scorched Start, Sprint, No-Highland) with badges.
- [x] GB-18: Undo window after Clear.
- [ ] GB-19: Daily community forest: everyone's play waters one big community plot, with a shared "best day" and an opt-in investment leaderboard (uses the community pools backend from tonight and W-5).
- [x] GB-20: Rare conditional wildlife in the wildlife log.
- [ ] GB-21: Timber gambler clear-cut option.
- [x] GB-22: Standing-value milestone celebrations (1k, 2.5k, 5k, 10k), also as achievements if they are not already.
- [x] GB-23: Weather reads on the grid (rain shimmer, drought tint).
- [ ] GB-24: Wetland/mangrove tidal puzzle (extends the Wetland Forest built as B1; share the tide logic with Tide).
- [ ] GB-25: Stakeholder faces (named recurring characters with moods and friendship perks).
- [x] GB-26: Idle/automation ranger crews, built into a skill tree (per W-3).
- [x] GB-27: Chain bloom effect.
- [x] GB-28: Forest Almanac collection page.
- [ ] GB-29: Carbon-credit market minigame.
- [x] GB-30: Perfect Season streak.

---

## M. New games (groundwork plans first; a plan is `planning/<game>-plan.md`)

- [x] M-1: Heist Committee: write the groundwork plan (turn-based crew planning on a timeline), then build it (M-1b).
- [x] M-2: Lighthouse: write the groundwork plan (cozy keeper idle game; a constant unease, as if it might turn into a horror game at any moment, but it never does), then build it (M-2b).
- (M-3 Cryptid Hunt dropped: you do not like roguelikes or card-game styles.)
- [x] M-4: Pocket Bazaar: write the groundwork plan (fast merge-and-fulfil; explicitly no energy limits and no microtransactions), then build it (M-4b).
- [x] M-5: Dead Reckoning: write the groundwork plan (navigation puzzle), then build it (M-5b).

**The four builds below were split into one item per milestone (2026-10-08). They live in new folders, so they cannot collide with Noy2's areas; each ends with one BLOCKED ON NOY2 milestone holding every hub and shared-file registration step. The twelve plan questions (He1-3, Li1-3, Pb1-3, Dr1-3) are answered: you answered all twelve on 2026-10-08: yes to every recommendation (cozy caper tone, Daily Job later, invented crew names; no ship ever lost, eerie details default on, plan's dread techniques; patience in beats, no real-time Rush mode, Daily Market later; full plan up front, two-ship chart later, no celestial navigation), with one note: a missing ship for drama may come later (in LATER).**

**Heist Committee** (`planning/heist-committee-plan.md`; code in a new `games/heist-committee/`; commit + tag each milestone as `heist-committee-milestone-0N`; milestones 1-4 ship a complete, playable game)
- [x] M-1b-1: Milestone 1, Engine core: `engine.py` data loaders, `resolve_beat`, tags/chain/counters, seeded RNG, text-only harness that runs one heist; tests for determinism and the chain-depth cap.
- [x] M-1b-2: Milestone 2, Plan UI: recruit cards, timeline grid, action tray, tap-to-place plus drag, live validation panel, pair-rule previews (prototype the touch interaction here, before content).
- [ ] M-1b-3: Milestone 3, Playback + payout: beat-by-beat playback, log lines, payout screen, chain diagram, write-up generator.
- [ ] M-1b-4: Milestone 4, Launch content: 3 targets, 12 crew, 20 complications, 3 gear pieces, contract board and scouting. First complete, playable game.
- [ ] M-1b-5: Milestone 5, Career and meta: cash, reputation, relationships, unlocks, rotating pool by career seed, more targets and crew (5 / 20 / 60).
- [ ] M-1b-6: Milestone 6, Standard kit: save widget with mid-playback resume, `settings.js`, confirm dialogs, tutorial, mobile dock/HUD, info panel, changelog, feedback.
- [ ] M-1b-7: Milestone 7, Achievements + story: 14 achievements, panel and toast, story toggle wiring, crew banter, career thread.
- [ ] M-1b-8: Milestone 8, Balance and bots: bot playtests, tune bands, second complication pass, colorblind and 375px audit.
- [ ] M-1b-9: Milestone 9, Own-folder wrap-up: favicon `icons/favicon-heist-committee.svg`, Desktop boot (`pc-config.json`, its own `pc.html` via a scratch `build("heist-committee", cfg)` call), the game's CLAUDE.md milestone table, dev logs, tag. Everything inside the game folder, so no waiting.
- [ ] M-1b-10: Milestone 10, Daily Job (optional): date-seeded job, archive, opt-in leaderboard board. Only if FOR-YOU He2 says to build it.
- [ ] M-1b-11: Milestone 11, BLOCKED ON NOY2 (hub registration): the shared registration that must wait until Noy2 releases the hub and shared files: root `index.html` title card and tags, `style.css` thumbnail, `script.js` entries, `sw.js` precache (own game files plus `pc.*`) with a `SW_VERSION` bump, `offline-manifest.json`, `game-manifest.json` / `game-added.json` / `game-last-updated.json` / `game-roadmap-data.json` (rerun the scripts), `game-sessions.json`, `achievements.html`, `leaderboards.html` if it has a board, `admin.html`, `shared/site-settings.js`, `sitemap.xml`, `share/meta` and `share/jsonld` cards (`scripts/generate-share-cards.py`), `scripts/perf-budget.json`, the hub regression and smoke tests (`shared/tests/smoke_support.py`, `test_smoke_everything.py`), the root `CLAUDE.md` games table row, and a check that the game works with Noy2's finished save widget and snapshots. Then run the shared test suite and `scripts/generate-pc-pages.py --check`.

**Lighthouse** (`planning/lighthouse-plan.md`; code in a new `games/lighthouse/`; commit + tag each milestone as `lighthouse-milestone-0N`; milestones 1-4 ship a complete, playable game)
- [x] M-2b-1: Milestone 1, Sim core: deterministic weather and ship generators, tick `step()`, oil/brightness/clockwork/structure/energy, text harness that plays a night; tests for determinism and pause/fast-forward invariance.
- [ ] M-2b-2: Milestone 2, Night UI: SVG scene, beam, ship silhouettes, evening plan panel, morning report, speed/pause controls.
- [ ] M-2b-3: Milestone 3, Day loop + upgrades: repairs, supplies, supply boat, upgrades, seasons, forecast.
- [ ] M-2b-4: Milestone 4, Complete Quiet mode: one year to completion, endless continue, save widget, settings, confirm dialogs. First complete, playable game (no story layer).
- [ ] M-2b-5: Milestone 5, Cast, letters, gifts: 12 sailors (6 is acceptable if the schedule needs it), letter panel, gifts, room scene, story toggle.
- [ ] M-2b-6: Milestone 6, The Unease: unease meter, odd-detail techniques, six mysteries (three if needed) with the dread-ledger tests, Eerie details setting, content note; prototype the first mystery before writing all of them.
- [ ] M-2b-7: Milestone 7, Standard kit: tutorial, mobile dock/HUD, changelog, info panel, feedback, light theme, colorblind audit.
- [ ] M-2b-8: Milestone 8, Achievements + polish: 16 achievements, panel and toast, copy lint, perf test, balance bots.
- [ ] M-2b-9: Milestone 9, Own-folder wrap-up: favicon `icons/favicon-lighthouse.svg`, Desktop boot (`pc-config.json`, its own `pc.html`), the game's CLAUDE.md milestone table, dev logs, tag. Everything inside the game folder, so no waiting.
- [ ] M-2b-10: Milestone 10, BLOCKED ON NOY2 (hub registration): the shared registration that must wait until Noy2 releases the hub and shared files: root `index.html` title card and tags, `style.css` thumbnail, `script.js` entries, `sw.js` precache (own game files plus `pc.*`) with a `SW_VERSION` bump, `offline-manifest.json`, `game-manifest.json` / `game-added.json` / `game-last-updated.json` / `game-roadmap-data.json` (rerun the scripts), `game-sessions.json`, `achievements.html`, `leaderboards.html` if it has a board, `admin.html`, `shared/site-settings.js`, `sitemap.xml`, `share/meta` and `share/jsonld` cards (`scripts/generate-share-cards.py`), `scripts/perf-budget.json`, the hub regression and smoke tests (`shared/tests/smoke_support.py`, `test_smoke_everything.py`), the root `CLAUDE.md` games table row, and a check that the game works with Noy2's finished save widget and snapshots. Then run the shared test suite and `scripts/generate-pc-pages.py --check`.

**Pocket Bazaar** (`planning/pocket-bazaar-plan.md`; code in a new `games/pocket-bazaar/`; commit + tag each milestone as `pocket-bazaar-milestone-0N`; milestones 1-4 ship a complete, playable game)
- [x] M-4b-1: Milestone 1, Board engine: `board.py` merge rules, cascades, legal-move solver, seeded RNG, text harness; tests for merges and no soft-lock.
- [x] M-4b-2: Milestone 2, Board UI: 5x6 grid, crates, drag plus tap-tap plus keyboard, Sell/Broom, merge highlights (prototype at 375px before customers).
- [x] M-4b-3: Milestone 3, Customers and orders: queue, patience counted in beats, delivery, payout, 4 archetypes, order generator with a reachability test.
- [x] M-4b-4: Milestone 4, Market day loop: day start and summary, coins, stall upgrades, a 10-day campaign, 3 festivals. First complete, playable game.
- [x] M-4b-5: Milestone 5, Combos, streaks, festivals: order combo, cascade bonus, all 6 festivals with previews, personal-best badges.
- [x] M-4b-6: Milestone 6, Standard kit + pledge tests: save widget, settings, confirm dialog, tutorial, mobile dock/HUD, changelog, info panel with the pledge list, feedback, and the pledge tests (no energy, no premium currency, no timers pushing spending).
- [x] M-4b-7: Milestone 7, Achievements + story: 14 achievements, panel and toast, regulars, story toggle wiring.
- [x] M-4b-8: Milestone 8, Own-folder wrap-up: favicon `icons/favicon-pocket-bazaar.svg`, Desktop boot (`pc-config.json`, its own `pc.html`), the game's CLAUDE.md milestone table, dev logs, tag. Everything inside the game folder, so no waiting.
- [ ] M-4b-9: Milestone 9, Daily Market (optional): date-seeded day, archive, opt-in leaderboard board. Only if FOR-YOU Pb3 says yes.
- [ ] M-4b-10: Milestone 10, BLOCKED ON NOY2 (hub registration): the shared registration that must wait until Noy2 releases the hub and shared files: root `index.html` title card and tags, `style.css` thumbnail, `script.js` entries, `sw.js` precache (own game files plus `pc.*`) with a `SW_VERSION` bump, `offline-manifest.json`, `game-manifest.json` / `game-added.json` / `game-last-updated.json` / `game-roadmap-data.json` (rerun the scripts), `game-sessions.json`, `achievements.html`, `leaderboards.html` if it has a board, `admin.html`, `shared/site-settings.js`, `sitemap.xml`, `share/meta` and `share/jsonld` cards (`scripts/generate-share-cards.py`), `scripts/perf-budget.json`, the hub regression and smoke tests (`shared/tests/smoke_support.py`, `test_smoke_everything.py`), the root `CLAUDE.md` games table row, and a check that the game works with Noy2's finished save widget and snapshots. Then run the shared test suite and `scripts/generate-pc-pages.py --check`.

**Dead Reckoning** (`planning/dead-reckoning-plan.md`; code in a new `games/dead-reckoning/`; commit + tag each milestone as `dead-reckoning-milestone-0N`; milestones 1-4 ship a complete, playable game)
- [x] M-5b-1: Milestone 1, Sim core: `sim.py` vectors, current zones, leeway, hazard intersection, tracks, scoring, text harness; tests for determinism, hazards, vectors.
- [x] M-5b-2: Milestone 2, Chart SVG: chart renderer (grid, land, hazards, current arrows, scale, rose), one hard-coded chart, static estimated track from a hard-coded plan.
- [x] M-5b-3: Milestone 3, Plan and sail: leg editor (numeric steppers and quick-turn buttons), live estimated track, Sail, animated true track, reveal overlay with error ribbon and score. Playable slice.
- [ ] M-5b-4: Milestone 4, Campaign chapters 1-2: 12 authored charts (open water, wind), stars, retry, par-plan reveal, chart validator tests. First complete, playable game.
- [ ] M-5b-5: Milestone 5, Fixes and watch-by-watch: landmarks, bearing fixes, leg-at-a-time mode, chapter 3.
- [ ] M-5b-6: Milestone 6, Fog, tides, compass error: chapters 4, 5 and 7, tide tables, uncharted hazards.
- [ ] M-5b-7: Milestone 7, Two ships: multi-ship plan and sim, collision events, chapter 6. Do this later rather than at launch unless FOR-YOU Dr2 says otherwise.
- [ ] M-5b-8: Milestone 8, Practice generator: seeded chart generator, solvability fuzz, shareable seeds.
- [ ] M-5b-9: Milestone 9, Standard kit: save widget, settings, confirm dialogs, tutorial, mobile dock/HUD, changelog, info panel with sourced facts and the abstraction disclaimer, feedback, light theme, colorblind audit.
- [ ] M-5b-10: Milestone 10, Achievements: 14 achievements (`achievements.json`), panel and toast, `achievements_earned` in the save state, favicon `icons/favicon-dead-reckoning.svg`, Desktop boot (`pc-config.json`, its own `pc.html`), the game's CLAUDE.md milestone table, dev logs, tag. All inside the game folder.
- [ ] M-5b-11: Milestone 11, Daily Chart (optional): date-seeded chart, archive, opt-in leaderboard board. Only if wanted later.
- [ ] M-5b-12: Milestone 12, BLOCKED ON NOY2 (hub registration): the shared registration that must wait until Noy2 releases the hub and shared files: root `index.html` title card and tags, `style.css` thumbnail, `script.js` entries, `sw.js` precache (own game files plus `pc.*`) with a `SW_VERSION` bump, `offline-manifest.json`, `game-manifest.json` / `game-added.json` / `game-last-updated.json` / `game-roadmap-data.json` (rerun the scripts), `game-sessions.json`, `achievements.html`, `leaderboards.html` if it has a board, `admin.html`, `shared/site-settings.js`, `sitemap.xml`, `share/meta` and `share/jsonld` cards (`scripts/generate-share-cards.py`), `scripts/perf-budget.json`, the hub regression and smoke tests (`shared/tests/smoke_support.py`, `test_smoke_everything.py`), the root `CLAUDE.md` games table row, and a check that the game works with Noy2's finished save widget and snapshots. Then run the shared test suite and `scripts/generate-pc-pages.py --check`.


---

## N. Seasonal events (redo the list around real big dates)

- [x] N-1: Redo Round 3 section N with real big-date events per your comment (Christmas, Halloween, New Year, Easter, Hanukkah, Thanksgiving, 4th of July, Valentine's Day, more, internationally inclusive), each finishable in about 15 minutes, with a temporary date-tied stand-in for games with no natural fit.
- [ ] N-2: Build the groundwork (W-4) and the first event end to end on one game.
- [ ] N-3: In the next round's M section, list games that could easily host a mode fitting each big event.

---

## O. Replayability follow-up

**Trade Empire**
- [x] O-1: Charter renewal at the endgame, with inherited advantages chosen through a research tree instead of picking a single one (per your note; supersedes the one-node idea).
- [x] O-2: Founding-conditions variety on renewal.
- [x] O-3: Lifetime ledger that survives renewals.
- [x] O-4: Opt-in harder charter after the first endgame.

**Continuum**
- [x] O-5: "Found a New Settlement" control (confirm-gated, archives the current one).
- [x] O-6: A "Found a new settlement" button beside each archived entry.
- [x] O-7: Founder's legacy carryover.
- [x] O-8: A fourth starting scenario unlocked after reaching Space Age once.

---

## P. Signal (daily deduction puzzle; plan in `planning/signal-plan.md`)

Decisions from your answers: theme retro radio-room; UTC daily reset with an archive so past puzzles can be played; a non-daily endless practice mode; launch date not tied to a special day; Option A "Triangulate" with some bigger-board modes. Python vs JS: you want Python as far as possible but would not make the call, so it is my call: Pyodide with an instant HTML shell and a lazy engine load so the first paint is immediate.

- [x] P-1: Build Signal to the plan's milestones with these decisions (one checkbox per milestone below).
- [x] P-1a: Engine, daily seed, archive of past puzzles.
- [x] P-1b: UI, retro radio-room theme, share text.
- [x] P-1c: Endless practice and bigger-board modes.
- [x] P-1d: Achievements, settings, tests, hub card, changelog.

## Q. Undersleep (plan in `planning/undersleep-plan.md`)

Decisions: cozy tone, "Unpacking"-esque; multiple characters, with a story mode where several characters' stories interconnect (a low-energy shut-in while an impulsive high-energy character keeps making plans); the player picks a preset that represents "them" and still plays other characters around it; framed as a game you add personal touches to so the character feels like you, not as a journal; no extra journal tags beyond my defaults. Your Q3 ("don't know what you mean") and Q2 (how visible is stored data) are answered in `planning/FOR-YOU.md`.

- [x] Q-1: Rework the plan for the cozy, multi-character, story-mode direction (update `planning/undersleep-plan.md`).
- [ ] Q-2: Build Layer A (the game) with characters, the "you" preset and the story arcs, then the personal-touches layer (no medical framing).

## S. Overclock (space skill-tree arcade game, reframed from a roguelike; plan in `planning/overclock-plan.md`)

You chose space and delegated the rest (you dislike the genre): I pick the gimmick, run length, meta-progression and story defaults.
- [x] S-1: Choose and document the gimmick, run length and meta-progression in the plan.
- [ ] S-2: Build it to the plan's baseline milestones.
- [ ] S-3: Reframe the plan first (you said yes, 2026-10-08): a fixed set of unlocks you choose in a skill tree, a Reactor Ring you manage, short runs scored on an opt-in leaderboard, no deck, no randomised runs and no permadeath; update `planning/overclock-plan.md` and `planning/round3-plans-index.md` before building.

## T. Last Line (turn-based tower defense; plan in `planning/last-line-plan.md`)

Decisions: the tower sits in a living hedge-maze that overgrows and dies to make a new route each wave; seeded maps; turn-based waves (time to reassess and set defences); endless mode with a best-wave leaderboard and a campaign; leaderboards generally, opt-in.
- [x] T-1: Update the plan for these decisions.
- [ ] T-2: Build it to the baseline milestones, with opt-in leaderboards (W-5).

## U. Deep Descent (plan in `planning/deep-descent-plan.md`, approved as "same as 6")
- (U-1 dropped to LATER, 2026-10-08: you said yes to moving Deep Descent out of the list because of the no-roguelike rule.)

---

## X. Warframe Build Tracker (your answers; "no" items dropped: 12 plat value, 16 lucky drop counter, 30 export/restore)

- [x] X-1: Meta build planner (one plan, one completion bar).
- [x] X-2: "This week" pin of up to three builds.
- [x] X-3: Weapon/warframe/companion crafting tracker with the import marking owned items.
- [x] X-4: Foundry timer notes with "ready at" and optional notification.
- [x] X-5: Void relic planner, including which relics carry the missing parts, which are unvaulted, and how to get them.
- [x] X-6: Credits and endo budget line per plan.
- [x] X-7: Drop-source optimizer for a whole wishlist (farming session suggestions).
- [x] X-8: Mastery-rank checklist.
- [x] X-10: "Recently completed" strip.
- [x] X-11: Forma planner, with about three suggested-build links to Overframe per item.
- [x] X-13: Trader schedule tab (Baro countdown from an entered date).
- [x] X-14: Copy wishlist as text.
- [x] X-15: Progress history chart from import snapshots.
- [x] X-17: Shared goals code for a friend.
- [x] X-18: Per-resource "I have enough" toggle.
- [x] X-19: Companion breeding/imprint planner (or manual log).
- [x] X-20: Per-resource farming tips written from research, not by hand.
- [x] X-21: Build-loadout notes.
- [x] X-22: Colour tag per build with filter (and fold in the related tagging ideas).
- [x] X-23: "What changed since my last import" diff view.
- [x] X-24: Long-term goals list.
- [x] X-25: Daily/weekly checklist tab with reset times.
- [x] X-26: Keyboard shortcuts with a "?" cheat sheet.
- [x] X-27: "Am I wasting anything?" audit.
- [x] X-28: Own-edits changelog, plus an "edited vs imported" visual difference so people can tick things off without a full import.
- [x] X-29: Endgame readiness score.
- (X-9 arcane/mod inventory tracker: "later", parked in `planning/LATER.md`.)

---

# ROUND 3, ALL SECTIONS ANSWERED (2026-10-07)

Your remaining Round 3 answers (Grid to Drift gamified, SOL to Le Champ de Mots, Cross-game Z, Hub Y) are below, one section per game, using the ids from `planning/IMPROVEMENT-IDEAS-ROUND-3.md` (e.g. `GC-3` = Grid gamified item 3, `C-3` = Grid regular item 3). Each idea was checked against the repo and the old lists first: `[x]` = already built, `[ ]` with "(partly built: ...)" = only the missing part is listed, plain `[ ]` = new. "(needs W-n)" points at the shared groundwork above; `[reframe/conflict/question: ...]` marks a line where your answer and a standing decision pull apart. Your "no" and "later" answers are left out (listed in the italic line at the end of each section; "later" items are in `planning/LATER.md`). Items that were already numbers in older sections (GB, M to X, R) were processed earlier and are not repeated here.

## A. SOL (Round 3 answers, 2026-10-07)

- [ ] A-2: Add a slim SOL toolbar strip forecasting the next System Anomaly a few ticks ahead (e.g. 'Flare in 12 ticks'); anomalies are plain timed modifiers (no contingency cards, never blocking progress), forecast is text-only under reduce motion. (you confirmed 2026-10-07: build simple timed anomalies without cards, even though A-1 was declined)
- [ ] A-3: Add SOL prestige Mutators: before each New Game+ run pick 0-3 opt-in rule twists (Thin Atmosphere: ecology decays 40% faster; One-Way Trade; Blind Governor) each raising the run's prestige-point payout; generalises the existing Challenge toggle into a dial, all easy to 100% and never luck-gated.
- [ ] A-4: Show a tiny glyph per active SOL mutator beside the prestige badge in the title and on the Stats & Share card text so screenshots show the run's rules. (needs A-3)
- [ ] A-5: Add a SOL Mission Board of rotating optional per-planet objectives (e.g. 'Terraform Mars with zero Sky Cities', 'Venus 60% terraform with ecology >= 50%'); completing one grants a permanent cosmetic-plus-small-perk Charter stamp shown in the Overview planet cards.
- [ ] A-6: Add a 'reroll mission' button to the SOL Mission Board costing a small amount of a currently-abundant resource. (needs A-5)
- [ ] A-7: Add SOL Governor Doctrines: research-unlocked per-planet if/then rule list (e.g. if ecology < 30% pause purchases and ship Water from richest planet), max 3 rules early, more via the Prestige Tree, with the Governor Report showing which rule fired; pairs with trade-route automation.
- [ ] A-8: Add a dry-run button to the SOL Doctrine editor that simulates 30 ticks headless on a copy of state and prints 'would have fired N times'. (needs A-7)
- [ ] A-9: Add a SOL Observatory meta-layer shared across prestiges: each prestige yields Survey Data, spent to unmask one more hidden anomaly on a star chart (Lagrange Points = bonus building slots, rogue comets = one-shot windfalls); a long-term collection of the map.
- [ ] A-10: Show an Observatory comet windfall in SOL as a tappable streak on the Overview that fades if ignored for a while; no idle gate, keyboard-accessible, text-only under reduce motion. (needs A-9)
- [ ] A-11: Add a SOL Scarcity Run mode: fixed daily challenge seeded from the UTC date (resource mix, ecology decay, starting planet loadout), same puzzle for everyone, completion time posted to an opt-in leaderboard. (needs leaderboard backend (exists), shared/community-pool.js)
- [ ] A-12: Show 'Today's seed' as a short pronounceable word triple (e.g. amber-orbit-7) on SOL's Stats & Share card for the Scarcity Run. (needs A-11)
- [ ] A-13: Add 3-4 SOL late-game Megaprojects (Orbital Mirror, Ring Habitat, Dyson Sail, Deep Core Tap), each needing resources from many planets at once for a game-warping perk (e.g. Sky Cities count double); building all four unlocks a secret epilogue variant.
- [ ] A-14: Show a construction progress ring per SOL Megaproject on the Overview, filled by whichever planets contribute that tick, with a text percent fallback. (needs A-13)
- [ ] A-15: Add SOL Rival Colonies: three named non-hostile AI corporations that claim Lagrange Points and push shared-market trade prices down unless the player specialises; no timers, recoverable, player may contest, ignore or partner. (needs A-9 (Lagrange Points))
- [ ] A-16: Add one-line rival ticker gossip to SOL's log (e.g. 'Helios Combine reports record Belt yields') with zero mechanical effect. (needs A-15)
- [ ] A-17: Add SOL Time Capsules: freeze current state as a named capsule (max 3), replay from it in a sandbox branch and compare outcomes; branch never counts for achievements, leaderboards or the real save.
- [ ] A-18: Add a one-click 'diff vs capsule' line in SOL showing resource and terraform gap between now and a capsule after N ticks. (needs A-17)
- [ ] A-19: Add a hidden SOL Codex of 7 cryptic clues (odd trailing sentence in each planet description) that unlock a silly secret building or fake achievement when acted on (e.g. Pluto at 0% ecology, 13 of one building, terraform Venus last); every clue must be hinted so it stays easy to 100%.
- [ ] A-20: Show a 'clues found: N/7' line in the SOL Codex hidden until the first clue is discovered. (needs A-19)
- [ ] A-21: Add SOL prestige Eras (Pioneer, Steward, Architect, Custodian) replacing the flat level counter, each re-theming the shell (palette shift, title tagline, quiet visual-only starfield tweak, no audio), toggleable and respecting light theme and reduce motion.
- [x] A-22: Add a cheeky per-planet 'Governor mood' one-liner in SOL's Governor Report that varies with personality and how much the player micromanages that planet.
- [ ] A-23: Add SOL Blueprint Swap: serialise build plan plus Doctrine list plus mutator picks into a short shareable code, importable as a ghost overlay in the Build Plan checklist; no backend. (needs A-3, A-7 for the Doctrine/mutator parts)
- [x] A-24: Add a 'copy as text spreadsheet' button to SOL's Build Plan (tab-separated step/done rows via clipboard with manual-copy fallback).
- [x] A-25: Add SOL Chain Reactions: performing the right sequence of actions across planets in a short window (e.g. dump Ice on Venus, trade Water to Earth, click Mars) triggers a small bonus, discovered by experiment, with a 'combos found' collection page and hints so it stays easy to 100%.
- [x] A-26: Add a soft SOL click-streak meter giving a very small yield bonus for staying in rhythm, with a text-only reduce-motion fallback and a Settings off switch; must never beat or replace normal play.
- [ ] A-27: Add an optional SOL Ecology Stress Test endgame arena: a one-shot scenario where a cascade of anomalies hits every planet and the player must hold combined ecology above a line using only already-set Governors/Doctrines (no clicking), scored by margin held. (needs A-7 (Doctrines), anomaly system from A-2)
- [ ] A-28: After a SOL Stress Test show a per-planet heatmap strip of when each planet's ecology dipped, with text/pattern cues (not colour alone). (needs A-27)
- [ ] A-29: Add a SOL Ghost Run mode: race a recorded replay of your personal best (or an imported friend's blueprint code) on a split track showing lead/lag in terraform percent every 25 ticks; local only. (needs A-23, A-30)
- [x] A-30: Add a SOL speedrun splits panel with a lap time per planet unlocked and a delta vs personal best (marked with +/- text as well as colour), hidden unless a 'Show timing' Settings option is on.
- [x] A-31: Add a SOL trophy-shelf strip of the most recently earned achievement badges near the top toolbar, each in SOL's gradient-glow style, plus a brief toggleable glow/particle flourish on unlock (off under reduce motion); toast stays.

*Not added: A-1 (no).*

## B. Canopy (regular ideas; the gamified batch is section GB above) (Round 3 answers, 2026-10-07)

- [ ] B-1: Add a Canopy "My Forests" library: store a compact record of every finished session (final values, playstyle badge, difficulty, grid size, the three report-card series, legacy bonus) in localStorage and let the player compare any two side by side with the existing report-card sparklines.
- [ ] B-2: Move Canopy's legacy bonus into a header chip (e.g. "+12% from your last forest") with a tooltip naming its source (last session's banked standing value) and how close it is to the +25% cap. (partly built: game.py render_legacy_bonus() shows a text line "Legacy bonus: +X% growth, from your last session's forest"; LEGACY_MAX_BONUS 0.25 cap; no chip, tooltip or cap proximity)
- [ ] B-3: Add a Canopy forest replay scrubber to the Session Summary: record periodic per-plot snapshots alongside the capped forest_log and let a slider scrub the grid through the session, plots greening and clearing in sequence, screenshot-friendly.
- [ ] B-4: Add a Canopy shareable forest image: render the final grid, playstyle badge and three headline numbers onto one canvas card (drawn in code, no generated images) with a Download PNG button beside Copy badge; no backend.
- [ ] B-5: Add a Canopy "Forest Lab" sandbox panel with sliders for soil degradation per clear, maturity speed, request frequency and season strength; sandbox sessions are clearly marked and excluded from personal bests, percentiles and leaderboards, and can be saved as harder/gentler Ranger-style variants.
- [x] B-6: Add a Canopy Settings request-interval selector (Relaxed / Normal / Frequent) that scales STAKEHOLDER_EVENT_INTERVAL_TICKS, saved and recorded with the difficulty tag so stats and percentiles stay honest.
- [ ] B-7: Finish full keyboard and screen-reader play as a shared component: an aria-live announcer (state changes, incoming requests, season shifts) plus, in Canopy, a visible grid cursor ring and Clear/Replant hotkeys (C/R); then roll the announcer/cursor pattern out to the other grid games. (partly built: index.html B16: arrow-key focus moves across #plot-grid, Enter/Space native, N selects requested plot, tiles have aria-label; T/G/U hotkeys; no C/R keys, focus ring, or aria-live announcer) (needs shared announcer module) (Partly done 2026-10-07: Canopy-local live announcer, C and R hotkeys, thicker focus ring; the shared announcer module is not built, so no other game got it.)
- [x] B-8: Add a shared high-contrast plot-state option next to text size and reduce motion: bold outlines and text glyphs (B / R / M for Canopy) on every plot tile so state reads without the green gradient; apply it to all games with state-coloured tiles, starting with Canopy. (needs shared settings component) (Canopy-local only.)
- [ ] B-9: Add a Canopy lifetime Statistics tab in the achievements-panel idiom: total plots cleared/replanted, hours played, average standing value by difficulty, playstyle badge distribution bar, best season, and per-request-type accept/decline rate, from local sessions (sandbox excluded).
- [x] B-10: Add an optional soil-quality heat overlay toggle in Canopy that recolours plot borders by remaining soil quality with numeric badges (accessible, off by default) so multi-clear damage is readable across the grid.
- [ ] B-11: Add Canopy scenario seeds: pre-made starting forests (Clear-cut Valley 60% bare, Fragmented Farmland checkerboard, Old-Growth Remnant one intact core), picked at session start, each with its own personal-best slot on the report card, reusing the plot save format. (needs optionally W-1 level select)
- [x] B-12: Extend Canopy's season indicator into a forecast strip showing the next two seasons' growth multipliers and tick countdowns (e.g. "Summer 1.05x in 12 ticks, then Autumn 0.95x"), including upcoming weather where it is deterministic. (partly built: game.py render_season_indicator() shows current season and "N ticks to <next>"; weather_at() is a pure function of tick; no multipliers or second season shown)
- [ ] B-13: Add a Canopy "Survey" pause-and-plan mode: freeze the tick, queue actions (clear, replant, decline next request), show a projected value delta using the counterfactual math, then commit all when unpaused. (needs W-2 pause)
- [ ] B-14: Turn Canopy's forest history into a sortable, filterable request-history table (plot, kind, your choice, value delta afterwards) as a "did I choose well" audit view. (partly built: Forest history panel (B3) lists forest_log entries (tick, kind, plot, text); no sortable/filterable table, no choice or value-delta columns)
- [ ] B-15: Extend the shared save widget with up to three named local forests per browser (e.g. "Ranger practice"), switchable from a small menu, each keeping its own difficulty and grid size; first use is Canopy. (partly built: shared/save-widget.js already has 3 numbered save slots for signed-in accounts plus save codes; no named local slots or switch menu for anonymous browsers) (needs shared/save-widget.js)
- [x] B-16: Extend Canopy's plot tooltip card with plot age, biodiversity rate per tick and clear count, and style it as one compact card shown on hover and focus. (partly built: index.html B8 plot tooltip (hover and focusin) via _plot_tooltip_text(): coordinates, state, value, soil %, recovery, veteran, specialist, adopted; missing age, biodiversity rate, clear count)
- [ ] B-17: Add a Canopy visual refresh: layered CSS/SVG tree sprites per plot state with gentle sway, depth shadow and seasonal foliage colours replacing flat tinted tiles, keeping the state icons; hand-drawn in code, NO generated images; sway respects reduce-motion.
- [ ] B-19: Add a Canopy long-term Forest Rank: lifetime XP from standing value, seasons survived and badge variety fills a ladder (Sapling Warden through Grove Keeper) that unlocks cosmetic badge-card frames and palette themes only, no gameplay advantage, placed under the achievements panel.
- [x] B-20: Achievement progress bars. (already built: game.py ACHIEVEMENT_PROGRESS (line ~2410) gives numeric progress lines for 12 countable achievements, rendered in the panel (~2443); one-shots deliberately plain)
- [ ] B-21: Add a Canopy interactive timeline chart available any time: larger version of the three report-card series with hover values, season bands and event markers for each clear, request, grant and specialist choice, joining forest_log with report history.
- [ ] B-22: Add a Canopy "while away" catch-up chip on tab return (e.g. "+214 value, 1 request expired") instead of silently jumping numbers, tick-speed independent.
- [ ] B-23: Add a hub-level "Climate Steward" profile that reads optional summary fields from the climate games' saves (Canopy standing value, Tide restored coastline, etc.) into one portrait; Canopy exposes its summary fields in its save state. (needs hub shell, Y/Z coordination)
- [ ] B-24: Add Canopy plot notes: right-click or long-press adds a short label (max 20 chars) to any plot, shown as a corner dot, saved with the session.
- [ ] B-25: Add a third Counter-offer option to Canopy clear-requests (e.g. clear half the plot area, or give two nearby bare plots instead) with deterministic outcomes previewed with numbers inside the existing stakeholder-relations math.
- [x] B-26: Add a Canopy Settings numbers-format dropdown (compact 1.2k, thousands separators, full precision) applied to the HUD and mobile dock.
- [ ] B-27: Add opt-in adaptive Coach hints in Canopy's report card: dismissible notes that read the session (e.g. same plot cleared 3 times in one season, soil now 55%), never block play, and replace tutorial text for returning players.
- [ ] B-28: Add a Canopy mobile bottom sheet opened by long-pressing a plot with large Clear/Replant/Adopt buttons; desktop layout unchanged.
- [ ] B-29: Add a Canopy custom grid shapes editor: paint which cells exist (island, ring, plus, river-split), save named layouts each with their own personal-best slot, kept out of standard percentiles.
- [ ] B-30: Add a Canopy performance guard: auto-throttle wildlife sprite animation and value-pop effects when the tick loop lags, with a "Performance mode" indicator in Settings and a manual override.
- [ ] B-31: Restyle Canopy's achievements panel as a forest-themed "grove wall" laid out like the plot grid, with a leaf/wildlife glyph (existing wildlife icons) per earned badge, locked ones as dim silhouettes keeping progress lines.

*Not added: B-18 (later, parked in LATER.md).*

## GC + C. Grid (Round 3 answers, 2026-10-07)

- [x] C-1: Add a run history library to Grid's Career panel: each finished run stores funds/clean-share/demand series, scenario, grade and points, listed with a stacked trend chart to compare runs.
- [x] C-2: Show on locked Grid career perks how many points away they are and the numeric effect (e.g. '+75 funds'); add levels if the tree needs next-level preview. (partly built: Perk buttons show cost and description (update_career_panel); single-level perks, no gap or numbers.)
- [x] C-3: Add a post-run 'what if' analyzer to Grid: replay the same demand and weather rolls with three canned strategies (all-renewable-early, no-retire, storage-first) and show grade and funds beside yours. (needs seeded per-run RNG (not stored today))
- [x] C-4: Add hover/focus highlighting to Grid's plant-mix chart: hovering a segment highlights that plant's row and shows its share of capacity, revenue and emissions.
- [ ] C-5: Add full keyboard and screen-reader operation to Grid: tab order through plant rows, arrow-key adjusting of build/retire, an aria-live announcement of each round's outcome, and a spoken-friendly gauge summary.
- [ ] C-6: Add a number-format and unit toggle to Grid's Settings: MW vs units, compact vs full numbers, and coloured arrows plus text for funds deltas (no hue-only cues).
- [x] C-7: Add a lifetime statistics tab to Grid: average grade per scenario, rounds survived, most-built plant, disruptions by cause and a clean-share-by-round heatmap, from the grid_career_v1 store. (needs C-1 run history)
- [x] C-8: Add a round recap line to Grid that collates scheduled maintenance, demand response, arbitrage income and weather delta into one expandable entry.
- [ ] C-9: Add a custom scenario builder to Grid: sliders for funds, plant mix, demand, growth and weather variability, saved by name and shareable as a code the save widget can import. (partly built: 4 fixed scenarios (C13/C27); no custom builder or share code.)
- [x] C-10: Add Relaxed/Standard/Operator difficulty presets to Grid: one dropdown at run start setting the existing toggles, with the preset shown in the header. (partly built: Separate toggles exist (steeper demand, weather variability, scenario); no preset dropdown or header label.)
- [ ] C-11: Add a single-line schematic to Grid: generators feeding a bus into a demand block, flow thickness by output, a battery tank for storage, animated per round, also usable as the shareable result image.
- [ ] C-12: Add checkboxes to Grid's trend graph to show or hide emissions, funds, demand and clean-share lines, keeping the best-round marker visible.
- [ ] C-13: Add up to three named local run slots to Grid for everyone (no sign-in), with a slot switcher and each slot's own scenario, reusing the save widget's serialisation. (partly built: shared/save-widget.js has 3 numbered slots for signed-in accounts only (U3) plus save codes.)
- [ ] C-14: Add a sortable fleet overview table to Grid: count, wear tiers, breakdown risk %, next scheduled maintenance and revenue per round for each plant type.
- [ ] C-15: Add a post-run round scrubber to Grid: slide through past rounds to see fleet, demand, weather and the disruption log at that round; store per-round snapshots. (partly built: Only emissions/cost/global/clean-share histories are stored per round; no fleet, demand or log snapshot.)
- [x] C-16: Add 'Reset career' to Grid behind ConfirmDialog, first offering to copy the career JSON, plus an import field to restore it.
- [ ] C-17: Add long-term operator ranks to Grid (Junior Dispatcher to Chief Engineer) from lifetime grid-hours and grades, unlocking cosmetic panel themes and a header, with no gameplay edge.
- [ ] C-18: Extend Grid's achievement progress readouts to the remaining countable achievements and show the next milestone on locked ones. (partly built: ACHIEVEMENT_PROGRESS gives readouts for 10 achievements (clean share, streak, score, maintenance, scale).)
- [ ] C-19: Add a table-view toggle to every Grid chart and gauge showing its numbers in a plain table plus a short text description of the trend.
- [ ] C-20: Add capacity and round number to Grid's sticky key-stats HUD (mobile-hud), so it shows funds, demand, capacity and round while scrolling. (partly built: shared/mobile-hud.js pins Funds, Demand, Emissions on narrow screens (index.html MobileHud.init).)
- [ ] C-21: Add an opt-in coach mode to Grid: a collapsible panel giving one plain-language observation per round from existing risk numbers, never blocking.
- [ ] C-22: Add a Grid Settings control to re-enable skipped confirmations and optionally skip retire confirmations under 20% wear while always keeping the last-unit warning. (partly built: Only last-unit retire and Finish Run confirm; shared confirm-dialog.js has a per-dialog 'don't ask again'.) [question: Premise differs: non-last retires already skip confirmation. Check what the owner wants.]
- [ ] C-23: Add an under-one-second round-advance animation to Grid (sun arc for solar, wind streaks, demand curve drawing itself), skippable in Settings and off under reduced motion.
- [ ] C-24: Add a print/copy view of Grid's operator report using shared/print-summary.css: scenario, grade, resilience and career points on one page.
- [ ] C-25: Expose Grid's best clean share, grade and resilience as a small structured summary the hub reads and shows beside Canopy and Tide results. (needs hub work, Z1 aggregate endpoint)
- [x] C-26: Show a 'repaired N fields' note in Grid's changelog panel when a loaded save is missing fields, instead of silently defaulting. (partly built: load_state() merges plant dicts silently (_merge_plant_dict, audit fix); no visible note.)
- [ ] C-27: Add a sandbox balance panel to Grid: sliders for cost decay, breakdown chance, demand growth and revenue per unit, tagged Sandbox and excluded from career points and percentile stats.
- [ ] C-28: Add a colour theme picker to Grid's trend graph and plant-mix chart (default, high-contrast, grayscale with pattern fills). (partly built: Trend cost line has a dash pattern (colorblind audit); bars have name labels, no pattern fills or picker.)
- [ ] C-29: Add an instant-replay share code to Grid: compress a run's key decisions and seeds into a string that plays back in a read-only viewer ending with the grade. (needs seeded per-run RNG, C-1)
- [ ] C-30: Add performance and mobile polish to Grid: batch DOM updates per round, lazy-render log panels and show a light 'loading round' state during slow Pyodide moments.
- [ ] C-31: Restyle Grid's achievement cards in the skyline-HUD look: earned badges as small lit-building icons, with a brief 'power up' flash on unlock (reduced motion safe). (needs GC-8 skyline palette)
- [x] GC-1: Add a deterministic 'Project' branch to Grid's upgrade tree: named permanent modifiers you pick and buy on purpose (Wind sites cost -15%, R&D grant, storage subsidy), tied to the policy lever and cost curve. No random draws, no discards. (needs W-3) [reframe: Owner dislikes deck-builders: card draw dropped. Overlaps GC-2b and GC-5 (same single tree).]
- [x] GC-2b: Build Grid's career upgrade tree (W-3) with a starting-loadout branch: pick a deterministic start option per run (Old Coal Contract, Storage Startup, Diplomatic Immunity) and fold the 4 existing perks in as first nodes. No random mutators. (needs W-3) [replacement: Replaces roguelike relics/mutators with an upgrade tree. GC-1, GC-5, GC-11, GC-16 add branches to this same tree.]
- [ ] GC-3: Add an optional 24-hour dispatch puzzle to each round in Grid: a solar hump, wind wobble and evening peak timeline where you drag plants into merit order (cheapest first, batteries at the peak); better dispatch raises revenue and cuts brownouts.
- [x] GC-4: Give each built plant in Grid a random nickname ('Old Smoky', 'Sunny Delight'), and play a short eulogy line plus a demolition puff when the last coal plant is retired; no change to the math.
- [ ] GC-5: Extend Grid's career upgrade tree with new plant types unlocked by career points (offshore wind, geothermal, small modular nuclear, gas with capture, green hydrogen), each with its own cost/capacity/risk quirk. Grid-specific, not shared with other games. (needs W-3)
- [ ] GC-6: Add ribbon-cutting juice to Grid's Build button: a quick flash and pop-in on the plant row, a bigger one for the first plant of each type, and a skyline light-up at 25/50/75% clean share; all under reduced motion and a Settings effects toggle.
- [ ] GC-7: Add a siting map to Grid: building solar/wind/hydro means picking a tile on a small emoji-tile regional map (ridge = wind, desert = solar, river = hydro) where tile quality changes capacity factor and nearby cities give NIMBY pushback.
- [ ] GC-8: Add a city skyline HUD strip to Grid: buildings light up as demand is met, flicker/dim during brownouts, with a smoky haze that thickens with emissions; give a reduced-motion static version.
- [ ] GC-9: Add a ghost run to Grid: overlay your best previous run's clean-share and funds series as a translucent line on the trend graph, with a round-by-round ahead/behind delta; store the per-run arrays in localStorage.
- [ ] GC-10: Add named boss rounds to Grid every 8th round (Heatwave, Polar Vortex, Dry Summer) with a one-round-ahead preview and a set demand spike or output penalty; beating it gives a big reward (funding bonus, a cost discount, an achievement). [reframe: 'Free card' reward replaced by a discount/funds/achievement because cards are dropped. Overlaps GC-24 storms.]
- [x] GC-11: Add a peek-forecast to Grid: pay a small fee to reveal next round's weather roll and disruption chance before building, unlocked as a meteorology branch of Grid's upgrade tree. (needs W-3)
- [ ] GC-12: Add a handcrafted puzzle campaign to Grid: 10-12 short scenarios with fixed starts and goals (e.g. Island grid: 6 rounds, 300 funds, 80% clean, no brownout) rated 1-3 stars on par rounds and budget; shareable results. (partly built: 4 scenarios exist (Standard/Coal-heavy/Greenfield/Emergency, C13/C27) but no goals, par or stars.) (needs W-1 (optional))
- [ ] GC-14: Add coal town loyalty to Grid: retiring fossil plants shifts a Town Support meter; keep it up with retraining or phased-closure funding, and a crash triggers protest events that block builds; tie it to the resilience score.
- [x] GC-15: Add a Perfect Round combo to Grid: consecutive rounds with zero disruptions and demand fully met build a revenue multiplier shown as a streak flame, extending the existing clean-streak counter.
- [ ] GC-16: Add an autopilot manager to Grid: an auto-builder following a player-set priority list (e.g. build cheapest renewable when funds > X), with smarter managers bought with career points as nodes in the upgrade tree; uses the GC-17 stop-on-event advance. (needs W-3, GC-17)
- [x] GC-17: Add an 'Auto-advance 5 rounds' button to Grid that stops at the first disruption, breakdown or policy offer.
- [ ] GC-18: Add an energy market to Grid: a spot price that random-walks each round, plus long-term supply contracts that lock a price for N rounds with a delivery bonus; contracts versus riding the spot price.
- [ ] GC-19: Add 'Gridley', a wry one-line commentary voice on round outcomes to Grid, toggled off in the Settings panel.
- [ ] GC-20: Add an R&D lab to Grid: invest funds in any renewable for escalating odds of a breakthrough that permanently improves its cost decay or capacity; dead ends refund part of the spend; show odds and a guaranteed-breakthrough counter.
- [x] GC-21: Add a free one-step 'undo last build' within the same round to Grid, disabled by an opt-in Ironman toggle where every action is final (with a badge for Ironman runs).
- [ ] GC-22: Extend Grid's regional grid into neighbour trading: an AI grid whose surplus or shortfall varies each round, with export/import at a negotiated price and a limited interconnector capacity. (partly built: C3 regional grid exists: one-way 'Connect a regional grid' that buys surplus (see CLAUDE.md, games/grid).)
- [ ] GC-24: Add storm-prep rounds to Grid: severe weather forecast a few rounds ahead with a track and damage radius, and spend funds to harden plants (wear reset, insulation, backup) before it lands.
- [x] GC-25: Add occasional surprise grants to Grid: a small funding windfall or inspection fine as a two-button accept/decline choice.
- [x] GC-26: Extend Grid's personal bests in the Career panel with fewest rounds to 90% clean and longest clean streak, and a 'new record!' flash. (partly built: Career panel shows best_score and best_grade (career_panel_lines); no record flash.)
- [ ] GC-27: Add an opt-in challenge set to Grid: Net-Zero Sprint (90% clean in 20 rounds), Coal Forever (A grade with 2 coal plants), Frugal (never spend over 300 funds), Nuclear Renaissance (win with no wind or solar), each with a badge and its own saved best.
- [ ] GC-28: Add an animated needle balance gauge for supply vs demand to Grid: wobbles and settles, spikes into a red brownout zone, and clicks when matched; shake and effects toggleable, off under reduced motion.
- [ ] GC-29: Add a daily seeded grid to Grid: the date fixes demand shape, weather rolls and the event schedule, with your score next to your own history; friend comparison later via leaderboards. (needs W-5, seeded per-run RNG (none stored today; game.py uses random.random)) [question: Owner asked: no friend system exists (accounts, opt-in leaderboards, community pools only; friends not scoped). Say so and offer the leaderboard route.]

*Not added: GC-2 (no); GC-13 (later, parked in LATER.md); GC-23 (later, parked in LATER.md); GC-30 (no).*

## GD + D. Tide (Round 3 answers, 2026-10-07)

- [x] D-1: Add a Harbor Ledger panel to Tide: a sortable table of every season this session (funds, acidity, fish yield, damage, rows dry, population, tier, investments) with a small chart per column, reading the existing per-season data.
- [x] D-2: Add a session library to Tide: finished sessions saved locally (scenario, lag mode, storms, final score) and any two overlaid on the acidity/fish-yield graphs as solid vs dashed lines.
- [ ] D-3: Add a shareable session code to Tide: a finished run exports a compact code (scenario, per-season choices, outcome) that a friend pastes into Load Ghost to view as a read-only overlay or step-through against their own run.
- [x] D-4: Add a season scrubber to Tide: a slider under the coastline to view any earlier season (grid, meters, tier badges, heritage) read-only without altering the live run.
- [ ] D-5: Add a Tide Workshop to Tide: opt-in sliders for starting funds, lag length, sea-level rate, surge size and fish sensitivity with a live difficulty rating and a 'custom rules' label; hard lag and the three scenarios become presets.
- [x] D-6: Add a season planner to Tide: a Plan tab to stage 3 to 5 seasons of allocations and see projected acidity, fish yield and rows-at-risk curves, never writing to game state until Commit season 1.
- [x] D-7: Finish Tide's accessibility pass: a live region announcing each season's result, a text description of the coastline ('Row 5 dry, seawall tier 2'), and keyboard-operable tiles, investment buttons and graphs with visible focus. (partly built: Z15 audit fixed settings heading; text-scale and reduced motion exist; shared ?/Esc overlay. No aria-live, tile text or keyboard grid in index.html.) (Partly done 2026-10-07: live region, row descriptions, arrow keys between rows, focus ring; still open: per-column tile navigation.)
- [ ] D-8: Add named coastline scenarios to Tide (low delta town, rocky headland, atoll, dredged port), each with its own elevation profile, heritage sites, economy weights and storm frequency, combined with the sea-level scenario into a grid of starts.
- [x] D-9: Add a Harbor Almanac tab to Tide: lifetime seasons survived, rows saved, heritage protected, storms weathered, plus personal best per scenario and lag mode with the tier combination, kept per-browser and fed to the achievements dashboard. (Built 2026-10-08; the hub achievements dashboard feed needs a shared hook and is not built. The almanac's best run is most damage avoided, because seasons dry are fixed per scenario.)
- [ ] D-10: Add Bronze/Silver/Gold ranks to Tide's achievements (e.g. survive a storm / 3 / 3 with no row lost) and add ranked achievements for heritage, retreat, diversification, monitoring and population. (needs shared achievements framework check)
- [ ] D-11: Add autosave history to Tide: keep the last three per-season autosaves plus the checkpoint and, when a load fails validation, show a Restore previous save panel listing each slot's season and funds instead of resetting silently. (partly built: Shared save-widget has 3 account slots and opt-in 5-minute autosave; get_state/load_state validate with safe defaults. No rolling history or restore panel.)
- [ ] D-12: Add a customizable dashboard to Tide: choose, pin and reorder panels with Compact, Analyst and Postcard presets, remembered in localStorage.
- [ ] D-13: Add a living harbor scene to Tide: sky cycle by season of the year, water tint shifting with acidity (hatch pattern redundancy for colorblind), stormy sky in storm seasons, behind the grid with a Settings toggle.
- [x] D-14: Add game keys to Tide: A to advance a season, 1/2/3 to invest, R to open the report, listed in the existing ? overlay. (partly built: Shared ?/Esc overlay is wired (index.html KeyboardShortcuts.init); no A/1/2/3/R keys.)
- [x] D-15: Add Advance x5 to Tide: repeats quiet seasons and halts at a storm forecast, fish-yield warning, heritage site at risk or monitoring report.
- [ ] D-16: Add high-contrast and dyslexia-friendly font toggles to the shared site settings so every game gets them, with Tide's grid tiles and meter bars as the first high-contrast palette. (needs shared/site-settings.js)
- [ ] D-17: Add ticker filter chips (Fish / Sea / Economy / Storm / Chronicle) and a search box to Tide's delayed-effect ticker and full history. (Partly done 2026-10-07: chips and search on the full history only; the short live ticker stays unfiltered by design.)
- [x] D-18: Add a Copy as text button to Tide that copies the settlement name, chronicle and session summary to the clipboard.
- [ ] D-19: Show 'affordable in N seasons at current income' beside each Tide adaptation tier and diversification level, with a pin to keep one target highlighted.
- [ ] D-20: Add a net-funds preview chip to Tide that shows funds after purchase and after this season's upkeep (heritage, tier) when hovering or selecting any investment.
- [x] D-21: Add a crosshair readout to Tide's trend graphs: hover or tap shows a vertical line and tooltip with that season's acidity, yield, damage and funds.
- [x] D-22: Add a range selector (last 10 / last 20 / all seasons) to Tide's D7 timeline and D10 average-line graphs.
- [x] D-23: Add an optional series-markers toggle to Tide's graphs with distinct dash styles and point shapes (circle/square/triangle) per series.
- [x] D-24: Add a live tab title and favicon status to Tide, e.g. 'Tide S12 - fish warning', switching the favicon when a storm is forecast or a warning fires.
- [x] D-25: Add a personal-best line to Tide's session summary ('Best for this scenario: 14 seasons dry. You: 11') from the Almanac data. (needs D-9)
- [ ] D-26: Polish Tide on mobile: raise tap targets to 44px on tiles and invest buttons and add swipe between Coast / Meters / Log panels. (partly built: Mobile dock for Advance/investments (D1, mobile-dock.js) and a 320px audit (Z18) exist; tile/button min-height is 2.5rem; no swipe panels.)
- [x] D-27: Make each Tide <details> panel (timeline, chronicle, heritage, diversification) remember open/closed state across reloads.
- [ ] D-28: Add a delta breakdown popover to Tide: clicking a meter change (acidity +4) lists the contributors ('+6 output, -2 reduction, +0 aquaculture').
- [ ] D-29: Add a plain-language label mode to Tide Settings that renames jargon (dampening, lag, output mix) to everyday words in buttons and tooltips.
- [ ] D-30: Pause Tide's looping animations (wave cue, tide ripple, scene) when the tab is hidden or the device reports low power, and resume on return.
- [ ] D-31: Restyle Tide's achievement cards: a coral or wave glyph per earned badge, a coral-reef accent border from the coastline art, and a brief ripple on unlock.
- [ ] GD-2: Build Tide's Harbor Charter as a skill tree: finishing runs and achievements earn Charter Marks spent on permanent Tide-only unlocks (starting sandbag tier, second monitor charge, cosmetic pier styles); stored per-browser in Tide's own localStorage. (needs W-3) [reframe: Run-based meta reframed as a skill tree per W-3. The 'new starting Edict slot' unlock is dropped because GD-1 (Edicts) was declined.]
- [ ] GD-3: Add a Storm Season boss fight to Tide: forecast shows surge height, player gets two seasons to pre-commit funds to a brace allocation (barriers, evacuate heritage, stockpile), then a wave-crash animation on the grid and a tiered result (Shrugged Off / Battered / Breached).
- [ ] GD-4: Add a 'Tidal Chess' challenge mode to Tide: fish lag plus a new runoff lag (industry pollution feeds acidity 2 seasons late) both active, only the fish-yield warning visible, scored on how few seasons dip below FISH_YIELD_WARNING_THRESHOLD. (needs W-1 (optional, as a level-select mode))
- [ ] GD-5: Add a Daily Tide seed to Tide: a once-a-day fixed run (sea scenario and storm timing seeded by UTC date) with a shareable result line like 'Day 14: 11 seasons, 2 rows lost, 1 site saved'; optional opt-in daily board. (needs W-5 (optional))
- [ ] GD-6: Add rival neighbour towns to Tide: a computer-run settlement on a fixed strategy (greedy industrialist, cautious wall-builder, diversifier) shown as a faint second coastline strip; beating each rival's final population/funds unlocks that strategy as a starting preset.
- [ ] GD-7: Add a Reef Builder side-board to Tide: a 3x4 reef plot under the coastline where Reduction points plant coral tiles that grow, soften storm surge and boost adjacent fish yield, with adjacency bonuses and bleaching when acidity spikes; reuse the grid renderer.
- [ ] GD-8: Add Trade Winds market events to Tide: telegraphed season events offering a fish-export contract, tourism boom or insurance payout; the player accepts or declines each, deals interact with diversification levels.
- [ ] GD-9: Add a Postcard Ending to Tide: at session end render a pixel postcard from real state (walls, reef, heritage, boats, flooded rows as sunken roofs) with a letter grade and nickname; keep a collectable gallery of every postcard variant.
- [ ] GD-10: Add a Harbor Trials campaign to Tide: hand-made fixed starts (e.g. 15 seasons, 200 funds, high acidity, two heritage sites, 3 invests per season) each with a par score and 3 stars, shown through the level select with every 5th level a new mode or mechanic. (needs W-1)
- [ ] GD-11: Add Crew and specialists to Tide: hire up to three (Marine Biologist: fish lag one season shorter; Harbor Engineer: tier costs -15%; Broker: better deal terms) each with per-season upkeep so the choice is a build decision. (needs GD-8 (Broker))
- [ ] GD-12: Add an optional Acid Tide boss to Tide around season 15: a mega-event pushing acidity to a spike unless the player spends a large buffer (funds plus reduction); surviving upgrades the fish recovery banner to a full victory beat, skipping makes fish crash hard.
- [ ] GD-13: Add Lucky Catch to Tide: each Advance Season can roll a bonus haul (net-cast animation, '+35 lucky catch'), likelier at high fish yield, plus a fish collection where each catch logs a species so collectors can complete it.
- [ ] GD-14: Add a balanced-seasons combo to Tide: investing in all three categories in a season builds an x1.1/x1.2/x1.3 income streak, skipping a category breaks it.
- [ ] GD-15: Extend Tide's flood flash: tiles in a flooded row ripple in sequence, add a foam edge to the flash, a brief screen shake; shake and ripple must be toggleable and respect reduced motion. (partly built: D8 newly-flooded-row flash exists (.coastline-flash, game.py _previous_flooded_rows).) (no 'glub' text: you confirmed 2026-10-07, consistent with declining GD-29)
- [ ] GD-16: Add boat traffic to Tide's scene: small boat sprites drift across, more with higher fish yield and population, vanishing after a crash and leaving one abandoned hull; ambient only, off with reduced motion.
- [ ] GD-17: Add harbor-master crew quips to Tide: one-line ticker voice triggered by real state changes ('Wall's holding, boss. Ask me again in five seasons.'), hidden by the existing shared Story toggle plus its own mute switch in Settings.
- [ ] GD-18: Add secret coastline critters to Tide: after set conditions (low acidity for 5 seasons; a heritage site saved through a storm) a seal or whale fin appears on the scene and can be clicked to log it in a Sightings list.
- [ ] GD-19: Add a pin-a-goal banner to Tide: pick one personal goal from a dropdown ('Keep 4 rows dry', 'Reach 200 population') with a small progress bar under the header and a ping when reached.
- [ ] GD-20: Add Rewind Tide to Tide: one charge per run retracts the last Advance Season and marks the run with a small tin-hat icon in the summary so records stay honest.
- [ ] GD-21: Show the Tide storm forecast as a range with a chance to overtop seawalls ('surge 18-26, 70% to overtop Seawalls') drawn as a small bell-curve chip.
- [ ] GD-22: Add achievement cosmetic themes to Tide: fortified_in_time, stocks_rebound and similar achievements unlock scene themes (dusk sky, storm-glass, coral-pink sand), selectable in Settings.
- [ ] GD-23: Add optional speedrun trackers to Tide: fewest clicks and fewest seconds to max adaptation tier, stored beside best-coastline-saved and shown in the session summary.
- [ ] GD-24: Add a hard-lag ironman badge to Tide: finishing a 20-season run in Hard Lag without Rewind or checkpoint replay earns a gold-anchor badge on the header and settlement history. (needs GD-20)
- [ ] GD-25: Add a quiet-seasons counter to Tide's meter view: seasons since the last acidity rise, with a glowing frame at 5 and 10.
- [ ] GD-26: Add a dice button next to Tide's settlement name input that rolls fun harbor names ('Port Regret', 'Kelp Junction') and have the chronicle reference it.
- [ ] GD-27: Add a heritage-site rescue moment to Tide: when a site is saved at the last second before its row floods, show a lifeboat icon and 'SAVED!' burst plus a chronicle entry.
- [ ] GD-28: Add Domino Season to Tide: when several rows flood in one season the ticker calls it with a tally, and a small comeback bonus (temporary cheaper barriers) follows so a disaster becomes a pivot.
- [ ] GD-30: Add a season-end report card to Tide: a one-second overlay after each Advance Season with three stat chips (funds, acidity, fish deltas) coloured and iconed by good/bad, then fading; icons not hue-only, off with reduced motion.

*Not added: GD-1 (no); GD-29 (no).*

## GE + E. Aftermath (Round 3 answers, 2026-10-07)

- [x] E-1: Add a lifetime statistics dashboard to Aftermath: damage taken per event category, average mitigation per event type, best and worst event matchups, KP over time and average score by skill-strength band, built from run_log_history, with a text alternative for charts.
- [ ] E-2: Build a pannable, zoomable skill-tree map for Aftermath where selecting a locked node lights the cheapest route and total KP needed, with filters for weather/social/economic categories, keyboard operable. (needs W-3)
- [ ] E-3: Add a purchase route planner to Aftermath: from pinned skills, an ordered buy list respecting prereqs with a running KP total and estimated runs to complete from average_knowledge_per_run, updating live. (partly built: pinned_skills_text and runs_until_affordable(skill_id) give a per-skill estimate (E-style pin feature).)
- [ ] E-4: Add a shareable run code to Aftermath: export the schedule, scenario, severity draws and result so a friend can paste it and play the identical schedule with their own tree ignored or normalised, then compare scores.
- [ ] E-5: Finish Aftermath's accessibility pass: aria-live announcements of each event resolution ('Flood hit, 42 damage, 18 prevented'), focus management when panels open, keyboard operation of the tree, and a plain-text schedule strip. (partly built: Z15 audit (panels, h2 headings, real buttons), text scale, reduced motion and ?/Esc shortcuts exist; no aria-live anywhere in game.py/index.html.) (Partly done 2026-10-07: aria-live announcer for investments, undo and events; still open: focus management on panel open, keyboard operation of the tree, plain-text schedule strip.)
- [ ] E-6: Add opt-in custom run sliders to Aftermath (event count, starting resources, damage scale, growth income) with a shown difficulty multiplier on KP, a 'custom' tag in history and exclusion from the hardest-schedule leaderboard.
- [ ] E-7: Add a Settlement Chronicle book to Aftermath: a persistent scrollable timeline across runs (first flood survived, worst disaster, skills adopted, generational-memory callbacks, records broken), viewable and copyable, per profile.
- [ ] E-8: Add location-driven settlement art to Aftermath: art varies by chosen scenario (coastal harbor, inland farm town, dense city, named cities) with a per-event weather overlay on resolve, off under reduced motion.
- [ ] E-9: Add a difficulty-adjusted score to Aftermath: normalise each run by the severity of its drawn schedule and lifetime widening, and show raw and adjusted numbers in history and on the toughest-run badge.
- [ ] E-10: Add up to 3 named local profiles to Aftermath, each with its own tree, history, pins and achievements, switched from a header menu, keeping the shared save widget and export working per profile.
- [ ] E-11: Add three ranks per skill to Aftermath earned by proven use (Early Warning ranks after N accurate previews, category skills after preventing that damage type), shown in the tree with a visible progress count. (needs W-3)
- [x] E-12: Add a Disaster Codex to Aftermath: per event type times faced, average damage, best mitigation, with the dated real-world notes unlocking as you face it, plus a completion indicator. (partly built: REAL_WORLD_EXAMPLES: one dated real example per event type (read 2026-09-26), shown beside the run (render_real_world); no per-event stats page.)
- [ ] E-13: Add a schedule builder to Aftermath: compose an event order from the event library up to a set length, save by name, run it, tag runs 'custom schedule' and export through the shareable run code. (needs E-4)
- [x] E-14: Add Aftermath keyboard shortcuts for allocation (number keys), Enter to resolve, T for tree, H for history, listed in the ? overlay. (partly built: shared/keyboard-shortcuts.js gives ? help and Esc to close panels (Z4); no number keys or Enter.)
- [x] E-15: Add x1 / x5 / Max step buttons next to resilience and growth in Aftermath, respecting costs and the resource cap.
- [x] E-16: Add high-contrast and readable-font toggles to Aftermath's Settings panel beside text scale and reduced motion, included in Reset to Default.
- [ ] E-17: Add a schedule strip to Aftermath with hover/focus details per upcoming event (type, expected-damage range at current build, category mitigation bonus).
- [ ] E-18: Add a damage waterfall to Aftermath's resolution panel: base damage, severity change, each mitigation source, final damage as a stacked bar with text equivalent.
- [ ] E-19: Add tree search and filter chips (Affordable / Pinned / Owned / Category) to Aftermath's skill tree.
- [ ] E-20: Add side-by-side run compare to Aftermath's Review Past Runs: tick two runs to see events, damage and score in two columns with differences highlighted.
- [ ] E-21: Add sort (score, date, mode), filters (extended, custom) and archive to Aftermath's Review Past Runs, archiving without removing KP credit.
- [ ] E-22: Add a short per-run note field to Aftermath saved to history and shown in the list, included in the progress export.
- [x] E-23: Itemise Aftermath's end-of-run KP by source (base score and any bonus lines) in the summary panel so the preview is explained.
- [x] E-24: Add a Copy run summary button to Aftermath with settlement name, run number, score and event list as text.
- [ ] E-25: Add named allocation presets to Aftermath ('Flood plan: 3 resilience, 1 growth') applied in one click before an event, stored per profile.
- [ ] E-26: Enlarge Aftermath's mobile tap targets and confirm Resolve plus resources show in the bottom bar at phone width. (partly built: #actions-dock pinned to bottom via shared/mobile-dock.js and mobile-hud.js sticky HUD already hold the invest and Resolve buttons.)
- [x] E-27: Add a live tab title to Aftermath ('Aftermath - Run 7, event 3 of 6 (Flood next)'), hiding next-event type in fog mode.
- [ ] E-28: Add an unspent-resources confirm to Aftermath's Resolve (e.g. 'Keep 80 resources unspent?') with a Settings switch to disable it, via shared ConfirmDialog. (Decided 2026-10-08: build it with the default OFF.)
- [ ] E-29: Add a 'helps against' line to each Aftermath skill tooltip listing which upcoming events it softens and roughly by how much for the current schedule.
- [ ] E-30: Add a persistent save health badge to Aftermath ('Saved 12s ago / storage full / unsaved changes') covering localStorage, with a one-click export prompt when storage fails. (partly built: Shared save widget shows 'Saved at HH:MM' and 'Save failed'; tree lives in localStorage with no health badge.)
- [ ] E-31: Restyle Aftermath's achievements: show earned badges as small lit nodes on a mini tree-shaped strip beside the toggle button, with text labels, more visible and tied to the skill tree look.
- [ ] GE-3: Add an opt-in Fog of War mode to Aftermath where the next 3 events are hidden until Early Warning (reveals 1 ahead) and Mutual Aid Network (reveals 2 ahead) are owned; hide expected-damage preview and mentor hints for hidden events; keep a hint explaining how to reveal them. [conflict: Conflicts with E-17/E-29/GE-26, which all show upcoming events: those must respect fog. Early Warning and Mutual Aid keep their existing mitigation bonuses.]
- [ ] GE-4: Add a Compound Disaster boss event to Aftermath: an optional 8th event on extended runs chaining Storm + Infrastructure Failure as two phases with one emergency action between phases and a big knowledge-point payout; opt-in, with a visible hint of what it needs, and not luck-gated. (needs GE-6 (emergency actions))
- [ ] GE-6: Add one-time-per-run emergency actions to Aftermath (Deploy Crews, Open Shelters, Ration Supplies) unlocked through the skill tree, each trading resources for a burst of mitigation on the current event; offered at resolve time with the cost and effect shown, and keyboard operable.
- [ ] GE-7: Add opt-in Cursed Seasons to Aftermath: pick up to 3 curses before a run (all floods x1.5, growth income halved, no early warning) for a scaling knowledge-point multiplier with bragging-rights tiers shown in history; achievements stay reachable without curses.
- [ ] GE-8: Add an opt-in settlement districts mode to Aftermath: a 3x3 grid (harbor, market, hill and so on) where resilience and growth units are placed and events hit specific districts by type (floods hit harbor and market); keyboard operable; classic mode balance untouched.
- [ ] GE-9: Add a citizen roster to Aftermath: recruit 3 named citizens per run from a pool (Engineer cuts infrastructure damage, Organizer softens unrest, Gambler boosts growth with a risk) whose fates after events feed the legacy system; choose from a shown pool so nothing is luck-gated.
- [ ] GE-10: Add Second Founding prestige to Aftermath: after buying every skill, reset the tree for a permanent prestige star giving a small starting perk and unlocking 3 Founding-only alternate skills with strong tradeoffs; show clearly what is kept and lost, with a confirm dialog. (needs W-3)
- [ ] GE-11: Add a challenge gauntlet to Aftermath: a list of hand-built fixed schedules (The Three Floods, Blackout Week, Everyone Is Angry) with fixed severities and a par score, separate from hash-severity runs, with a completion tick per challenge so it is easy to 100%. (needs W-1)
- [ ] GE-12: Add insurance and double-down bets to Aftermath between events: insurance (pay now, recover 60% of next event's damage) and a bet (pay resources for a bonus if damage stays below the preview range), using expected_damage_range as the shown odds; both opt-in and clearly priced.
- [x] GE-13: Add a damage-prevented popup to Aftermath after each event: a count-up '-58 damage prevented!' number plus a small streak counter if mitigation held two events in a row; respects reduced motion (static number).
- [ ] GE-14: Add per-category event hit effects to Aftermath (flood blue ripple, heatwave orange pulse, unrest red shudder) with emphasized resolution numbers, and a separate Settings toggle for screen shake and flashes (off by default under reduced motion) for sensitive players.
- [x] GE-15: Add a Flawless Defense flash to Aftermath when an event's damage drops under 10% of base, awarding a bonus knowledge point and a new achievement in achievements.json, with the threshold hinted in the mentor. (Built with a 15% of base damage threshold, not 10%: the 85% mitigation cap and severity of at least 0.85 make under 10% unreachable. Review if you want a different bar.)
- [ ] GE-16: Add a skill unlock reveal animation to Aftermath: a newly bought skill glow-pulses and the links toward newly available prereq-gated children light up (list highlight if the tree is still a list); respects reduced motion. (needs E-2 (tree map, for connector lines))
- [ ] GE-17: Add 2 mystery skill nodes to Aftermath's tree: '?' nodes with no description until prereqs are bought, then revealing a perk (e.g. Lucky Break: an event is halved on a fixed, hash-decided one in ten); show the revealed odds so nothing is hidden luck.
- [x] GE-18: Add undo of the last allocation click to Aftermath within a between-event phase before Resolve, with a visible undo-count; disabled after Resolve and after load.
- [ ] GE-19: Add a Mutation of the Day to Aftermath: a deterministic-by-date modifier (floods x1.2 severity, growth cost -3) shown on the run screen, opt-in, framed as a daily scenario with a clear name and a normal-run option; not a random mutator. [reframe: Daily scenario, not roguelike mutators; keep it opt-in and exclude from the main leaderboard.]
- [ ] GE-20: Add a settlement mood emoji strip to Aftermath: tiny citizen faces shifting from grinning to grim with resources and resilience, updated on each allocation click, with an aria-label for screen readers.
- [ ] GE-21: Add a post-run epitaph to Aftermath: a witty line from a large bank keyed to outcomes (e.g. 'The levee held. The mayor did not.') on the run-summary panel, with a Settings toggle to hide it and a tone kept gentle for bad runs.
- [ ] GE-22: Add a run-improvement streak to Aftermath: a fire counter at 2+ consecutive runs beating the prior best, with a warm glow in Review Past Runs; use text plus icon, not colour only.
- [ ] GE-23: Add an optional run timer to Aftermath with a best-time-to-finish column in Review Past Runs; time never affects score or KP, only a badge, and the timer is off by default.
- [ ] GE-24: Add a starting twist to Aftermath runs: each run begins with a chosen or hash-decided quirk (Rich Start: +60 resources and no growth; Fortified Slum: +2 resilience, -1 growth) shown before the run, with the player able to pick from the list. [reframe: Random mutator reframed as a selectable scenario option with no luck-gated outcomes.]
- [ ] GE-25: Add unlock-tier settlement skins to Aftermath (thatched, timber, concrete) at skill thresholds 5, 10 and all, shown at run start and in history; set thresholds from the tree's actual size (currently 7 skills).
- [ ] GE-26: Add an event countdown pulse to Aftermath: a gentle pulse on the schedule strip and slight growth of the next-event icon as Resolve nears, off under reduced motion and the new effects toggle. (needs E-17 (schedule strip))
- [ ] GE-27: Add lucky break and dark omen rolls to Aftermath: a hash-decided ~5% chance an event severity gets x0.7 or x1.3 with a special banner, shown in the preview beforehand so it is never a surprise penalty.
- [ ] GE-28: Add a critical insight chance to Aftermath: a deterministic small chance of doubled KP on a perfect defense, with sparkle text, and a hint of when it can happen so nothing important is luck-gated.
- [ ] GE-29: Add a run recap highlight reel to Aftermath: a 5-second sequence of the run's worst hit and best save as animated cards before the table, with skip button and static fallback under reduced motion.
- [ ] GE-30: Add named legacy monuments to Aftermath: a top-3 score run permanently adds a small monument icon to the settlement art with a plaque showing the settlement name, listed in a trophy shelf.

*Not added: GE-1 (no); GE-2 (no); GE-5 (no).*

## GF + F. Herd (Round 3 answers, 2026-10-07)

- [ ] F-1: Add Herd 'Ranch Rules' sliders in Settings (starting funds, season swing, pressure penalty, growth-cost slope) with a custom-rules summary; custom runs tagged unranked and excluded from Z1 community stats and leaderboards.
- [ ] F-2: Add Herd 'Ranch Ledger' tab: compact summary per finished session/generation (final funds, methane, score vs baseline, levers, poultry) with a trend chart filtered by mode (cap/seasons/plain), stored in localStorage.
- [ ] F-3: Add Herd round replay: a timeline scrubber replaying pasture cows, gauge, haze and funds per round with markers for lever purchases and advisor choices; needs a per-round state record.
- [ ] F-4: Add a Herd shareable farm card PNG export (gauge, trend sparkline, score vs baseline, levers, achievements count) from the report card, reusing the shared print-summary component. (partly built: Z21 print-friendly report card (print-summary.css); no image export.)
- [ ] F-5: Add Herd 'Farm Snapshots': export a mid-run state as a challenge code with the sender's best result attached as the score to beat, using the save-widget code path. (partly built: Shared save-widget save codes (get_state/load_state) already share any state.)
- [ ] F-6: Add a Herd 'explain this number' inspector: click income, methane, coupling ratio or pressure loss for a breakdown tree (base, each lever, season, welfare, supply chain), reusing the consequence-preview math.
- [ ] F-7: Add a Herd dry-run planner drawer: queue several rounds of purchases on a scratch copy and see projected gauge, funds and methane for 5-10 rounds, with the counterfactual line for reference.
- [ ] F-8: Add a Herd mixed-herd allocation UI: after poultry unlocks, one allocation slider across beef/dairy, poultry and plant-based with a live stacked bar of income, methane and welfare per segment.
- [ ] F-9: Add a Herd policy-advisor offer pool (carbon-credit contract, feed-price hedge, organic label trial, welfare grant) drawn without repeats, an advisor history list with real-world tags, and report-card display.
- [ ] F-10: Complete Herd keyboard and screen-reader play: every lever and Advance Round keyboard reachable with visible focus, arrow-key control on the lever list, aria-live round-result announcements, and a shortcut cheat sheet in How to Play. (partly built: Z15 audit of panels (no gap), Z4 ?/Esc shortcuts via shared/keyboard-shortcuts.js; Z28 focus ring.) (Partly done 2026-10-07: polite live region reads the round result; still open: arrow-key control on the lever list, a visible-focus audit, the shortcut cheat sheet.)
- [ ] F-11: Add Herd Beginner/Standard/Expert profiles at new game: Beginner shows a next-best-lever hint chip, Expert hides previews and tooltips, built as toggled layers over existing content.
- [ ] F-12: Add offline-first polish across games: precache Pyodide, an 'offline, community stats paused' status pill, and a queued stats/feedback submit that flushes on reconnect; start with Herd. (partly built: sw.js: network-first with offline fallback, precaches game shells (site milestone 10); Pyodide CDN cache-first at runtime, no precache or status pill.)
- [x] F-13: Add a Herd 'funds per methane saved' figure to each lever in the lever list, from the existing preview formulas.
- [ ] F-14: Add Herd optional colourblind-safe hatch patterns and shape markers for the methane trend graph, welfare bar and supply-chain bar, toggled in Settings.
- [ ] F-15: Add Herd high-contrast theme and dyslexia-friendly font toggles in Settings, persisted via the same localStorage path as text scale.
- [ ] F-16: Add a Herd pin-a-stat header: pin up to three readouts (funds, welfare, income per round) into a sticky strip visible while the extras panel is open.
- [x] F-17: Add a Herd lever history log: a collapsible list of purchases ('Round 4: bought Capture Systems (-40)') under the extras panel, filterable by lever.
- [ ] F-18: Add a Herd Settings option to require confirmation for any purchase above N percent of current funds, using the shared confirm dialog. (partly built: Shared confirm-dialog already guards the Plant-Based Pivot (F16) only.)
- [x] F-19: Add a Herd x1/x5/max bulk-buy stepper beside Grow Herd and lever buttons showing total cost before clicking, reusing the rising-cost preview.
- [x] F-20: Add Herd round-delta chips (+/-) beside funds, methane, welfare and pressure after each Advance Round that fade after a few seconds, with a pin click.
- [x] F-21: Add a Herd 12-round season calendar strip in seasons mode showing upcoming income swing and plant-demand surge as colour- and icon-coded cells.
- [x] F-22: Add a Herd poultry vs cattle comparison mini-card in the poultry panel: per-unit income, methane-equivalent and welfare effect side by side.
- [x] F-23: Add a Herd breeding progress ring on the breeding lever showing rounds left in the 3-round maturation, replacing the text.
- [x] F-24: Add a Herd cap-mode headroom bar under the 20-methane cap with 'rounds until you must decouple' at the current growth pace.
- [ ] F-25: Add Herd settings export/import: one button copies all local settings (text scale, motion, toggles, personal bests) as a short code, another restores it, using shared/export_progress.py.
- [ ] F-26: Add a Herd slow-device lite mode toggle (haze, methane wisps, cow-graze off, static pasture), and make it a shared setting in shared/site-settings.js offered to the other games.
- [ ] F-27: Add Herd achievement hover progress: mini progress bar and exact amount left on hover/focus, extending ACHIEVEMENT_PROGRESS to the remaining numeric achievements. (partly built: ACHIEVEMENT_PROGRESS gives unearned cards an 'N of M' line for ~6 numeric achievements; no hover bar.)
- [x] F-28: Add a discreet Herd pace note on the round counter and a save-and-quit nudge every 10 rounds.
- [ ] F-29: Add Herd plain-language glossary popovers (coupling ratio, counterfactual, welfare, capture) via dotted underlines with a full glossary in How to Play.
- [ ] F-30: Add Herd friendly save-recovery: when a save fails validation in load_state, show a plain reason and an option to load with defaults.
- [ ] F-31: Restyle Herd achievement cards: livestock/pasture glyph per earned badge, barnyard-accent border and a brief unlock flourish (reduced-motion respecting).
- [ ] GF-2: Extend Herd's succession legacy perks into a visible upgrade tree: start with one capture unit, a second policy-advisor option, a rare breed with better breeding odds, a farmhouse skin; make certification and poultry early goals each generation chase. (partly built: F25 succession: hand_over_farm(), legacy_points, LEGACY_PERKS (Family Savings, Heritage Flock, Mentor's Methods), #succession-panel; test_succession.py.) (needs W-3)
- [ ] GF-3: Add Herd Auditor boss rounds: every 10th round a regulator audit with a visible target (e.g. coupling under 0.6 and welfare over 60), 3 rounds of warning; pass earns a permanent perk, fail costs a fine and a market-trust hit.
- [ ] GF-4: Add Herd rival ranch ghost opponents (Big Ag Barry pure growth, Organic Olive pure restraint, community-median copy) with a live scoreboard strip; win by beating them in funds AND methane. (needs backend pool (median rival))
- [x] GF-5: Add Herd decoupling combos: named build-order combos (Circular Barn, Happy Herd, ...) with a grey-silhouette combo book that fills as discovered, each giving a small reward.
- [ ] GF-6: Add Herd Ranch-of-the-Week: date-seeded fixed-event challenge with handicap modifier (e.g. no capture systems, double weather swings), scored against the community percentile via Z1 and a personal weekly history strip. (needs backend pool, W-5)
- [ ] GF-7: Add Herd commodity trading as an optional game mode: a price ticker for meat, dairy and eggs where contracts lock the next 3 rounds at today's price, interacting with season swings and plant-demand surges.
- [ ] GF-8: Add Herd disaster events (heatwave, disease outbreak, feed-price spike, flood) with a 2-round telegraph and a specific lever to blunt each (welfare/breeding vs disease, capture vs regulator visit); opt-in like seasons.
- [ ] GF-9: Add Herd ranch expansion map: a small paddock grid where herd units are placed; neighbouring paddocks share bonuses (capture pipes link, biofilters cover adjacent poultry sheds).
- [ ] GF-10: Extend Herd's Marlow Farm story into a branching 'The Family Farm' narrative: Grandpa's choices (sell to agribusiness, go organic, take the subsidy) with light vignettes and 3 endings, still skippable via the story toggle with the sim unchanged. (partly built: story.json + shared/story-chapters.js: Marlow Farm story, one chapter per achievement, Story on/off pill (W1, 2026-09-26).)
- [ ] GF-11: Add Herd challenge ladder: named score-attack modes (Decouple by round 12, Max profit under a 15 methane cap, Poultry only) with bronze/silver/gold medals and a trophy shelf; consider W-1 level select with a mode every 5th entry. (needs W-1 (optional))
- [ ] GF-12: Add Herd cow reactions: pasture cows show moo bubbles, hop or nap depending on welfare and coupling, with a silly quip on click; respect reduced motion.
- [ ] GF-13: Add Herd named cows: generated names (Beyonmoo, Sir Grazealot) on hover plus a retired hall of fame for the longest-serving units.
- [ ] GF-14: Add a Herd round-summary 'cha-ching': rolling count-up of funds on Advance Round and a small confetti burst when the round beats the last; toggleable and reduced-motion respecting.
- [x] GF-15: Add a Herd perfect-round streak counter (methane fell AND funds rose) with a flame icon and tiny bonuses at 3/5/10 rounds.
- [x] GF-16: Add Herd breed collection: named breeds as a collector shelf with a hidden Methane-Eater Cow (e.g. coupling under 0.25 with welfare over 90), glowing sprite and shelf achievement; breeds in general are a collector goal per owner.
- [ ] GF-17: Add Herd achievement-gated cosmetic barns: earning certain achievements unlocks barn/fence/tractor skins for the pasture hero image, selectable in the extras panel.
- [x] GF-18: Add Herd 'undo last round' once per game at a fund penalty, to let players try risky levers and recover from misclicks.
- [ ] GF-19: Add Herd tactile animations: a short CSS tractor crossing the screen on Advance Round and squish-on-press buttons, reduced-motion respecting, no audio.
- [ ] GF-20: Add Herd farm event cards: each round a 20% chance of a one-line flavour event with a two-button choice and small stakes (e.g. neighbour offers to buy 2 units: cash or refuse).
- [ ] GF-21: Add Herd golden-cow bonus: rarely a golden cow glides across the pasture and clicking it in time grants a one-off funds bonus; provide a non-timed alternative (button or reduced-motion auto-claim).
- [x] GF-22: Add a Herd rating title ladder on the report card (Hobby Farmer to Decoupling Legend) with a tiny cartoon and the next title's requirement.
- [ ] GF-23: Add Herd starting loadouts (Big Herd, Lean Green, Poultry Start, Cash Rich) unlocked by achievements that bend opening funds/levers for a new game or generation.
- [ ] GF-24: Add a Herd sandbox mode: set herd size, methane and levers freely and watch the gauge react, with no scoring and no achievement/community effects.
- [ ] GF-25: Add an optional Herd feed-additive mixer minigame: a 5-second click-timing bar (hit the green band) nudging that round's feed effect by a few percent, with an auto-resolve button.
- [ ] GF-26: Add Herd rival and policy-advisor speech-bubble one-liners after each round based on standing, using the existing vignette plumbing. (needs GF-4 (rival))
- [ ] GF-27: Add a Herd post-certification crate: a satisfying open animation granting a cosmetic or small perk, shown as a visible prestige reward with the contents hinted so 100% never relies on luck. [reframe: Random loot reframed as hinted/choose-one reward; cosmetics share GF-17 shelf.]
- [ ] GF-28: Add a Herd opt-in blind-run hard mode hiding the counterfactual and gauge best-markers until the end, with a stronger reveal then.
- [x] GF-29: Add a Herd per-run highlights reel: a 3-line recap of funny moments (peak herd, biggest single-round swing) after a generation or on the report card, screenshot-friendly.
- [ ] GF-30: Add a Herd daily perk pick: each calendar day offer one of two small boons (e.g. +5% feed effect), chosen by a date-seeded rotation and shown in advance. [reframe: Random daily boon made a visible date-seeded rotation (not a random mutator); overlaps GF-6 date seed.]

*Not added: GF-1 (no).*

## GG + G. Thaw (Round 3 answers, 2026-10-07)

- [x] G-1: Add a Thaw 'Field Notes' tab charting every finished run over time (temperature saved, tipped regions, average acceleration, lever mix, per-region bests), storing per-run summaries. (partly built: Climate archive (G23): per-region bests of degrees saved, furthest round, highest dampening in localStorage.) (needs GG-2 or GG-9 (run end))
- [x] G-2: Add a Thaw overlay chart comparing any two past runs (or a run against the Region D counterfactual) on one graph with the melt gridline and a per-round divergence readout. (needs G-1)
- [ ] G-3: Add a Thaw round-replay scrubber showing the three regions across rounds with scientist's-log entries pinned at their rounds.
- [x] G-4: Add a Thaw explain-this-number inspector: click a warming rate or acceleration factor to see a stacked breakdown (background rise, feedback, dampening reduction, monitoring), tied to the info toggles.
- [ ] G-5: Add a Thaw forecast planner drawer: draw hypothetical funding splits and see dashed 10-round temperature projections per region beside the next-round tooltip.
- [ ] G-6: Add a Thaw difficulty panel in Settings: sliders for background rise, feedback strength, starting funds, monitor cost, with Gentle/Standard/Severe presets; tag custom runs and exclude them from Z1 percentile comparisons.
- [ ] G-7: Add a Thaw shareable run report: one-click printable and PNG poster with the three region graphs, final temperature saved, best region message and top log lines, using the shared print-summary pattern.
- [ ] G-8: Add Thaw challenge codes: export a mid-run state as a shareable code so a friend takes over from round N and tries to beat the temperature-saved score, via the shared save widget.
- [ ] G-9: Add a Thaw scientist-mode view toggle replacing friendly labels with real units plus small footnotes on where each constant came from; any real-world figure (e.g. Gt carbon) must be read live and named. [conflict: A 'Gt carbon proxy' mapping would be an invented real-world claim unless sourced live; owner should confirm labels stay game units.]
- [ ] G-10: Add full keyboard and screen-reader play to Thaw: focus rings on every control, aria-live announcements of tipping, critical tier and round results, and a summary-sentence text alternative per mini-graph. (Partly done 2026-10-07: aria-live round summary, mini-graph labels, focus rings; still open: a full keyboard-only play-through audit.)
- [ ] G-11: Add Thaw history decimation: collapse older rounds into summary points so graphs stay fast in long games, plus a developer-panel memory readout; keep saves and long_game compatible.
- [ ] G-12: Add a Thaw board-room table with sortable columns (temperature, acceleration, dampening, funds, rounds since tipping, best-ever), per-row sparklines and Region D as a greyed row.
- [x] G-13: Add a Thaw temperature unit setting (Celsius, Fahrenheit, Kelvin) converting displays, gridline and thresholds, persisted in localStorage.
- [x] G-14: Add Thaw Settings option giving region graph lines distinct dash patterns and end markers for colour-independent reading.
- [x] G-15: Add Thaw high-contrast and readable-font themes in Settings that override the glass panels, persisted like text scale.
- [ ] G-16: Add a Thaw mini-graph hover crosshair showing the round, exact temperature and dampening at that point, keyboard accessible.
- [ ] G-17: Add a Thaw larger single-region focus view that expands one region's graph and readouts full width with lever controls beneath.
- [ ] G-18: Add Thaw scientist's-log filter chips (tipping, milestones, invest), text search and plain-text export.
- [ ] G-19: Add Thaw log entry pinning so pinned entries survive the 40-entry cap and appear in the run report. (needs G-7 (for report))
- [ ] G-20: Add a Thaw custom preset slot for Regions B and C with the same preview tooltip, saved in the save state.
- [ ] G-21: Add a faint personal-best pace line on Region A's graph from the stored best run; needs stored per-round best history.
- [ ] G-22: Add a Thaw round-counter note with estimated session length and a safe-to-save nudge.
- [ ] G-23: Add a Thaw Settings threshold that uses the shared confirm dialog for investments above a chosen size.
- [x] G-24: Add a Thaw sparkline next to the acceleration readout showing its recent trajectory.
- [ ] G-25: Add Thaw settings export and import: copy and restore all local settings and personal bests as a short code, no account needed.
- [x] G-26: Add a Thaw lite mode in Settings disabling backdrop blur, ambient background animation and graph transitions.
- [ ] G-27: Add progress bars and a remaining-amount readout (and hover detail) to Thaw's locked achievement cards. (partly built: Locked achievements show 'X of Y' text via ACHIEVEMENT_PROGRESS in update_achievements_display().)
- [ ] G-28: Add Thaw glossary popovers on underlined terms (dampening, acceleration factor, melt threshold, monitoring) with one-line definitions and a full glossary in How to Play.
- [ ] G-29: Add Thaw friendly corrupt-save recovery that names which field failed and offers load-with-defaults.
- [ ] G-30: Add Thaw community-compare history keeping the last five percentiles in a mini list in localStorage.
- [ ] G-31: Restyle Thaw's achievement cards with arctic frost/permafrost glyphs per earned badge, an icy accent border matching the region palette and a brief unlock flourish (reduced-motion safe).
- [x] GG-2: Add a Thaw 'Hold the Line' mode: keep at least two of three regions un-tipped for as many rounds as possible while background rise escalates via new events; score is rounds survived, with an opt-in leaderboard entry. (needs W-1 (as a mode level), W-5)
- [ ] GG-3: Build Thaw's Station Upgrade skill tree: finishing modes earns research credit spent on permanent Thaw-only upgrades (earlier next-round warning, starter dampening, a 4th preset, wider mini-graph); all upgrades reachable with no luck. (needs W-3, GG-2)
- [ ] GG-4: Add Thaw crisis events (wildfire, sinkhole road, heatwave, funding slump) with a 2-3 round countdown, defused by spending monitor or preserve resources; roll them deterministically from round and region like cascade_roll, with a visible warning.
- [x] GG-5: Add resource routing to Thaw: convoy funds between Regions A, B and C with a small transport tax so the player triages between rescuing a critical region and feeding a healthy one; never touches Region D.
- [ ] GG-6: Add Thaw survey mode: regions start with hidden permafrost carbon density, revealed by paying for a survey; rich regions tip harder but yield more output; densities are fixed per save (no luck) and hinted before purchase.
- [ ] GG-7: Add a Thaw daily 'Cold Case' (UTC date-seeded scenario with fixed start temperatures and one twist) with a temperature-saved score compared to the community percentile through the existing Z1 stats hook. (needs W-1 (mode level))
- [ ] GG-8: Add a Thaw sandbox 'Director' mode: the player triggers background-rise bumps (volcano, heat dome) to try to tip regions run by an AI steward of selectable skill; a toy mode that teaches the same dynamics. (needs W-1 (mode level))
- [ ] GG-9: Add a Thaw challenge ladder of named modifier runs (Minimalist, All-in Output then pivot, Blind until round 10) with medals and a trophy shelf; reuse GG-23 and GG-25 toggles for the Blind and no-preview modifiers. (needs W-1 (mode level))
- [ ] GG-10: Add an optional 10-second Thaw stabilise minigame when a region enters critical tier (route sensors, plug leaks, click hotspots) granting a temporary dampening buff, with an auto-resolve skip so the sim is never gated.
- [ ] GG-11: Add Thaw story mode 'The Station Crew': a small cast comments on each region across the run with three endings by spread of outcomes, with a story-off toggle (build on the existing flavour-line toggle and shared story-toggle).
- [ ] GG-12: Add a toggleable (off by default for reduced-motion) low-frequency shake of the region card plus a crack animation across its mini-graph when a region tips, in Settings.
- [x] GG-13: Add the 'Ice Age' streak medal to Thaw: show the stable-round count as a medal that grows into a frosty icon at 5/10/15 consecutive rounds below the melt threshold. (partly built: tipping-streak-display (game.py ~2197) shows rounds since last tipping event.) (Built as rounds without a tipping event, since 15 rounds below the melt threshold is impossible with the fixed background rise.)
- [ ] GG-14: Add Thaw's secret 'Snow Leopard' achievement for finishing with Region A 8+ degrees cooler than Region D, unlocking a station skin. (needs GG-18 (skin selector))
- [ ] GG-15: Add a toggleable Thaw mascot pair (snow hare and arctic fox, drawn as inline SVG or emoji) in the corner that react to state (shiver when hot, cheer when dampening rises, faint at critical) and occasionally bicker; no audio.
- [ ] GG-16: Add occasional research-grant notes to Thaw offering a gamble (take 30 funds now or 60 only if no region tips next round); roll deterministically per round and show the odds so it is never luck-gated.
- [ ] GG-17: Add one Thaw undo per run: rewind a round at a funds cost, snapshotting state before Advance Round.
- [ ] GG-18: Add achievement-locked Thaw map skins (aurora borealis, tundra at dusk, 8-bit tundra) selectable in Settings, each unlocked by a named achievement.
- [ ] GG-19: Add a Thaw rolling-digit temperature readout that ticks up during Advance Round, faster when acceleration is high, collapsing to instant under reduced motion.
- [x] GG-20: Add a Thaw 'phew' banner when a region's projected next-round temperature would have crossed melt or critical but the last investment pulled it back.
- [x] GG-21: Add three fixed AI stewards (Cautious Kai, Rash Rasmus, Balanced Bea) to Thaw that post deterministic temperature-saved scores each run so the player sees who they beat. (needs GG-2 or GG-9 (run end))
- [ ] GG-22: Add a Thaw mystery supply crate every 6th round with a perk (extra preserve unit, monitor discount, faster preset) and an opening animation; make the perk deterministic and hinted ahead so it is never luck-gated.
- [ ] GG-23: Add an opt-in Thaw hard mode that hides the next-round three-region preview tooltip and dampening forecast, with an end-of-run reveal of how close the player's guess was.
- [x] GG-24: Add a Thaw title ladder from 'Ice Cube' to 'Cryosphere Guardian' by temperature-saved bands, shown at finish with the next title's goal. (needs GG-2 or GG-9 (run end))
- [x] GG-25: Add a Thaw blindfold toggle in Settings that hides mini-graphs and shows text status only.
- [ ] GG-26: Add a Thaw post-round ticker of funny fake headlines reacting to conditions (fox complains about mud), clearly fictional, with a story-off hide.
- [x] GG-27: Add a Thaw perfect-balance bonus: a small fund bonus and a visual pulse (no audio) when all three regions end a round within 1 degree of each other.
- [x] GG-28: Add a Thaw 3-line highlights recap built from the scientist's log at session end or on demand (e.g. Region B tipped round 9, recovered round 14), with a copy/share button.
- [ ] GG-29: Add Thaw loadout presets Scout, Builder and Gambler that shift starting funds and dampening, unlocked via the station upgrade tree or achievements. (partly built: POLICY_STANCES (G13): Growth/Balanced/Mitigation start for Region A.) (needs GG-3 (optional))
- [ ] GG-30: Add a Thaw daily boon: first session each day offers a choice of two tiny boons (+10 funds or cheaper monitor), stored per day in localStorage, no streak pressure.

*Not added: GG-1 (no).*

## GH + H. Loop (Round 3 answers, 2026-10-07)

- [ ] GH-3: Add Market Shock events to Loop: a deterministic, telegraphed event (price spike, port strike blocking a trade partner for 3 cycles, demand trend) shown one cycle early; looped chains shrug it off, linear chains are hit; no fail-state; on/off setting.
- [ ] GH-4: Add Loop Lab meta-progression to Loop: finished chains earn Patents that permanently unlock options (Modular Design and Take-Back Depot investment variants, starting-funds tiers, a fourth investment slot), built as a skill tree. (needs W-3)
- [ ] GH-5: Add a Rival Corporation ghost to Loop: a linear extraction-only AI runs the same production target in parallel and races your cumulative profit, ahead early and overtaken as damage multiplies its costs, with a visible crossover moment.
- [ ] GH-6: Add Chain Puzzle Mode to Loop: hand-authored levels (e.g. close a 40% chain in 6 cycles with 200 funds and no trade; hit 90% circular using only Reuse), each with a par cycle count and 3-star rating, via the level select (every 5th level a mode). (needs W-1)
- [ ] GH-7: Add a Daily Seed chain to Loop: one deterministic scenario per UTC day (goods category, starting damage, event schedule) with a local personal best, optionally an opt-in leaderboard, modelled on Signal's daily seed engine. (needs W-5 (optional board))
- [ ] GH-8: Add a Bottleneck mode to Loop (opt-in, offered via the level select): each investment node gets a throughput cap, overload visibly backs up the flow particles, so repair/reuse/recycling capacity must be balanced like a factory builder. (needs W-1)
- [ ] GH-9: Add a Loop Tycoon Autopilot to Loop: after the first closed loop, cycles can advance on a timer while funds buy automation-tier upgrades, with deterministic elapsed-cycle catch-up computed on load; opt-in separate mode, Advance Cycle stays.
- [ ] GH-10: Add Franchise prestige to Loop: once the loop is closed and score passes a bar, reset the chain for a permanent multiplier and a new goods tier (Electronics, Vehicles, Buildings) with harder base circularity. (needs W-3)
- [x] GH-12: Add a Perfect Cycle combo multiplier to Loop: the existing zero-extraction streak climbs a combo that multiplies that cycle's score bonus, dropping to zero on a miss. (partly built: closed_loop_streak/best_closed_loop_streak count zero-extraction cycles and reset on a miss (game.py:645-653).)
- [ ] GH-13: Add investment juice to Loop: each Repair/Reuse/Recycle purchase snaps its ring node, ripples outward and floats a '-N raw' extraction-saved number; toggleable and silent under reduce-motion. (partly built: Funds burst, trade-network pulse tiers and top-node glow exist (game.py _trigger_funds_burst, pulse_tier); no ring-node snap, ripple or floating numbers.)
- [x] GH-14: Add a secret fourth goods category to Loop (e.g. Ship-Breaking Yard or Fast Fashion), unlocked by 100% circular on all three normal categories, with its own vignette lines and a different starting fraction.
- [x] GH-15: Add Loop Score name plates to Loop's end screen: The Scrapper (mostly recycle), The Fixer (mostly repair), The Diplomat (mostly trade), plus a mix title, with a collection list of the plates earned.
- [ ] GH-16: Add damage-meter cracks to Loop: panel borders gain visual cracks and the starfield dims slightly as damage climbs, easing back as circularity recovers; no extra numbers, honours reduce-motion.
- [x] GH-17: Add a Golden Cycle to Loop: once per chain one future cycle (seeded, deterministic) sparkles in the UI and doubles supply from the investment bought that cycle; never required for achievements. [conflict: Owner rule: nothing luck-gated without a hint. Sparkle is the hint; keep optional and out of records.] (DROPPED: dropped by you 2026-10-08 (luck item).)
- [ ] GH-18: Add a Rewind token to Loop: one per chain, reverts the last Advance Cycle (state snapshot), shown as a spendable token in the header.
- [ ] GH-19: Add a snarky supply-chain narrator ticker to Loop under the chain, with lines reacting to play, controlled by the existing Story on/off toggle (add its selector).
- [x] GH-20: Add speed-loop achievements to Loop: closed the loop by cycle 12, closed with under 500 total extraction, never used trade; shown in the achievements panel only, not as callouts.
- [x] GH-21: Add an optional import-export gamble to Loop: a two-choice 'sell now or hold a cycle for a chance at a higher price' with odds shown; opt-in, equal expected value, never needed for achievements or personal bests. [conflict: Random outcome clashes with 'nothing luck-gated'; making it opt-in and disclosed.] (DROPPED: dropped by you 2026-10-08 (luck item).)
- [ ] GH-22: Add collectable Trading Cards to Loop: 6 per goods category unlocked at circular-fraction thresholds, art-free stat blocks with rarity and in-game stats, shown in a collection panel. [conflict: Real-world fun facts must be read live and dated, not recalled; keep card text in-game, or source it.]
- [ ] GH-23: Add unlockable ring colour themes to Loop (Neon, Blueprint, Paper Cut-out) earned through achievements and chosen in Settings, cosmetic only.
- [x] GH-24: Add Streak insurance to Loop: spend 10 funds once per chain to freeze the closed-loop streak through one bad cycle.
- [x] GH-25: Add near-miss messaging to Loop: when a cycle ends just short of a closed loop or next 25% step, show 'So close: N units short!' with the cheapest one-click fix that would have covered it.
- [ ] GH-26: Add a Landfill Mining mode to Loop (separate start scenario): begin with a huge waste heap as a resource pool, spend funds to dig it into the loop, with toxicity costing extra unless Repair/Reuse is high. (needs W-1)
- [ ] GH-27: Add Two-chain juggling to Loop (optional mode): run two goods categories at once sharing one funds pool and damage meter, trade partners pick a side each cycle, investments spill by-products to the other chain. (needs W-1)
- [ ] GH-28: Add ghost replay sharing to Loop: export a compact run code (investments per cycle) that another player loads as a ghost line on their circular-fraction graph to beat.
- [ ] GH-29: Add optional haptics to Loop: subtle vibration on investment and at 25% milestones where the browser allows, off by default, toggled in Settings.
- [x] GH-30: Add Crates to Loop: each closed-loop milestone grants a crate with a perk from a visible catalogue (+10 funds, an investment discount, a cosmetic node), shake animation toggleable. [conflict: Random reveals clash with easy-to-100%: make the catalogue visible and complete in a fixed order.] (DROPPED: dropped by you 2026-10-08 (luck item).)
- [ ] H-1: Add a Past Chains archive to Loop: store a compact record per finished or reset chain (category, cycles to close, total extraction, score, investment mix) and a panel with a line chart overlaying the last 5 chains' circular-fraction curves.
- [ ] H-2: Add an opt-in Sandbox Tuner to Loop: sliders for starting funds, production target 30-80, damage multiplier cap and investment costs; tuned chains tagged 'custom', excluded from bests and difficulty-sensitive achievements (Z27), tuning saved in the save code.
- [ ] H-3: Add a Multi-cycle Planner to Loop: queue investments across the next 3-5 cycles and preview projected circular fraction, extraction cost and funds before committing.
- [x] H-4: Add an Accessible Chain view to Loop: an ordered list/table mirroring the ring, trade partners and meters, with an aria-live per-cycle summary ('Cycle 14 complete: 62% circular, extraction down 4'), fully keyboard reachable. (partly built: network_map_text() text supply map and the Z15 audit exist; no aria-live in index.html, no list/table mirror of ring and meters.)
- [ ] H-5: Add three named chain slots inside one Loop save with a header switcher, each showing last-played time and circular %; the save code carries all slots.
- [ ] H-6: Add a full-page style switcher to Loop (Blueprint, Paper Craft, Retro Terminal) in Settings via CSS variables only: ornate on desktop, a lighter set on mobile.
- [ ] H-7: Add comparison cards to Loop: a Share result button exports a code (category, cycles, extraction, score, per-cycle circular fractions) that a friend pastes into a Compare panel for side-by-side sparklines and stats.
- [ ] H-8: Add Assist mode to Loop: Off/Hints/Guided, Hints highlights the investment with the best marginal supply gain, Guided adds a one-line why from the audit calculations; assisted runs tagged and excluded from mastery records.
- [x] H-9: Add a Career records board to Loop: per-category bests (fastest close, lowest extraction, highest score, longest zero-extraction streak) with date and settings tag, plus a heat-strip of every cycle played coloured by circular %.
- [ ] H-10: Add a Cycle ledger to Loop: a sortable table per cycle (funds in/out, units by source, damage, multiplier, trade partner used) with a Copy as CSV button, beside the audit panel.
- [ ] H-11: Add a phone layout to Loop: a swipeable three-tab bottom dock (Chain / Invest / Stats) using shared/mobile-dock.js, keeping the sticky cycle/funds/circular % HUD strip. (partly built: shared/mobile-hud.js sticky HUD is wired (index.html:468); no three-tab dock (shared/mobile-dock.js not used).)
- [ ] H-12: Add a Founder Rank ladder to Loop (Apprentice, Engineer, Director...) from cumulative cycles, chains closed and categories mastered, as a non-mechanical badge inside Loop and on the hub title card.
- [x] H-13: Add game shortcuts to Loop: Space advances a cycle, 1/2/3 buy Repair/Reuse/Recycling, T triggers trade, all listed in the ? help overlay. (partly built: shared/keyboard-shortcuts.js gives ? help and Esc close (index.html:492-503); no game-action keys.)
- [ ] H-14: Add buy-multiple to Loop: shift-click or an x1/x5/x10 chip applies an investment several times with a running total shown on the button.
- [x] H-15: Add a worked-equation tooltip to Loop's extraction cost: 'base 10 x damage multiplier 1.8 (cap 2.5)', also readable on touch. (partly built: Damage display shows 'extraction cost x1.80' with a tooltip and visible ceiling note (game.py:2172-2190); no base x multiplier equation.)
- [x] H-16: Add a High contrast switch to Loop's Settings: stronger text, panel border and ring node contrast, starfield removed behind text panels, persisted like the other settings.
- [x] H-17: Add a dyslexia-friendly font switch to Loop's Settings: a system dyslexia-friendly stack with wider letter spacing, persisted like other settings.
- [x] H-18: Add a flow animation speed selector to Loop's Settings (Off / Slow / Normal / Fast) for the chain particles, separate from reduce-motion.
- [ ] H-19: Add optional shape-coded particles to Loop: rings for circular paths, squares for linear paths, as a Settings toggle.
- [ ] H-20: Add a spend-confirmation threshold to Loop's Settings: ask 'Spend 120 of 140 funds?' when a purchase exceeds a chosen percentage of funds, default off.
- [ ] H-21: Add collapse chevrons with localStorage memory to every Loop panel (audit, score, trade network, vignette). (partly built: The decluttering pass added collapsible <details> sections (index.html:193 etc.); state is not remembered.)
- [x] H-22: Add a live tab title to Loop, e.g. 'Loop - C14 - 62% circular', updated every cycle.
- [x] H-23: Add a Copy summary button to Loop: plain text like 'Loop Clothing - closed cycle 18 - score 940' plus a block-character row of per-cycle circular fraction.
- [ ] H-24: Build a shared next-up achievement chip showing the closest unearned achievement and its progress (e.g. 'Zero-extraction streak 3/5'), in Loop first, then every game. (needs shared component)
- [ ] H-25: Add a chain size picker to Loop: Short/Standard/Long (target 30/50/70) at chain start, scores normalised per unit and records labelled by size.
- [ ] H-26: Add per-node sparklines to Loop: hovering a ring node shows a tiny sparkline of spending in that node per cycle.
- [ ] H-27: Add a load-time integrity note to Loop: when a save is corrupt or old, show a friendly 'repaired X, reset Y' list instead of silently defaulting.
- [ ] H-28: Add optional one-line cycle notes to Loop, shown in the ledger and history.
- [ ] H-29: Add performance auto-mode to Loop: sample frame times and, if the ring animation struggles, offer 'Switch to light animation?' with one-click acceptance saved to settings.
- [ ] H-30: Add a 'Replay tips' button to Loop's Settings that resets the one-time onboarding hints (Regional Partner, hard ceiling, etc.). (partly built: A Tutorial restart button exists (index.html:33); one-time hints (regional_hint_seen etc.) are not resettable.)
- [ ] H-31: Restyle Loop's achievement cards: earned badges render inside a small closed-loop ring icon with a brief unlock flourish (honours reduce-motion), and make the achievements entry point more visible.

*Not added: GH-1 (no); GH-2 (no); GH-11 (no).*

## GI + I. Drift (Round 3 answers, 2026-10-07)

- [x] GI-1: Add Mayor's Council milestones to Drift: every 10 rounds choose one of three named civic programs (Night-School Network, Rapid Housing Modules, Transit Expansion), each a permanent run-long effect with a trade-off, built as a branching upgrade tree, not a drawn hand or random offer. (needs W-3) [reframe: Owner said no deck-builder. Closest honest version: a deterministic pick-one-of-three upgrade tree; all programs visible up front so nothing is luck-gated. Overlaps GI-3 and GI-9.]
- [x] GI-2: Add a Crisis Calendar to Drift: telegraphed events (surge round, budget cut, bumper harvest, flood damaging infrastructure) shown one round ahead in a Next Round preview, with an optional pay-to-brace choice; always recoverable, never a fail state, fixed schedule not a random deck. [reframe: 'Deck' reads as card mechanics; built as a visible deterministic calendar instead. Reuse the second-wave warning pattern. GI-11, GI-12 and GI-26 build on it.]
- [ ] GI-3: Add Advisors to Drift: recruit up to three specialists (Housing Planner, Language Teacher, Logistics Chief), each with a small passive bonus and a cooldown special move (e.g. Surge Build: housing half price this round); advisor choice is deterministic and visible, with a fire/rehire option.
- [ ] GI-4: Add a Region Atlas to Drift: four preset starting regions (Coastal Port, Mountain Valley, Border Junction, Post-Industrial Town) with distinct capacity/income profiles, each unlocked by clearing the previous at a target wellbeing; the last tier reuses the Crisis Start profile. (needs W-1)
- [x] GI-5: Add a Budget Autopilot to Drift: standing allocation rules (e.g. keep services at 60%, spend surplus on housing) that auto-advance rounds quickly while the player tunes the rules, with a visible rule log and an easy stop; opt-in mode that never gates achievements.
- [ ] GI-6: Add Rival Regions to Drift: three named AI-managed regions (Frugal, Builder, Reactive) simulated on the same severity curve and drawn as extra lines on the trend graph, with a round-60 comparison result card.
- [ ] GI-7: Add Grant Applications to Drift: periodic funding grants requiring a capacity mix by a deadline (e.g. Services >= 40 within 5 rounds for +100 funds), shown as short-term objectives; a missed grant just lapses, never a penalty.
- [ ] GI-8: Add an optional District Planner mode to Drift: a small grid where housing blocks, schools and clinics occupy footprints and adjacency gives bonuses (school beside housing boosts services), as a separate game mode that leaves the core investment loop untouched. (needs W-1) (you confirmed 2026-10-07: separate optional mode, the core loop stays)
- [ ] GI-9: Add Legacy Points to Drift: finishing a run at Model Region banks points spent in a branching permanent unlock skill tree (start with +20 funds, a fourth capacity type Community Spaces, Hard Mode tiers). (needs W-3)
- [ ] GI-10: Add a what-if Timeline Scrubber to Drift: after a run, pick any round, change one decision and replay forward, showing the new wellbeing curve diverging from the original on the trend graph.
- [x] GI-11: Add Boss Rounds to Drift: rounds 25, 50 and 75 are named surge tests (arrivals spike scaled to the severity curve) with a one-round preview and a bespoke 'held the line' celebration card when capacity covers it.
- [ ] GI-12: Add a Weekly Region Challenge to Drift: a deterministic weekly starting profile plus fixed event schedule keyed to the ISO week (no backend), with a per-week personal best stored in localStorage.
- [x] GI-13: Add a Perfect Fit streak to Drift: when capacity covers the round's arrivals within a small margin with no overbuilding, a counter grows and gives a small wellbeing bonus, shown beside the forecast panel.
- [ ] GI-14: Add a building pop animation to Drift: each investment makes a building rise-and-settle with a tiny dust puff on the region visual; off when Reduce Motion is on.
- [x] GI-15: Add Region Personality titles to Drift: the end-of-run summary names your spending pattern (The Builder, The Educator, The Engineer, The Balancer) and each title is collected in a titles list.
- [ ] GI-16: Add a Lucky Break to Drift: rarely a small sparkling windfall (community donation or volunteer wave: +15 funds or a free housing build) appears, drawn from a seeded schedule.
- [x] GI-18: Add a Rewind Token to Drift: one take-back per run that undoes the last round advance (restoring the pre-advance state), with a used-marker in the run summary.
- [ ] GI-19: Add a strain heartbeat to Drift: a soft pulse on the strain readout whose speed rises with strain level and calms as it falls; disabled by Reduce Motion.
- [ ] GI-20: Add an optional Municipal-humor ticker to Drift: a one-line warm local-news headline strip (e.g. Council debates bench placement for six hours), never mocking arrivals, with an off toggle in Settings.
- [x] GI-21: Add Star ratings to Drift: each finished run earns 1-3 stars on three goals (wellbeing, speed to net-positive, funds efficiency) with a run-history strip of the best star combos.
- [x] GI-22: Add Civic Milestone discoveries to Drift: certain capacity combinations at set rounds (e.g. services and infrastructure both above 100 by round 30) reveal named cosmetic entries in a collection panel, each with a hint once locked.
- [ ] GI-23: Add Council vote popups to Drift: when funds cannot cover both a housing and a services purchase in the same round, offer a two-button vote with a short flavor line and a tiny modifier for the chosen path.
- [ ] GI-24: Add Seasons to Drift: rounds cycle through four seasons that tint the region visual and modestly shift income and arrivals (winter housing pressure, harvest income), shown in the forecast.
- [ ] GI-25: Add cosmetic region skins to Drift: unlockable building palettes (Seaside, Alpine, Desert, Neon Future) earned through achievements and selectable in Settings.
- [ ] GI-26: Add an Emergency Response step to Drift: during surge rounds, a 3-step quick decision panel (open temporary shelter, request mutual aid, ration services), each option with a distinct cost and strain effect, replacing a plain advance.
- [ ] GI-27: Add a Legacy Map to Drift: a persistent map that grows across runs with districts you unlocked or perfected, which carries starting bonuses into the next run. (needs W-3) [conflict: Overlaps GI-9 (Legacy Points unlock tree): build one meta-progression with the map as the tree's presentation. Owner to confirm.]
- [ ] GI-28: Add a mentor ghost to Drift: after reaching Thriving, load one of your own past runs as a faint per-round build-order guide, with bonus Legacy Points for matching or beating it. (needs W-3)
- [ ] GI-29: Add band-change confetti to Drift: crossing into a higher wellbeing band triggers a short confetti/ripple over the gauge; silent and off when Reduce Motion is on. [conflict: The idea mentions an optional chime; dropped because the owner said no audio of any kind.]
- [x] GI-30: Add a Play 5 rounds button to Drift that auto-advances with the current allocation and stops early if strain rises a level or a forecast event arrives.
- [ ] I-1: Add a Region Archive to Drift: store every completed run (region name, difficulty, final band, net-positive round, ROI split, trend curves) and browse them with an overlay chart comparing wellbeing curves from any three runs.
- [ ] I-2: Add a Scenario Builder to Drift: sliders for starting housing/services/infrastructure, income, severity rate and horizon (50/100/150) producing a shareable scenario code, loadable from the setup screen; custom runs are tagged so records and achievements stay honest.
- [ ] I-3: Add Planner assist to Drift: an Off / Suggest / Explain toggle recommending this round's purchases from the forecast and ROI data with a one-line reason; assisted runs are tagged and excluded from personal bests.
- [ ] I-4: Add a Region Report to Drift: at run end, a printable card and copy-as-text report (name, difficulty, key rounds, subscore trends, ROI table, coda choice).
- [ ] I-5: Add a non-visual play mode to Drift: the region visual, arrival stream and gauges mirrored as labelled tables, an aria-live round summary and full keyboard control of purchases.
- [ ] I-6: Add in-game named region slots to Drift: three slots named from the region name, each showing last-played time and current band, switchable from the header, so Standard and Crisis Start regions can run side by side and the slots ride the save code. (partly built: shared/save-widget.js gives 3 numbered slots per signed-in account with time-ago labels (U3).)
- [ ] I-7: Add a rich district view to the Drift Desktop boot: pan/zoom, day/night lighting, and arrival dots traveling along roads to the buildings that house them, keeping the simple visual for mobile. (partly built: Desktop boot (PC-10) gives the full-window layout and skyline banner; pan/zoom and traveling dots are not built.)
- [x] I-8: Add a Round Ledger to Drift: a full-run table (funds in/out, allocation split, arrivals, integrated, pending, strain, subscores) with sorting, filtering and Copy-as-CSV.
- [ ] I-9: Add named difficulty tiers to Drift (Gentle, Standard, Rigorous, Demanding) bundling existing toggles with a summary line of what each changes, with personal bests tracked per tier and Z27 achievement rules respected.
- [ ] I-10: Add a split-screen dual-region layout to Drift: a desktop two-column view with linked highlighting between the player's region and the neighbouring district, and a tabbed single column on phones.
- [ ] I-11: Add terminology and tone settings to Drift: a choice of vocabulary (arrivals / newcomers / new residents) and a numbers-only mode that hides vignettes and the dot stream, suitable for classrooms.
- [ ] I-12: Add event markers to Drift's trend graph (first net-positive round, band changes, strain peaks, reallocations, second-wave start) with hover detail and toggleable layers (strain, wellbeing, control region, ROI). (partly built: trend_graph_svg draws strain, wellbeing and a dotted control-region line with a legend.)
- [x] I-13: Add keyboard purchase controls to Drift: number keys buy Housing/Services/Infrastructure, Enter advances the round, and the ? help lists them via KeyboardShortcuts extra.
- [ ] I-14: Add budget templates to Drift: save up to three named purchase plans (e.g. Services-first) and apply each in one click per round.
- [x] I-15: Add a Reset this round button to Drift that refunds purchases made since the last Advance Round and restores the earlier funds and capacity.
- [ ] I-16: Add range chips (Last 10 / Last 25 / All) and a crosshair tooltip with exact values per round to Drift's trend graph.
- [x] I-17: Add a collapsible round recap line to Drift after each advance (e.g. Housing 12 short; 8 integrated; strain steady).
- [x] I-18: Add a Copy run summary button to Drift: plain text with a block-character wellbeing curve, region name, tier and final band.
- [ ] I-19: Add a Compact / Comfortable density toggle to Drift's Settings beside text size, persisted like other preferences.
- [x] I-20: Add High-contrast and Dyslexia-friendly font toggles to Drift's Settings, boosting contrast on gauges and panels, persisted like existing preferences.
- [ ] I-21: Add an animation speed selector (Slow / Normal / Fast / Off) to Drift's Settings for the arrival-dot stream and building transitions, separate from Reduce Motion.
- [ ] I-22: Add round number and wellbeing band name to Drift's mobile sticky HUD. (partly built: MobileHud (shared/mobile-hud.js) shows funds, strain and wellbeing score on phones.)
- [ ] I-23: Add a segmented arrivals pipeline to Drift: a pending-versus-integrated bar split by age bands (this round, 2-3 rounds, 4+ rounds).
- [x] I-24: Set Drift's tab title each round to 'Drift - R37 - Stable - Region Name'.
- [ ] I-25: Turn Drift's personal-best readout into a per-tier table (best band, fastest net-positive round, date).
- [ ] I-26: Add a 20-round sparkline beside each subscore trend arrow in Drift.
- [ ] I-27: Add a manual-save nudge to Drift: when more than 10 rounds have been advanced since the last save, show a gentle 'saved X ago' reminder near the save widget. (partly built: shared/save-widget.js shows 'N min ago' per slot and 'Saved at HH:MM' after saving.)
- [ ] I-28: Add an optional large-move confirmation to Drift using the shared confirm dialog, when a reallocation or policy purchase uses more than a set share of funds or capacity, with the cost shown.
- [ ] I-29: Add glossary popovers to Drift: tap-or-hover terms (capacity, strain, integration, control region) open a one-line definition with a link to The Real Story where relevant.
- [ ] I-30: Show a friendly 'restored X, reset Y' note when Drift loads a corrupted or old-version save instead of silently defaulting. (partly built: load_state falls back safely on missing keys (test_save_system.py), silently.)
- [ ] I-31: Restyle Drift's achievement cards with a small route or milestone glyph per badge tied to the region art and a brief unlock flourish (off with Reduce Motion), replacing the plain rows.

*Not added: GI-17 (later, parked in LATER.md).*

## J. Trade Empire (Round 3 answers, 2026-10-07)

- [ ] J-3: Build the Trade Empire Cartel Board endgame system: a market-cornering research branch that lets you deliberately spike a good's price (buy out the stockpile) or crash rivals (dump), with a backlash penalty if the same good is squeezed twice in a short window; show the penalty window plainly.
- [x] J-4: Add a 'price memory' ghost line to each Trade Empire price sparkline showing where the price was before your last manipulation (stockpile buy/sell now, Cartel Board squeezes later), drawn dashed or labelled, not colour only.
- [ ] J-5: Build a Chain Builder puzzle mode in Trade Empire: draw multi-hop production chains (e.g. Ore to Alloy to Machinery) with intermediate refining colonies, scored by throughput per ship, as a separate mode so the main economy is unchanged. (needs W-1 (optional: chain levels as a level select))
- [x] J-6: Show a 'throughput per ship' number per route/chain on Trade Empire's Ledger (units moved per ship per N ticks), so the score has a home before Chain Builder exists.
- [x] J-7: Add Fleet Captains to Trade Empire: each ship earns a captain at veteran-hauler milestones, and the player CHOOSES its perk from a visible roster (Frugal, Lucky Trader, Night Owl, Perfectionist) with per-archetype trade-offs; captains swap between ships once per charter. [reframe: Reframed: random perk draw is luck-gated and roguelike-ish; made a visible, choosable, collectable roster. 'Once per session' changed to once per charter (assumed; confirm).]
- [x] J-8: Show each Trade Empire captain perk as a short humorous quote on the ship panel (e.g. 'Every crate counted twice'), hidden when the Story toggle is off.
- [ ] J-9: Build a 'Trade Crises' scenario campaign in Trade Empire: handcrafted starting boards (Grain Famine at Aurum, Isotope Glut in Kepler, Broken Automation Network) each with a par target for gold/silver/bronze medals, separate from the main arc, with achievements for medals. (needs W-1 (optional: scenario list as a level select))
- [ ] J-10: Add a restart-scenario hotkey (listed in the ? shortcut help) and a best-medal chip on each Trade Crises scenario card in Trade Empire.
- [ ] J-11: Add Corporate Espionage to Trade Empire: a non-violent shadow NPC firm, Meridian Freight, contests the same routes and is seen only through price moves you did not cause; answer by out-pricing it, signing exclusive Trade Guild contracts, or ignoring it. No combat or piracy.
- [ ] J-12: Add a rival ledger line ('Meridian moved 340 units this cycle') in Trade Empire that is flavour only until Market Intel research is unlocked, after which it shows real numbers.
- [x] J-13: Layer named Prestige Charter archetypes on Trade Empire's renewal: on each renewal choose a focus (Hardened Fleet, Frontier Speculator, Master Diplomat) that also reshapes the starting board (one colony pre-developed, one good locked), in addition to the existing perk tree. (partly built: O-1..O-4 done: charter points + 12-perk tree, O-2 automatic founding conditions on renewal, harder charter. No named archetype that changes the starting board.) [conflict: Your earlier O-1 note chose a research tree instead of picking a single charter; this proposes a single pick. Proposed as an archetype on top of the tree; also overlaps O-2's automatic conditions.] (DROPPED: dropped by you 2026-10-08.)
- [x] J-14: Show the active Charter's crest (a shape plus a text label, not colour only) next to the Trade Empire title, and list past Charters as a career log on the Ledger/Charter panel. (partly built: Charter panel has a lifetime ledger (counts of charters, goods, routes, hard runs; O-3). No crest by the title and no per-charter career log.)
- [ ] J-17: Add Market Weather to Trade Empire: unpredictable one-off booms and slumps (a festival at Verdant, a strike at Ferrum) lasting 20-40 ticks that cascade to dependent colonies, with the Almanac hinting at leading indicators so close readers can front-run them; opt-in toggle like seasonal demand.
- [ ] J-18: Add a text-only news ticker chip on Trade Empire's map with a one-line headline per Market Weather event ('Strike at Ferrum: ore output down'), no scrolling motion.
- [ ] J-19: Build a Ship Blueprint Lab in Trade Empire: a research-unlocked screen where you allocate points among speed, hold and efficiency to design, name and save custom hulls, with several saved designs per run to choose from when buying ships.
- [ ] J-20: Add a 'compare to average hull' bar chart on Trade Empire's Blueprint Lab, with value labels so the trade-offs read at a glance without colour.
- [ ] J-21: Add a Hub & Spoke layer to Trade Empire: designate one colony as a Distribution Hub that halves transit to its neighbours but caps its own stockpile, with different hub choices favouring different networks, and update Fleet Priority routing to account for it.
- [ ] J-22: Draw the Trade Empire hub node with a thicker ring and a tooltip stating its current bonus.
- [ ] J-23: Add an Expedition side-mode to Trade Empire: send one ship on a long multi-tick exploratory run away from routes for a reward table (new good, one-time windfall, research points, nothing), costing that ship's income; include a bad-luck guarantee so nothing essential is luck-gated.
- [ ] J-24: Show an 'expedition odds' tooltip on Trade Empire's send-expedition button listing each outcome's chance and the bad-luck guarantee.
- [x] J-25: Add Colony Personalities to Trade Empire: each colony gets a temperament (Grateful, Demanding, Opportunistic) that evolves from its trade history and changes its price premium and how it reacts to Colony Investment and loyalty events, derived deterministically and explained in the colony panel.
- [x] J-26: Draw a small emoji-free mood glyph (circle/triangle/square) on each Trade Empire colony node keyed to temperament, with a legend.
- [ ] J-27: Build a Second Economy endgame tier in Trade Empire: once the fourth cluster (Umbral Deep) exists, unlock an interstellar commodities exchange where you set standing buy/sell orders that fill on their own, tying trade posts, speculation and automation together.
- [ ] J-28: Add an order-book mini-table to Trade Empire's exchange showing the last five fills.
- [ ] J-29: Add an opt-in Blackout Challenge hard mode to Trade Empire: map and sparklines hidden unless bought through Market Intel research, and prices shown as ranges; keep it clearly optional with a plain-language warning.
- [ ] J-30: Add a 'dark run' achievement and a Ledger stamp for finishing the Trade Empire endgame under Blackout, with the badge shown on the title/opening screen.
- [x] J-31: Restyle Trade Empire's achievements: show earned badges on a small 'Ledger' ribbon strip near the Achievements toggle (space-commerce look echoing the Ledger stamps), with a brief unlock flourish that respects reduce-motion and the effects toggle.

*Not added: J-1 (no); J-2 (no); J-15 (later, parked in LATER.md); J-16 (later, parked in LATER.md).*

## K. Continuum (Round 3 answers, 2026-10-07)

- [ ] K-1: Add a governed 'Standing Orders' system to Continuum: pick if/then rules from menus (e.g. food surplus below X shifts labour to Provision; unrest above Y pauses new districts), no code writing; slots/trigger types unlocked by research nodes; each firing is logged in the policy log/Council Minutes.
- [x] K-2: Add a Dynasty meta-progression to Continuum: every finished or failed run banks Legacy points (extra for Hard Mode) that buy permanent starting perks and new starting scenarios (hardier tribe, river-valley start, library heirloom); perks shown in the archive, switchable off. (partly built: O-7 founding.LEGACIES one-off founder's legacy and O-8 Refuge scenario are built (founding.py); no Legacy points, perk shop or Dynasty rank.) (needs W-3 skill-tree component (perk shop could use it))
- [x] K-4: Add a 'technical debt' mechanic to Continuum's Digital and later eras: quick cheap builds accrue hidden debt raising maintenance and failure odds until a refactor season is scheduled; shown as a City Views dashboard line and a hazard tint on the civic map.
- [ ] K-5: Add living ruins to Continuum: old buildings persist as heritage sites (3D scene, civic map; culture bonus if kept, free land/materials at a livability cost if demolished, Look Back preview); later eras switch the layout from circle to grid to fit more buildings.
- [x] K-6: Add era doctrines to Continuum: at each era transition pick one doctrine (Maritime, Highland, Caravan, Scholarly) that makes some research branches cheaper and unlocks different buildings, recorded in the founder's log and tied to Dynasty perks (K-2). (needs K-2 Dynasty perks) (Built 2026-10-09 without 'unlocks different buildings': every building is tied to a fixed era and role across the engine, the hamlet view and tests, so the doctrine gives cheaper research branches plus a standing bonus instead.)
- [x] K-7: Add neighbouring settlements to Continuum: 2-3 AI cities with their own eras and needs on a small regional map where the player trades, shares research or competes for a contested resource, built as the same slot interface a later multiplayer mode would use. (needs W-6 multiplayer scoping (done), backend pool if real players later) (Built 2026-10-09 as three computer-controlled neighbours behind a controller slot; no shared research pool and no hostile actions, by design.)
- [x] K-8: Add an advisor council to Continuum: 3-4 named advisors (farmer, engineer, merchant, scholar) give conflicting seasonal recommendations; the player tracks trust and each advisor's record is scored against real outcomes; optional and hidden by the story toggle. (needs shared/story-toggle.js)
- [x] K-9: Add a time-lapse run replay to Continuum: scrub the playthrough as a 3D timelapse with policy log, founder's log and research unlocks pinned on a timeline, and export a ~20-second clip or image strip, building on the shareable card and settlement archive.
- [ ] K-10: Add a daily seed challenge to Continuum: one fixed seed, scenario and modifier per UTC day with a par score and a 'you vs everyone' percentile from the Z1 stats endpoint, with no streak penalty. (needs Z1 stats endpoint (built); UTC daily seed pattern from Signal) (Partly done 2026-10-08: daily challenge from shared/seed.py with par, ledger and Today-strip key; still open: the you-versus-everyone percentile, which needs a board registered in app/boards.py.)
- [x] K-11: Add a scenario editor and mod codes to Continuum: sliders for starting resources, event frequency, era length and a few rule toggles, exported as a short share code another player can load and try to beat the par.
- [ ] K-12: Add a generated map with biomes to Continuum (rivers, coasts, mountains, desert) that changes resource costs, where districts can go and how disasters hit, rendered in the 3D scene and 2D civic map, with consulting cities carrying their own inherited geography.
- [ ] K-13: Add an endless 'Beyond' mode to Continuum after the Relay Age: procedurally escalating generated eras each with a themed sustainability mechanic and rising entropy, scored by how many eras the city survives, with a 'furthest era reached' ladder in the archive.
- [x] K-14: Add a post-mortem screen to Continuum after any run: auto-generated retrospective (what went well, what went wrong, root cause of the biggest livability drop, three decisions to redo) built from the Council Minutes/policy log and the livability-vs-growth scatter.
- [x] K-15: Add notable citizens to Continuum: generated named citizens with a trade and personal thread (apprentice to guild master, child to next-era engineer) who follow the city across eras and unlock small bonuses; can be switched off and referenced in the founder's log. (needs shared/story-toggle.js)
- [x] K-16: Add a 'why did that change' hover explainer to Continuum stats: shows the top three contributing factors of the last change as a small waterfall.
- [x] K-17: Add a limited-use 'rewind one season' token to Continuum, earned through achievements or a Dynasty perk, costing something valuable to use. (needs K-2 Dynasty perks (optional))
- [x] K-18: Add a data export button to Continuum that downloads CSV and JSON of per-season stats and policy-log (Council Minutes) entries. (partly built: Archive card JSON download exists (game.py _download_card, card.js); no CSV/JSON per-season stats or policy-log export.)
- [x] K-19: Add a side-by-side compare of two archived Continuum settlements with stat deltas highlighted.
- [x] K-20: Add cosmetic city banners and skyline flourishes to Continuum, unlocked by achievements and Dynasty rank, shown in the archive and on the shareable card. (needs K-2 Dynasty rank)
- [x] K-21: Add a screensaver mode to Continuum: the 3D city runs itself with a slow orbit camera and all UI hidden, for a second monitor. Visual only; no ambient soundscape (audio is parked, see K-22).
- [x] K-23: Add subtle tech-industry easter eggs to Continuum's Digital era log lines and building names (legacy-server closet, co-working guild hall), hidden by the story toggle. (needs shared/story-toggle.js)
- [x] K-24: Add settlement naming to Continuum: an era-flavoured name generator plus a free-text option (length-limited and sanitised), shown on the plaque, archive and shareable card.
- [x] K-26: Add a par-time badge to Continuum: finish a run in fewer real minutes or fewer seasons than a par set per scenario, using the existing time-played readout.
- [x] K-27: Add sparklines to Continuum's City Views dashboard next to every stat showing the last 20 seasons.
- [x] K-28: Add a 'citizen of the season' spotlight card to Continuum's log: one named resident and one flavour line tied to a recent event, hidden by the story toggle. (needs shared/story-toggle.js)
- [x] K-29: Add an opt-in Blitz timer to Continuum's Hard Mode: 30 seconds per season or the default policy applies, with its own achievement (opt-in, with a pause or accessibility off switch). (DROPPED: dropped by you 2026-10-08.)
- [x] K-30: Add a hotkey remapping panel to Continuum's Settings beside the '?' cheat-sheet, to bind advance-season, view switches and camera presets to custom keys.
- [x] K-31: Restyle Continuum's achievement cards: earned badges get a small per-era icon and the violet-glass accent, laid out as a 'monument row' instead of a plain list (no generated images; inline SVG or CSS). (partly built: Achievement cards exist (style.css .achievement-card, 21 in achievements.json) with progress and rarity; no era icons or monument row.)

*Not added: K-3 (later, parked in LATER.md); K-22 (later, parked in LATER.md); K-25 (no).*

## L. Le Champ de Mots (Round 3 answers, 2026-10-07)

- [ ] L-1: Build a Le Champ de Mots farm economy: mastered plots yield harvest coins (fed from the practice ledger), spent at a market stall on cosmetic decor, a bigger watering can that reminds adjacent plots, and plot skins; never touches SRS scheduling and every coin source visibly counts. (Partly done 2026-10-09: Farm shop with one coin per full watering and six cosmetic ring skins; still open: bigger watering can, harvest coins from mastered plots, decor, market stall.)
- [ ] L-2: Build Le Champ de Mots end-of-chapter market-day boss: multi-round fight on that chapter's vocab, grammar and phonetic items with lives and a combo special attack, rewarding a plot skin and an achievement; reuse combo, adaptive distractors and test pool; counts to practice score. (needs L-1 (skins))
- [ ] L-3: Build a separate optional Le Champ de Mots 'Voyage' minigame: cross France city by city answering question rounds from the core generator, with free-hint and second-try perks as a permanent upgrade/collection track (not random relics or card draws); feeds SRS/practice ledger and score. [reframe: Owner: 'as another mini game'. Roguelike/relic/deck framing replaced by fixed city route plus unlockable perks; easy to 100%.]
- [ ] L-4: Build a Le Champ de Mots 'error detective' mode: a French sentence with one planted mistake (gender, agreement, accent, auxiliary); player taps the wrong word and fixes it; mistakes drawn from the error-pattern digest; add to PRACTICE_MODES so it counts.
- [ ] L-5: Extend Le Champ de Mots with a village of named recurring NPCs (baker, postman, vet) who request items and phrases over days, with a friendship level raised by correct answers; story thread stays optional; answers count to practice score. (partly built: story.json + Story panel (changelog 2026-09-26, off toggle); Cafe Rush/Boutique Dash customers exist; no persistent NPCs.)
- [ ] L-6: Build a Le Champ de Mots daily mots croises: one procedurally generated mini-crossword or word-search per day from unlocked/learning words with a par time; counts to practice ledger.
- [ ] L-7: Build Le Champ de Mots cloze stories: short generated paragraphs from mastered vocabulary with gaps to fill, ordered easy to hard; counts to practice score; supersedes the parked story-quiz entry in LATER.md.
- [ ] L-8: Build a Le Champ de Mots mock-exam simulator: timed FREN151/152-style test over a chosen chapter range with predicted grade, per-topic breakdown and a 'fix these three things' list; counts to practice score.
- [x] L-9: Build a Le Champ de Mots exam-date planner: enter exam date, what-if slider (N minutes a day -> % plots Automated by then), projection from the real SRS state and a minimum-daily-effort suggestion.
- [ ] L-10: Build a Le Champ de Mots conjugation matrix puzzle: persons-by-tenses grid with blanked cells, timed, combos for completed rows/diagonals, added as a sixth minigame family entry counting to practice score.
- [ ] L-11: Build a Le Champ de Mots farm layout sandbox: earned decor (scarecrows, fences, fountains) placeable freely around the plots, plus a screenshot-able farm card. (needs L-1 (decor source))
- [ ] L-12: Build Le Champ de Mots classmate farm visits: share code to a read-only farm snapshot and a 'care package' of 5 tough words left for the owner; needs a backend snapshot table in app/; opt-in and safe. (needs backend snapshot table)
- [ ] L-13: Add personal mnemonics to Le Champ de Mots plots: write your own memory sticker per plot, shown on a failed answer, with auto-suggest from past failures; ties into the phrasebook.
- [x] L-14: Build a Le Champ de Mots daily quest board: three small goals a day (e.g. water 5 grammar plots, 90 in Blitz, 3 liaison items) granting coins or practice score; missed days leave it empty, no streak. (needs L-1 (coins, optional))
- [x] L-15: Build a Le Champ de Mots faux-amis arcade minigame: rapid-fire real cognate or false friend with increasingly sneaky examples from a curated list; counts to practice ledger.
- [x] L-16: Add a faux-ami warning badge on affected Le Champ de Mots farm plots, using the existing type-marker icon system and the faux-amis list built for L-15. (needs L-15 (faux-amis data))
- [x] L-17: Add a Le Champ de Mots 'golden plot' of the day: one random due plot highlighted, correct answer gives double practice score.
- [x] L-18: Add leech detection to Le Champ de Mots: an item failed many times in a row becomes a 'stubborn weed' with a mnemonic prompt, chunked re-teach card or hint to suspend for a while.
- [x] L-19: Add a once-per-session 'that was a slip' button to Le Champ de Mots that undoes a clearly keystroke-error typed answer without penalising the SRS interval.
- [x] L-20: Add an on-screen accent bar (é è ç œ etc.) beside every typed input in Le Champ de Mots, on phones and desktops, working with the existing accent strict/lenient toggle. (partly built: Accent strict/lenient toggle exists (index.html #accent-toggle-checkbox, game.py normalize_answer fold_accents).)
- [ ] L-21: Add a Le Champ de Mots weekly recap card shown once a week: plots watered, best combo, new plots automated, hardest word, with a share image; non-guilt and easy to dismiss.
- [ ] L-22: Add an optional Pomodoro study timer to Le Champ de Mots in the minigames-side file: crops visibly grow while it runs, small practice-score bonus on completion, penalty-free stop button. (you approved 2026-10-07 an explicit exception to Le Champ de Mots' no-animation/no-timer tests: update the test and the CLAUDE.md rule when building, keep it toggleable and reduced-motion safe)
- [ ] L-23: Add a Le Champ de Mots scarecrow mascot with a few discrete (non-eased) reaction poses for combos and weeds, with outfits unlocked by achievements; toggleable. (you approved 2026-10-07 an explicit exception to Le Champ de Mots' no-animation/no-timer tests: update the test and the CLAUDE.md rule when building, keep it toggleable and reduced-motion safe)
- [x] L-24: Add a filter and sort control to the Le Champ de Mots farm grid: weakest first, due today, by type.
- [ ] L-25: Add an opt-in hardcore mode to Le Champ de Mots: strict grading everywhere, no hints, no multiple-choice fallback, with an achievement for a whole week completed under it; keep it optional and hinted.
- [x] L-26: Add Le Champ de Mots player titles (Apprenti, Jardinier, Fermier, Maitre de Ferme) rising with the practice ledger, shown in the header and on shared cards.
- [ ] L-27: Add a session highlight reel to Le Champ de Mots results screens: best combo, quickest answer and toughest word beaten. (Partly done 2026-10-08: best combo and toughest word beaten on the Review and Proficiency results and the dashboard; quickest answer not built because game.py deliberately has no clock.)
- [x] L-28: Add a Le Champ de Mots header exam-countdown widget: days to the entered exam date plus projected coverage, hidden when no date is set. (needs L-9 (exam date and projection))
- [x] L-29: Add a weak-items export to Le Champ de Mots: download flagged items as a CSV or Anki-compatible deck.
- [ ] L-30: Add rotating cosmetic seasonal farm sprites and weather (autumn leaves, snow) to Le Champ de Mots, tied to the real calendar or semester stage and toggled by the visual-style switcher. (needs W-4) (you approved 2026-10-07 an explicit exception to Le Champ de Mots' no-animation/no-timer tests: update the test and the CLAUDE.md rule when building, keep it toggleable and reduced-motion safe)
- [ ] L-31: Restyle Le Champ de Mots achievement cards with warm farm-themed crop/harvest glyphs per earned badge, themed across High-def, Low-poly, Text-based and Cartoon styles, as a restyle not a rebuild.

- [x] GP-1: Mark on every Le Champ de Mots question activity whether it grows plots (user request 2026-10-08): text marker, dashed ring for no, tooltip and aria-label say how or why.
- [x] GP-2: Make more than watering grow plots: proficiency tests credit like Review, the five arcade games give the Review nudge once per plot per day for plots already watered, summaries end with 'Plot growth credited: N plots nudged'. Hand-written sentence modes (bonus, builder, conversation, listening, liaison) do not grow plots and say so.
- [x] GP-3: Tests, changelog entry and an activity-to-growth table in the game's CLAUDE.md.
- [x] GP-4: Watering rule (user request 2026-10-08): the first correct answer per plot per in-game day from any plot-linked activity waters it (full review: interval, ease, streak, stage); later same-day answers nudge at most once; a never-watered plot can be watered by a game or Review. Plain-words explanation at the end of the game's CLAUDE.md.
- [x] GP-5: Water options chooser beyond "water next plot": a chosen week, by topic, wilting first, quick multiple choice, typing, listening, and a per-minigame list, each with a live count of plots it can water.
- [x] GP-6: Every minigame connects to at least two plots per play with a visible "Waters: <plot>" line (audit test added; a Cafe Rush dish that never found its plot was fixed).
- [x] GP-7: Four new minigames (Word Match, Grammar Gaps, Listening Pick, Word Order Race) so every plot has at least one game (592 of 790 plots covered before, 790 of 790 now); coverage table in the game's CLAUDE.md.
- [x] GP-8: Slower / Normal / Faster on all nine minigames, remembered per game; only the game's own score scales (80, 100, 125 percent).
- [x] GP-9: Progressive question format: a never-watered plot is always multiple choice; the typed share rises with growth stage (Sprout 20%, Budding 45%, Blooming 70%, Automated 90%, capped at 95%), deterministic, with an "Always multiple choice" setting.
- [x] GP-10: Grading rules found by the answer-report review (needs game.py changes): STRICT consults each item's curated accepted_en/accepted_fr, slashed answers grade LENIENT, internal punctuation and hyphens ignored, the English side ignores the accent toggle, bonus tiles and sentences honour curated answers (48 xfail tests wait on this).
- [x] LC-1: Fix the unreadable text in Le Champ de Mots: your report (2026-10-07) is "a lot of white on white text and dark on dark". Run a computed-style contrast scan (same method as the earlier light-theme passes) on both the Classic page and the Desktop page, in light and dark themes and in all four visual styles (High-def, Low-poly, Text-based, Cartoon), across the farm, every panel and window, the question flow, the five minigames, the dashboard, Settings and the opening screen; fix every text/background pair under WCAG AA 4.5:1 (3:1 for large text), then add a test that fails on a new pair. Start with the Desktop page's `pc.css` panel backgrounds and the dark-glass top bar and side column, which were written recently and have not been scanned. Known spots you reported (2026-10-07): **the title is white on white**, and **Café Rush's secondary questions show dark text on a dark background in the 'fill in the blank' example**; you said there are many more. (No screenshots yet, so the scan finds the rest.) (Partly done 2026-10-08: root cause was the pale dawn sky behind pale title and stat text; fixed with a dusk-sky override plus arcade, alternate-style and cream-card ink fixes, a regression test and a scan tool in tests/tools. Still open: scan all 16 combinations of style, theme and page, including the Desktop page, and look at the farm selects and narrow row buttons.) (Done 2026-10-09: all 16 combinations scanned; the last six Desktop combinations were not re-scanned after the final CSS edits, which only touch the five selectors fixed.)

## Z. Cross-game patterns (Round 3 answers, 2026-10-07)

- [ ] Z-1: Build shared/seed.py: one seeded-run module every game's randomness routes through, taking a short seed string (e.g. TIDE-K7F2Q), with a 'copy seed' button on run-end screens and a 'start from seed' field on the new-game screen; no backend; roll it out game by game. (Shared module built 2026-10-08 (shared/seed.py and seed.js with copy-seed and start-from-seed UI, tested identical in Python and JS); each game still has to route its randomness through it.)
- [ ] Z-2: Add async challenge links: finishing a seeded run offers 'Challenge a friend' producing a URL that opens the game on the same seed with a 'beat <score>' banner, with a small POST /challenges storing seed/score/username so a 'friend beat you' note shows in Continue Playing; opt-in and friend-only by default. (needs Z-1)
- [ ] Z-3: Add shared ghost runs: a trace recorder saving a compact per-turn key stat into the save state and a ghost-overlay renderer drawing someone else's trace (or the site's median run from the stats endpoints) as a faint line on each game's existing chart; each game opts in with two lines. (needs Z-1)
- [x] Z-4: Add shared per-game leaderboards with a privacy tier: POST /scores and GET /leaderboard/{game}/{board}, entries anonymous by default ('Player 7F2Q') with one account setting to show the username; seeded boards (daily, weekly, all-time) and personal-best rows built once, each game declares board names and a validation function. (needs W-5) (Built with W-5: each game declares a board with one `register_board(...)` call carrying its score bounds, direction, windows and integer flag; personal-best rows are `GET /users/me/scores`. Wiring each game is separate.)
- [ ] Z-5: Add a daily seed for every game: one deterministic seed per UTC date from the date string, a 'Today's run' button on each game's start screen, a hub strip showing which daily runs you have done today, and a no-punishment streak counter. (needs Z-1) (Daily seed built 2026-10-08 (daily_seed in Python and JS, a Today's run button helper, the noyvj-daily-v1 record and a no-punishment streak); the button on each game's start screen and the hub Today strip are still to wire.)
- [ ] Z-6: Add a weekly hub-wide challenge rotation: each week the hub picks one game and one modifier (e.g. 'Herd, no antibiotics', 'SOL, half starting energy') from a shared JSON schedule via one shared modifiers loader; every weekly challenge must be completable in 1-2 hours (your comment), and it pairs with the event-badge system but is a weekly rhythm, not a holiday. (needs Z-1)
- [x] Z-7: Add a shared player profile data model in the account (total time played, achievements per game, favourite game, longest streaks, badges) with a small profile.update() helper each game calls at save time instead of the hub scraping save blobs; the profile page is Y-3. (Partly done 2026-10-09: backend profile table and routes, shared/profile.js helper and the public profile page are built; games do not call NoyvjProfile.update yet: the cleanest place is once in shared/save-widget.js after a successful save.)
- [ ] Z-8: Add cross-game cameo unlocks: a milestone in one game unlocks a tiny cosmetic or flavour item in another (e.g. a Tide tide-pool creature appearing in Drift's ocean), rendered in the receiving game's own art style, with a shared unlocks.json storing only flags.
- [x] Z-9: Add a shared save-schema versioning and migration harness: every save carries schema_version, shared/migrate.py runs a chain of per-game migrations on load with a fixture test loading every historic save shape, and a failed migration shows a 'could not read this save, here is the raw code' screen instead of a silent reset. (Built 2026-10-08: shared/migrate.py with a per-game registry and fixtures for all 15 games; the 'could not read this save' screen belongs in the save widget and is not built.)
- [x] Z-10: Add a save 'time machine' to the save widget: keep the last 5 auto-snapshots (locally, and on the backend for signed-in players) and offer 'restore an earlier state' with timestamps and a one-line summary from each game. (needs backend table)
- [x] Z-11: Build a shared 'smoke everything' test harness that boots each game headlessly (fake-DOM), runs N scripted turns with a random-action fuzzer, asserts no exceptions and no NaN or negative-resource states, and runs all 13 games in one command.
- [ ] Z-12: Add a performance budget: a script measuring each game's Pyodide boot time, first-interactive time and payload size into a table in planning/ (regenerated by hand like the other scripts) that fails loudly over a written budget, plus trying Pyodide package pre-loading/caching in the service worker so repeat visits skip the biggest download. (Partly done 2026-10-08: scripts/measure-perf.py with a --check mode, planning/PERF-BUDGET.md and scripts/perf-budget.json built, baseline taken for all 15 games (cold first-interactive 1.2 to 2.0 s, about 5.4 MB of the 5.7 to 6.1 MB total is Pyodide); still open: service-worker caching of Pyodide, which needs sw.js.)
- [ ] Z-13: Build shared/i18n.js with t("key") and per-language strings.json (English default), convert the shared save widget, confirm dialog, tutorial and achievements panel first, then add a Spanish/French pass for the climate quartet (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift); skip Le Champ de Mots.
- [ ] Z-14: Build a shared replay format (seed plus player inputs, not state) with a read-only replay mode (play/pause/speed) usable for admin bug repro attachments and community highlights; first needs a seeded RNG path in the pilot game. (needs seed module (Z-1 left blank) or minimal per-game seeded RNG; W-2 for speed/pause) [conflict: Depends on Z-1 (seeded runs), which you left blank; the todo folds in a minimal seed path for the pilot game. Also pairs with Z-17.]
- [x] Z-15: Add bronze/silver/gold rarity labels computed from the live earned_pct in shared/achievement-stats.js (thresholds in one place, adjusting as players arrive) and a hidden-achievement flag that reveals the description only after the first player earns it; each game keeps its own icon art. (partly built: shared/achievement-stats.js shows live '% of players' per achievement (old Z27b); no tiers, no hidden achievements in games/*/achievements.json) (needs achievement stats backend (built)) (Built 2026-10-08: Gold at 10% or fewer, Silver at 35% or fewer, Bronze above; set in one table at the top of shared/achievement-stats.js; no achievements.json has a hidden flag yet.)
- [ ] Z-16: Build a pilot co-op world code for Canopy (or Drift): two players share one read-mostly world state, each submits one turn per day, backend merges into a single world state (no websockets); write the merge rules first and park the 1v1 pairing question on W-6. (needs W-6 scoping decision, backend pool/world table)
- [x] Z-17: Add an in-game 'Report a problem' button in the shared widgets that auto-attaches the save code, schema version, browser/viewport and last 20 console log lines with a clear preview of exactly what will be sent, posting to a new /bug-reports endpoint listed on admin.html. (partly built: Hub has site feedback/bug-report form (/feedback, listed in admin.html); Le Champ de Mots answer reports (/answer-reports); Continuum info 'Report an issue' button) (Partly done 2026-10-09: bug_reports table, POST /bug-reports, admin panel and shared/report-problem.js built; not wired into any game page yet.)
- [ ] Z-18: Add a shared opt-in practice-sandbox toggle (game exposes sandbox(): no fail states, all tools unlocked, real save and achievements untouched) starting with Grid, Continuum and Trade Empire; SOL's existing post-endgame sandbox stays as is. (partly built: SOL has a post-endgame cost-free sandbox mode (games/sol/game.py sandbox_mode, A15); none in the rest)
- [x] Z-19: Create shared/a11y.css honouring prefers-reduced-motion and prefers-contrast (calm animations/flashes, stronger borders and text), include it in every game, layered over each game's own motion toggle rather than replacing it. (partly built: Reduced motion exists per game (settings.js, site-settings.js sync, @media in tutorial.js/ambient-bg.css/pc-shell.css); no shared/a11y.css, no prefers-contrast anywhere) (Built 2026-10-08: shared/a11y.css (prefers-reduced-motion and prefers-contrast, layered over each game's own switch, data-motion-essential opt-out), wired into every page. Only Le Champ de Mots (index and pc pages) is still to wire.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-19 SOL
  - [x] Z-19 Canopy
  - [x] Z-19 Grid
  - [x] Z-19 Tide
  - [x] Z-19 Aftermath
  - [x] Z-19 Herd
  - [x] Z-19 Thaw
  - [x] Z-19 Loop
  - [x] Z-19 Drift
  - [x] Z-19 Trade Empire
  - [x] Z-19 Continuum
  - [x] Z-19 Le Champ de Mots
  - [x] Z-19 Signal
  - [x] Z-19 Lexis
- [x] Z-20: Add one shared copy-result-as-text helper (Wordle-style line, e.g. 'Tide, 4,210 pts, 3 storms survived', seed only if the game has one) and call it from the end/summary screen of every game except Signal, which keeps its own. (partly built: Signal has a result-share copy (games/signal/app.js lastShareText); no shared helper, no other game) (Shared helper built 2026-10-08 (shared/copy-result.js); calling it from each game's end screen is still to wire (per-game boxes below).)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-20 SOL
  - [x] Z-20 Canopy
  - [x] Z-20 Grid
  - [x] Z-20 Tide
  - [x] Z-20 Aftermath
  - [x] Z-20 Herd
  - [x] Z-20 Thaw
  - [x] Z-20 Loop
  - [x] Z-20 Drift
  - [x] Z-20 Trade Empire
  - [x] Z-20 Continuum
  - [x] Z-20 Le Champ de Mots
  - [x] Z-20 Lexis
- [x] Z-21: Add shared/perf-mark.js that logs Pyodide boot milestones (script start, pyodide loaded, game setup done, first interactive) via performance.mark and one consistent console format, included by every game. (Built 2026-10-08: shared/perf-mark.js (marks script-start, dom-ready, pyodide-loaded, game-setup-done, first-interactive; one `[noyvj-perf] <game> <mark> <ms>ms` format), wired into every page. Only Le Champ de Mots is still to wire.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-21 SOL
  - [x] Z-21 Canopy
  - [x] Z-21 Grid
  - [x] Z-21 Tide
  - [x] Z-21 Aftermath
  - [x] Z-21 Herd
  - [x] Z-21 Thaw
  - [x] Z-21 Loop
  - [x] Z-21 Drift
  - [x] Z-21 Trade Empire
  - [x] Z-21 Continuum
  - [x] Z-21 Le Champ de Mots
  - [x] Z-21 Signal
  - [x] Z-21 Lexis
- [x] Z-22: Rework the shared save widget: move it to a small top corner control that never overlaps play, start auto-collapsed on every screen size, and show a live 'saved N minutes ago' line that becomes a plain-text warning if the last save attempt (manual or auto) failed. (partly built: shared/save-widget.js: fixed bottom-right 190px box, collapsible; status line shows 'Saved at HH:MM' / 'Save failed — try again'; collapsed by default only on narrow/desktop boot)
- [x] Z-23: Add a shared touch-target stylesheet (min 44px hit areas, touch-action: manipulation) included by every game, then sweep each game's tiny buttons. (Built 2026-10-08: shared/touch-targets.css (44px on phones and touch screens, touch-action: manipulation, an invisible 44px hit area for the round info buttons and the back link; Signal's board cells opt out with data-touch-exempt), measured at 360px across the games. Only Le Champ de Mots is still to wire and sweep.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-23 SOL
  - [x] Z-23 Canopy
  - [x] Z-23 Grid
  - [x] Z-23 Tide
  - [x] Z-23 Aftermath
  - [x] Z-23 Herd
  - [x] Z-23 Thaw
  - [x] Z-23 Loop
  - [x] Z-23 Drift
  - [x] Z-23 Trade Empire
  - [x] Z-23 Continuum
  - [x] Z-23 Le Champ de Mots
  - [x] Z-23 Signal
  - [x] Z-23 Lexis
- [x] Z-24: Add a shared ?debug=1 dev overlay in a corner box showing FPS, state size in bytes and last save payload length, loaded by every game and inert without the flag. (Built 2026-10-08: shared/debug-overlay.js (fps, get_state() size, last /saves body length, heap, lite, errors, boot marks), inert without ?debug=1, wired into every page. Only Le Champ de Mots is still to wire.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-24 SOL
  - [x] Z-24 Canopy
  - [x] Z-24 Grid
  - [x] Z-24 Tide
  - [x] Z-24 Aftermath
  - [x] Z-24 Herd
  - [x] Z-24 Thaw
  - [x] Z-24 Loop
  - [x] Z-24 Drift
  - [x] Z-24 Trade Empire
  - [x] Z-24 Continuum
  - [x] Z-24 Le Champ de Mots
  - [x] Z-24 Signal
  - [x] Z-24 Lexis
- [x] Z-25: Add a shared error boundary script (uncaught Python/JS errors show a friendly 'something went wrong, your save is safe' panel with a copy-details button) included by every game. (Built 2026-10-08: shared/error-boundary.js (one friendly panel with Copy details, Reload and Dismiss; ignores ad, network and ResizeObserver noise; never touches storage), wired into every page. Only Le Champ de Mots is still to wire.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-25 SOL
  - [x] Z-25 Canopy
  - [x] Z-25 Grid
  - [x] Z-25 Tide
  - [x] Z-25 Aftermath
  - [x] Z-25 Herd
  - [x] Z-25 Thaw
  - [x] Z-25 Loop
  - [x] Z-25 Drift
  - [x] Z-25 Trade Empire
  - [x] Z-25 Continuum
  - [x] Z-25 Le Champ de Mots
  - [x] Z-25 Signal
  - [x] Z-25 Lexis
- [x] Z-27: Add a shared achievement Share button that copies a one-line text ('I earned X in Game, N% of players have it') plus the game link, using the live earned_pct, omitting the percentage while suppressed/under-sampled. (needs achievement stats backend (built)) (Shared Share button built 2026-10-08 (shared/achievement-share.js); the script tag per game page is still to add.)
- [x] Z-28: Add a shared pause-when-tab-hidden helper for games with a real-time loop (SOL, Canopy, Trade Empire, Continuum animation), with an on/off toggle in each game's settings; avoid silent simulation advance while hidden. (needs W-2 pause)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-28 SOL
  - [x] Z-28 Canopy
  - [x] Z-28 Trade Empire
  - [x] Z-28 Continuum
- [x] Z-29: Add a shared info/help panel footer showing the game's changelog date, seed (if any) and site URL, so screenshots and printouts are self-identifying; apply to every game's info/help panel. (Built 2026-10-08: shared/info-footer.js adds `NoyvjGames - <game> - updated <changelog date> - [seed] - <site URL>` to #howto-panel and #info-page-panel (a seed shows once Z-1 exposes one via window.NoyvjSeed.current() or NOYVJ_SEED), wired into every page. Only Le Champ de Mots is still to wire.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-29 SOL
  - [x] Z-29 Canopy
  - [x] Z-29 Grid
  - [x] Z-29 Tide
  - [x] Z-29 Aftermath
  - [x] Z-29 Herd
  - [x] Z-29 Thaw
  - [x] Z-29 Loop
  - [x] Z-29 Drift
  - [x] Z-29 Trade Empire
  - [x] Z-29 Continuum
  - [x] Z-29 Le Champ de Mots
  - [x] Z-29 Signal
  - [x] Z-29 Lexis
- [x] Z-30: Add data-testid attributes to the shared components (save widget, confirm dialog, achievements panel, tutorial) and document the naming convention in planning/game-template.md.
- [x] Z-31: Add a hub-wide "Slow computer" toggle (user request 2026-10-08): one switch on the hub (and in the hub settings page, Y-10) stored as `lite-mode` in localStorage and, for signed-in players, synced through shared/site-settings.js. New `shared/lite-mode.js` and `shared/lite-mode.css` set `data-lite` on `<html>` before first paint (also default it on when `navigator.deviceMemory` is 2 or less, `hardwareConcurrency` is 2 or less or `prefers-reduced-data` is set, with a note and an off switch, never silently); CSS then turns off every animation, transition, backdrop blur, animated starfield/ambient background and large shadow site-wide, and a tiny JS API (`NoyvjLite.on()` and a change event) lets games drop their own costs (Continuum's 3D scene frame rate and effects, canvas loops, the Pyodide-side tick animations). Unify with Thaw's own lite mode (G-26) and each game's reduce-motion switch rather than adding a second inconsistent one. Include the two shared files in the hub and every game page (Classic and Desktop) and add a test that every page includes them. (Wiring waits until the Champ and hub-shell agents finish so no game folder has two writers.) (Built 2026-10-08: shared/lite-mode.js + .css (html[data-lite], key lite-mode, automatic slow-device default with a visible note, NoyvjLite API and noyvj-lite-change event, account sync as lite_mode through site-settings.js and the backend whitelist), toggles on the hub nav and settings.html, Thaw's G-26 lite mode and Continuum's 3D scene now use it, tested on every page. Only Le Champ de Mots (index and pc pages) is still to wire.)
  Per game (Classic and Desktop pages both; tick each once wired and tested):
  - [x] Z-31 SOL
  - [x] Z-31 Canopy
  - [x] Z-31 Grid
  - [x] Z-31 Tide
  - [x] Z-31 Aftermath
  - [x] Z-31 Herd
  - [x] Z-31 Thaw
  - [x] Z-31 Loop
  - [x] Z-31 Drift
  - [x] Z-31 Trade Empire
  - [x] Z-31 Continuum
  - [x] Z-31 Le Champ de Mots
  - [x] Z-31 Signal
  - [x] Z-31 Lexis

*Not added: Z-26 (parked in LATER.md at your word, 2026-10-07: shared quiet-mode helper while audio is parked).*

## Y. The hub shell (Round 3 answers, 2026-10-07)

- [x] Y-1: Build the public profile page (profile.html?u=name) on the hub: badges, per-game achievement counts, favourite game, member-since, off by default behind one 'make my profile public' switch (new backend field and endpoint) plus a share-my-profile link. (needs backend profile endpoint (needs owner redeploy))
- [x] Y-2: Add a compact hub 'Today' strip above the game grid: each daily game's seed status (Signal), the weekly rotating challenge, any active seasonal event badge and your current streak, all driven by one admin-edited JSON feed. (needs W-4 seasonal events groundwork)
- [ ] Y-3: Build leaderboards.html on the hub: game picker, board picker (daily/weekly/all-time), opt-in anonymous-by-default rows and a friends-only tab fed by the Y-4 friend list. (needs W-5 general opt-in leaderboards, Y-4 friends list) (partly built 2026-10-08: root `leaderboards.html` with game, board and period pickers, rows, your scores and the username switch, reading `GET /leaderboard`; only the friends tab (Y-4) and a hub nav link and service-worker entry remain.)
- [ ] Y-4: Add an account friends list: add by username with mutual accept, show each friend's last-played line and current streak, and deliver challenge links inline; no messaging at all. (needs backend friends tables/endpoints, Y-1 profile)
- [x] Y-5: Add a 'For you' lobby row for returning players: rule-based (no ML) next-game suggestions from tags, finished games, similar-tag players' finishes and untouched games, always stating the reason ('because you finished Canopy'). (partly built: Onboarding survey and New Player recommendation exist (script.js pickRecommendedGame, Z13/Z19) but only for first-time visitors and with no rule-based 'because you finished X' row.) (needs aggregate stats endpoints (exist)) (Built 2026-10-08; 'finished' is a guess: a signed-in account has at least 60% of a game's achievements, FINISHED_RATIO in hub-foryou.js.)
- [ ] Y-6: Generate per-game hub info pages (static /game/<slug> pages or hash routes) with description, screenshots, average rating, % completed, top achievements, a big Play button and their own title/social card, built by script from game-manifest.json. (needs Y-7 social cards)
- [ ] Y-7: Write a scripts/ Python generator for 1200x630 PNG share cards per game (drawn from existing thumbnails and favicons, no AI imagery) and add Open Graph/Twitter meta to the hub, each game page and the roadmap. (Partly done 2026-10-08: scripts/generate-share-cards.py draws 1200x630 cards for the hub and all 14 games, Open Graph and Twitter meta is on the public hub pages, per-game snippets are in share/meta/; still open: wiring those snippets into each game page.)
- [ ] Y-8: Add a script generating sitemap.xml, robots.txt and VideoGame/WebApplication JSON-LD from game-manifest.json; add Search Console verification file once the owner supplies the token (FOR-YOU entry). (needs owner's Search Console token) (Partly done 2026-10-08: scripts/generate-seo.py writes sitemap.xml, robots.txt and per-game JSON-LD in share/jsonld/, hub JSON-LD inlined; still open: your Search Console token and inlining the per-game JSON-LD. Note robots.txt only counts at the domain root, which this project site does not control, so submit the sitemap in Search Console.)
- [x] Y-9: Add an opt-in 'Download for offline' button per title card that precaches that game's Pyodide bundle and files, with an honest size estimate (navigator.storage.estimate) and a storage-used readout with a remove option. (partly built: sw.js precaches every game shell and caches Pyodide's CDN responses cache-first after first play, but there is no per-game 'Download for offline' button, size estimate or storage readout.)
- [x] Y-10: Build the hub settings page consolidating theme, reduce motion, text scale default, autosave default, analytics opt-in, announcement/tour reset, clear local data, export everything and key bindings (Y-19), reusing site-settings.js. (partly built: Scattered pieces exist: theme toggle in nav, account-synced theme/text scale/reduced motion (shared/site-settings.js), analytics opt-in (hub_pageview_opt_in), tour restart button; no settings page.)
- [ ] Y-11: Add a hub community activity feed of anonymised, rate-limited event lines generated from the stats tables (no free text); players can opt in to show their username in lines, linking to their public profile. (needs Y-1 profile, backend activity endpoint)
- [x] Y-12: Build events.html: current holiday event, countdown, per-event badge gallery (missed ones greyed with 'returns next year') and links to participating games' event modes, with one events.json driving both the page and profile badges. (needs W-4 seasonal events groundwork, N-2, Y-1)
- [x] Y-13: Extend admin.html (still direct-URL, owner-gated) with daily plays, signups, saves, feedback and bug-report sparklines from GROUP BY date endpoints, a top-errors-this-week table and a feedback moderation queue (feedback has is_hidden). (partly built: admin.html has aggregate stats and answer-report triage (Mark done/Reopen); no time-series, no sparklines, no errors table, no feedback moderation queue.) (needs backend admin time-series endpoints)
- [x] Y-14: Add account settings controls to download everything the server holds (saves, achievements, feedback, profile) as JSON and to permanently delete the account with confirmation, and update terms.html to match. (needs backend export/delete endpoints)
- [x] Y-15: Build a searchable Help/FAQ page (saves, autosave, why accounts, moving devices, what is stored) reusing the lobby search index, and add each repeated feedback question as a permanent answer. (Built with 22 answers checked against the code; repeated feedback questions get added to help-data.json as they come up.)
- [x] Y-16: Polish the hub as a mobile app shell: bottom nav bar on phones (Games/Today/Profile/More), pull-to-refresh via service-worker revalidate, and safe-area padding for installed-PWA mode. (needs Y-2 Today strip, Y-1 profile (for the nav targets)) (Built 2026-10-08 without a Profile target because no profile page exists.)
- [ ] Y-17: Let signed-in players pin 'tell me when this game updates' and surface it as a badge on the What's New link and their profile, reusing the new-since-visit logic (shared/whats-new-banner.js); no push or email. (needs Y-1 profile)
- [x] Y-18: Add personal game collections stored in the account (e.g. cozy, play on phone, class evidence) with a lobby filter, without changing the shared tags. (Built 2026-10-08 on this device only: syncing to the account needs a whitelisted collections key in shared/site-settings.js and the backend settings validation.)
- [x] Y-19: Add hub keyboard shortcuts ('/' focus search, g then r roadmap, '?' list) matching the Z4 convention, and let players rebind them in the settings page (Y-10). (needs Y-10 settings page)
- [ ] Y-20: Add a 'copy my site stats' button to the profile producing a line like '12 games, 87 achievements, joined Sept 2026'. (needs Y-1 profile)
- [x] Y-21: Add a <noscript> and old-browser/WebAssembly fallback message to the hub explaining what needs JavaScript/WebAssembly, with plain links to every game.
- [x] Y-22: Add a per-card estimated session length chip (5 min / 20 min / long-form) read from a manual field in game-manifest.json, filterable in the lobby and feeding the onboarding quick-vs-deep preference. (Session lengths live in game-sessions.json, my estimates: confirm them.)
- [ ] Y-23: Add a small caption under the lobby sort dropdown showing each sort's current leader (top rated, most saved, most played). (needs most-played stat from stats endpoints) (Partly done 2026-10-08: caption shows top rated and most saved; no per-game 'most played' stat exists on any endpoint so that leader is not shown.)
- [x] Y-24: Add a 'was this helpful?' thumbs up/down to each What's New entry, stored in the feedback table with the entry id (new nullable column or tagged field), and show the tallies on admin.html. (needs backend feedback entry-id field)
- [x] Y-25: Add an offline banner on the hub driven by navigator.onLine that greys out uncached game cards instead of letting them fail.
- [x] Y-26: Skip the hub's stats/community endpoint fetches when navigator.connection.saveData is on, quietly by default, with a 'reduce data' note in settings (Y-10). (needs Y-10 settings page)
- [x] Y-27: Add a lightweight /health endpoint and a footer site-status dot (green/amber) with a one-line explanation of why ratings/saves may be unavailable. (needs backend /health endpoint)
- [ ] Y-28: Add a print stylesheet for the achievements dashboard and profile pages (clean black-on-white list with progress bars) reusing shared/print-summary.css. (needs Y-1 profile (for the profile half)) (Partly done 2026-10-08: the achievements dashboard prints cleanly with a Print button; the profile half waits for Y-1.)
- [x] Y-29: Add a credits & thanks section (tools, fonts, Pyodide, consenting named playtesters) separate from sources.html, linked from the hub footer and from every game's home/opening screen. (Partly done 2026-10-08: credits.html listing only what the site really uses, linked from the hub footer; still open: the link from every game's home and opening screen.)
- [x] Y-30: Auto-fill the terms/privacy 'last verified' line from the file's git date via a scripts/ generator and link a short 'what changed' list.
- [x] Y-31: Add a rating summary endpoint (average and count per game slug) and make the hub read it instead of downloading every rating row for each game on load (found by the backend QA pass: `GET /ratings/{slug}` returns every row and grows with every rating; the hub fires one per game).

---

## R. Returning later (your re-decisions)

Dropped or parked: audio items R1-R8 (revisit round 6), R24 and R26 (Thaw/Drift in-game reset: no), R32 (Thaw counterfactual tour: later), R34 (riven column: ask round 6), R37 (Silk Road: no), R38 (Contraption: later, explanation in FOR-YOU), R12 and R14 (keep as built), R16/R17/R35/R36 (nothing to decide; clean the stale entries).

- [x] R-9: SOL "+X since last save" delta readout after loading.
- [x] R-10: SOL personal-best fastest full playthrough timer.
- [x] R-11: SOL "never touched automation" pure-clicker achievement (kept easy).
- [ ] R-13: Continuum full-playthrough integration test (Tribal to Space Age; engineering task).
- [x] R-19: Tide endgame visual flourish.
- [x] R-22: Herd prestige layer (the succession system built as F25 may already cover this: confirm and close).
- [x] R-23: Herd intro blurb that reacts to the methane level.
- [ ] R-27: Canopy compare standing value against the site-wide average (the stats backend now exists).
- [x] R-28: Grid "grid twin" (built as the shadow grid; you said pick, maybe late-game: confirm and close).
- [x] R-29: Tide multi-settlement (built as the sister settlement; confirm and close).
- [ ] R-30: Tide shared coastline community stat (needs W-6 scoping).
- [ ] R-31: Aftermath mutual-aid network positive event (needs W-6 scoping).
- [ ] R-33: Continuum peer-city ghost overlay (needs W-6 scoping).
- [x] R-39: Write the multiplayer scoping document (= W-6).
- [ ] R-clean: remove the stale `planning/LATER.md` entries for R16, R17, R35, R36 and the items now built.

---

## SW. Site work that landed after 2026-09-27 without a list entry (added 2026-10-07, all done)

- [x] SW-1: Whole-site audit 2026-09-27 and its fixes (`planning/AUDIT-260927.md`; fixes `3392b49`, `eb0517d`).
- [x] SW-2: Roadmap site-level milestones table rewritten to cover everything shipped; Roadmap and What's New revalidate on load and keep the Warframe tracker off public pages (`2c79355`, `920202f`).
- [x] SW-3: Service worker revalidates same-origin requests and precaches past the HTTP cache, which fixed stale files after deploys (`ad35c59`).
- [x] SW-4: Backend starts even when the database is unreachable and retries schema setup, after the 4 Oct outage where every route returned 404 (`2a8427e`).
- [x] SW-5: Playtest audit 2026-10-06 and its fixes (`planning/AUDIT-261006.md`, `14980b8`): blanket `[hidden]` rule, collapsed save widget on phones, compact toggles, install banner after the survey.
- [x] SW-6: Owner-only pages (admin, ideas, Warframe tracker) gated to the `noyvj` account through `GET /users/me`, plus the hub's "Owner only" nav dropdown (`7107480`, `fd738a5`, `002ff55`).
- [x] SW-7: Ideas answer sheet `ideas.html` with its generator, answers synced to the owner account, and a "For you" round built from FOR-YOU.md (`a63e3b8`, `1d8a11c`, `b5e4ba9`).

## PC. PC version of every game, the Desktop boot (plan `planning/PC-VERSION-PLAN.md`, guide `planning/PC-GAME-CONVERSION-GUIDE.md`)

Classic stays the default boot (`index.html`); Desktop is a second boot (`pc.html`) sharing `game.py` and saves. Continuum's Classic page must not break (class deliverable).

- [x] PC-1: Plan and conversion guide, decisions recorded (layout and feel only, separate boots, shared saves).
- [x] PC-2: Shared shell, layout switch, config-driven generator and generic tests (`shared/pc-shell.*`, `shared/layout-pref.js`, `scripts/generate-pc-pages.py`, per-game `pc-config.json`).
- [x] PC-3: Continuum Desktop (the pilot): HUD chips with trend dropdowns, Menu window, draggable windows, composite windows.
- [x] PC-4: Tide Desktop.
- [x] PC-5: Canopy Desktop.
- [x] PC-6: Grid Desktop.
- [x] PC-7: Herd Desktop.
- [x] PC-8: Thaw Desktop.
- [x] PC-9: Aftermath Desktop.
- [x] PC-10: Drift Desktop.
- [x] PC-11: Loop Desktop.
- [x] PC-12: Signal Desktop.
- [x] PC-13: Trade Empire Desktop.
- [x] PC-14: Le Champ de Mots Desktop (agent-built, reviewed, committed 084a60b; offline cache worker version 27).
- [x] PC-15: SOL Desktop. Same state as PC-14 (722 tests pass, uncommitted, stopped mid-build).
- [x] PC-16: Screenshots of every Desktop game sent to you (2026-10-08, 14 games at 1440x900, first load, light theme; Thaw and Continuum were shot from the last commit because their working-tree files were mid-edit). Chronicle has no Desktop boot yet (CH-13).
- [ ] PC-18: Fix whatever you say feels wrong in the Desktop screenshots (say which game and what), then re-send screenshots of the changed games. Controller support: not yet; audio stays parked.
- [x] PC-17: Fix SOL's research node buttons staying greyed out as Iron accumulates (Classic bug found by the Desktop agent: `update_research_node_list()` only runs on events, not as Iron grows). Needs a light update of the `disabled` flags in the tick path, not a full list rebuild every tick (that would swallow clicks); then drop the workaround in `games/sol/pc.js`.

## LX. Lexis (language-deduction puzzle game; plan `planning/lexis-plan.md`, game in `games/lexis/`)

- [x] LX-1: Groundwork plan with your decisions (deduction first, story as the pull, sci-fi, three languages growing to five, a ladder from pulses to compound glyphs).
- [x] LX-2: Milestone 1, engine core (Pulse language, parser, world, scenes, deducibility checker, notebook, `handle(json)`).
- [x] LX-3: Milestone 2, first playable screen.
- [x] LX-4: Milestone 3, the Compound language (rung 2) and its deducibility checker.
- [x] LX-5: Milestone 4, planet 2 in the view and the contact goals.
- [x] LX-6: Milestone 5, achievements, save widget, tutorial and opening screen.
- [x] LX-6b: Your answers 2026-10-07: go with the recommendations (hints are in-world, such as asking someone to repeat slowly, with no answer-giving button; working title stays Lexis). Noy2 continues Lexis this round.
- [x] LX-7: Milestone 6, the bridge language (rung 3: plural, negation, question markers).
- [x] LX-8: Milestone 7, story spine and ending, Info page with real-linguistics sources read live.
- [x] LX-9: Milestone 8, hub registration (card, thumbnail, favicon, offline cache), polish, accessibility pass, light theme, Desktop boot.

## CH. Chronicle (history game built from expandable sets; plan `planning/chronicle-plan.md`)

- [x] CH-1: Groundwork plan (one engine, each topic a data pack, sourced claims with confidence levels, review page before a set ships).
- [x] CH-2: Your answers recorded in the plan (2026-10-07): general players, timeline builder then cause web, American presidents first, three reputable sources linked per claim, a report-a-problem button on every claim, one game with a set picker. Noyvj session builds it; Noy2 finishes the first Lexis milestones this round.
- [x] CH-3: Milestone 1, set format, loader and validation tests (every claim needs three sources, dates, no contradictions), a tiny sample set.
- [x] CH-4: Milestone 2, the timeline builder mechanic and engine, playable on the sample set.
- [x] CH-5: Milestone 3, the collectible archive and progress save; save widget, achievements, tutorial, opening screen.
- [ ] CH-6: The report-a-problem feature: a button on every claim, a backend table and routes (same pattern as Le Champ de Mots' answer reports), and a list on the admin page where you mark each report done.
- [x] CH-7: Milestone 4, the cause web mechanic.
- [x] CH-8: Milestone 5, myth or record, plus the Info page showing the three sources for every claim.
- [x] CH-9: Milestone 6, "whose account?" source evaluation.
- [x] CH-10: Milestone 7, spaced review and decision points.
- [ ] CH-11: Milestone 8, author the American presidents set in full (three sources per claim, a review page, then your review), balanced and non-partisan.
- [ ] CH-12: Milestone 9, second and third sets (history of food, Ancient Greece) and the set picker.
- [ ] CH-13: (Note: `scripts/generate-last-updated.py` adds chronicle to `game-manifest.json`; it was removed by hand until the game is hub-registered, so re-run the script then.) Milestone 10, polish, accessibility pass, hub registration, Desktop boot.

## IA. Ideas answers (waiting on you)

- [x] IA-1: Ideas answers: Round 3 is fully answered and processed (answers written into the Round 3 doc, yes items added in the sections above, later items in `LATER.md`, no items dropped). Round 2's typed answers are committed in its doc. Add the next round here when you finish it.

---

## UX. User-reported problems (2026-10-07, in the user's own words where short; fixing now with agents, one owner per file set)

- [x] UX-1: Canopy on mobile: the pinned bars (HUD, action dock, save widget, floating pills) cover nearly the whole screen and make it hard to play. Cap what is pinned, make it collapsible or smaller, and check at 360 and 390px wide. (`games/canopy/`)
- [x] UX-2: Multiple saves are not working (three slots per account, the shared save widget). Reproduce, find the cause, fix, add a test. (`shared/save-widget.js`)
- [x] UX-3: Canopy "Move between plots" (arrow keys) does not work on desktop. (`games/canopy/`)
- [x] UX-4: Canopy "Reset Session" does nothing, at least with two saves saved. (`games/canopy/`, may involve the shared save widget)
- [x] UX-5: Canopy's desktop side column has too much scrolling. Tighten it so the common actions fit without scrolling at 1440x900 and 1024x700. (`games/canopy/`)
- [x] UX-6: With multiple saves, the bars (opening screen or save widget) go off-screen when there is a save to load. (`shared/opening-screen.js`, `shared/save-widget.js`)
- [x] UX-7: Make "Your saves" on the hub collapsible (remember the choice). (hub `index.html`, `script.js`, `style.css`)
- [x] UX-8: Every game gets a way back to its own main page (the opening screen: Continue, New Game, Saves, Settings), and that main page gets a way to the hub. (`shared/opening-screen.js`, one shared control)
- [x] UX-9: Feedback entries get a "this is a test, hide it" toggle in admin, like accounts have, so test feedback can be hidden without going into the backend. (`admin.html`, `app/`)

## QA. Quality passes: code review, bug check, bloat cleanup and load time for everything (user request 2026-10-08)

One checkbox per pass per area. A pass is not done until its fixes are committed with tests green and its findings (fixed, deferred and why) are written in the dev log. Run these after the big feature waves land; do the hub, backend and shared passes first because every game depends on them. Never weaken a test to make a pass finish; if a rule looks wrong, ask in FOR-YOU.

- [ ] QA-1: Code review for every game and the site: read the whole thing as a reviewer: correctness bugs, risky patterns, duplicated logic, unclear names, missing tests for important rules; fix what is clearly wrong and list what needs a decision.
  - [ ] QA-1 SOL
  - [ ] QA-1 Canopy
  - [ ] QA-1 Grid
  - [ ] QA-1 Tide
  - [ ] QA-1 Aftermath
  - [ ] QA-1 Herd
  - [ ] QA-1 Thaw
  - [ ] QA-1 Loop
  - [ ] QA-1 Drift
  - [ ] QA-1 Trade Empire
  - [ ] QA-1 Continuum
  - [ ] QA-1 Le Champ de Mots
  - [ ] QA-1 Signal
  - [ ] QA-1 Lexis
  - [ ] QA-1 Chronicle
  - [x] QA-1 The hub (index.html, script.js, style.css and the root pages)
  - [x] QA-1 The backend (app/)
  - [x] QA-1 Shared components (shared/)
  - [ ] QA-1 Scripts and test infrastructure (scripts/, shared/tests, every game's tests/ folder)
  - [ ] QA-1 The service worker and offline behaviour (sw.js)
  - [ ] QA-1 Planning docs and dev logs (stale or duplicated text)
- [ ] QA-2: Bug check for every game and the site: hunt for real bugs: play it end to end in a browser in Classic and Desktop at 1440x900 and 360x740, in both themes, try odd inputs, old and hand-edited saves, resets, undo, rapid clicks, a hidden tab and a slow device (lite mode); write a regression test for each bug found.
  - [ ] QA-2 SOL
  - [ ] QA-2 Canopy
  - [ ] QA-2 Grid
  - [ ] QA-2 Tide
  - [ ] QA-2 Aftermath
  - [ ] QA-2 Herd
  - [ ] QA-2 Thaw
  - [ ] QA-2 Loop
  - [ ] QA-2 Drift
  - [ ] QA-2 Trade Empire
  - [ ] QA-2 Continuum
  - [ ] QA-2 Le Champ de Mots
  - [ ] QA-2 Signal
  - [ ] QA-2 Lexis
  - [ ] QA-2 Chronicle
  - [x] QA-2 The hub (index.html, script.js, style.css and the root pages)
  - [x] QA-2 The backend (app/)
  - [x] QA-2 Shared components (shared/)
  - [ ] QA-2 Scripts and test infrastructure (scripts/, shared/tests, every game's tests/ folder)
  - [ ] QA-2 The service worker and offline behaviour (sw.js)
  - [ ] QA-2 Planning docs and dev logs (stale or duplicated text)
- [ ] QA-3: Bloat cleanup for every game and the site: remove dead code, unused CSS rules and ids, duplicate helpers, stale feature flags, abandoned experiments and oversized comments; shrink files without changing behaviour (tests must stay green); report bytes before and after.
  - [ ] QA-3 SOL
  - [ ] QA-3 Canopy
  - [ ] QA-3 Grid
  - [ ] QA-3 Tide
  - [ ] QA-3 Aftermath
  - [ ] QA-3 Herd
  - [ ] QA-3 Thaw
  - [ ] QA-3 Loop
  - [ ] QA-3 Drift
  - [ ] QA-3 Trade Empire
  - [ ] QA-3 Continuum
  - [ ] QA-3 Le Champ de Mots
  - [ ] QA-3 Signal
  - [ ] QA-3 Lexis
  - [ ] QA-3 Chronicle
  - [x] QA-3 The hub (index.html, script.js, style.css and the root pages)
  - [x] QA-3 The backend (app/)
  - [x] QA-3 Shared components (shared/)
  - [ ] QA-3 Scripts and test infrastructure (scripts/, shared/tests, every game's tests/ folder)
  - [ ] QA-3 The service worker and offline behaviour (sw.js)
  - [ ] QA-3 Planning docs and dev logs (stale or duplicated text)
- [ ] QA-4: Load time optimization for every game and the site: measure Pyodide boot, first interactive and payload with scripts/measure-perf.py (Z-12), then cut what is slow: lazy-load rarely used panels and big data files, avoid reading and parsing big JSON up front, defer non-critical scripts, compress or inline tiny assets, trim the precache list to what is needed, and record before and after numbers in planning/PERF-BUDGET.md.
  - [ ] QA-4 SOL
  - [ ] QA-4 Canopy
  - [ ] QA-4 Grid
  - [ ] QA-4 Tide
  - [ ] QA-4 Aftermath
  - [ ] QA-4 Herd
  - [ ] QA-4 Thaw
  - [ ] QA-4 Loop
  - [ ] QA-4 Drift
  - [ ] QA-4 Trade Empire
  - [ ] QA-4 Continuum
  - [ ] QA-4 Le Champ de Mots
  - [ ] QA-4 Signal
  - [ ] QA-4 Lexis
  - [ ] QA-4 Chronicle
  - [x] QA-4 The hub (index.html, script.js, style.css and the root pages)
  - [x] QA-4 The backend (app/)
  - [x] QA-4 Shared components (shared/)
  - [ ] QA-4 Scripts and test infrastructure (scripts/, shared/tests, every game's tests/ folder)
  - [ ] QA-4 The service worker and offline behaviour (sw.js)
  - [ ] QA-4 Planning docs and dev logs (stale or duplicated text)


## FY. Answered in FOR-YOU on the ideas sheet (2026-10-08)

- [ ] FY-1: Grid C6: let a player save two scenarios and overlay their trend graphs for a side-by-side comparison (you said now).
- [x] FY-2: Tide D10: show the acidity from three seasons ago right next to the current acidity so the delayed link is visible as numbers (you said now).
- [ ] FY-3: Aftermath E5: add another event category beyond weather and non-weather (for example a heat-mortality event) to the fixed seven-event schedule (you said now).
- [ ] FY-4: Herd F4: a second end-of-game feedback question about Herd's own lesson ("did decoupling feel like a real strategy, or a tax on growth?"), like Thaw's two-question pattern (you said now).
- [ ] FY-5: Loop H16: an optional "supply chain disruption" random event, opt-in as an advanced mode, kept apart from the deterministic core lesson (you said now).
- [x] FY-6: Contraption (physics sandbox): DROPPED by you 2026-10-08.
- [ ] FY-7: One shared compact run-code format (you said yes): friends paste a code to view a ghost; built once in `shared/` and then used by Loop GH-28 and H-7, Tide D-3 and Grid C-29.
- [x] FY-8: Read the 3 new Le Champ de Mots answer reports that arrived after the first review (a10db191 "the road" for "the street"; 4f38d109 and 8295f0aa on the "Is it far/close (from here)?" phrase) and tick "fixed" on the ones the data fixes.
- [ ] FY-9: U1: Undersleep: should the optional daily check-in layer be hidden until the player turns it on (you said yes: yes, hidden by default ("Just play" is the default).)
- [ ] FY-10: U2: Undersleep: keep the player's personal data on the device only, with manual export and import, and never in a save code or the cloud (you said yes: yes. A cloud version needs per-account encryption, which is a real project; say "later" if you want that project eventually.)
- [ ] FY-11: Ch1: Chronicle: after you spot-check the sample set, may I author the full American presidents set (three sources per claim) (you said yes: yes, then the history of food and Ancient Greece as sets 2 and 3.)
- [ ] FY-12: Ch7: Chronicle: when it is ready, should Chronicle go on the hub (card, thumbnail, favicon) now, or wait until the presidents set is fully authored (you said yes: wait until the full presidents set is done.)
- [ ] FY-13: Lexis: keep growing it toward the Large size (planets 4 and 5). Your answer was 'no' with "Continue to grow it.", which I read as: keep growing it, no separate stop. [question: tell me if you meant not to build planets 4 and 5]
- [x] FY-14: Le Champ de Mots: when a question asks for just the word, do not require its le/la (you said no to requiring it: "Don’t require it when just asking for the word").
- [ ] FY-15: Be1: Backend: how many proxies does FastAPI Cloud put in front of the app (you said yes: leave as is unless you see abuse.)
- [x] FY-16: Be2: Backend: reject the username noyvj at signup unless an owner environment variable is set (you said yes: yes.)
- [x] FY-18: Be4: Hub: remove the Google ads script (placeholder client id) from the hub until your AdSense account is approved (you said yes: yes, and I put it back when you give me the id.)
- [ ] FY-19: Ti1: Tide: build a Tide Workshop (sliders for starting funds, lag length, sea-level rate, surge size) with runs labelled "custom rules" and never ranked (you said yes: yes.)
- [ ] FY-20: Ti2: Tide: may I choose the named coastline scenarios myself (three invented coasts: low delta, cliff bay, barrier island, with plain traits) (you said yes: yes, my call.)
- [ ] FY-21: Ti3: Tide: add a living harbor scene (a harbor picture drawn in code that reflects acidity and fish, with an off switch) (you said yes: yes.)
- [ ] FY-22: Ti4: Tide: give technical words (acidity, lag) plainer labels with the science in a tooltip (you said yes: yes.)
- [ ] FY-23: Ti5: Tide: show achievements as medal cards (shape plus text) instead of a plain list (you said yes: yes.)
- [ ] FY-24: Gr1: Grid: should retiring a plant ask for confirmation only when it is the last plant? (Retiring any other plant already skips confirmation.) (you said yes: yes, last plant only.)
- [ ] FY-25: Gr2: Grid: may the scenario builder share scenarios through the shared run-code format (you said yes: yes.)
- [ ] FY-26: Gr3: Grid: build the R&D lab as part of an upgrade tree (you suggested a tree over a roguelike earlier) (you said yes: yes.)
- [ ] FY-27: Gr4: Grid: build neighbour trading with computer-controlled neighbours only (no real players) (you said yes: yes.)
- [ ] FY-28: Gr5: Grid: build storm prep as a short preparation step before a storm with small costs (you said yes: yes.)
- [ ] FY-29: He1: Herd: may I choose the balance values for the new mechanics myself and tell you afterwards (you said yes: yes.)
- [ ] FY-30: He2: Herd: may I write the branching story as a short original story with three branches, with real-world facts only in the info panel (you said yes: yes.)
- [ ] FY-31: He3: Herd: how much should the minigame affect results (you said yes: a small bonus capped at about 5% of a round's funds.)
- [ ] FY-32: He4: Herd (and Aftermath, Thaw): mark runs that use custom rules as "unranked" and keep them off leaderboards (you said yes: yes.)
- [ ] FY-33: Th1: Thaw: show real-world gigatonne carbon figures only if I read them live and name the source on screen (you said yes: yes.)
- [ ] FY-34: Af1: Aftermath: add a fog mode (events hidden until they arrive) as an optional hard mode, since it conflicts with the forecast features (you said yes: yes, optional.)
- [ ] FY-35: Af2: Aftermath: put the scenario and modifier options into one "modifiers" menu (you said yes: yes.)
- [ ] FY-36: Lo1: Loop: build trading cards with short real-world facts about each material, read live and named on screen (you said yes: yes.)
- [ ] FY-37: Lo2: Loop: add market shocks as a deterministic scheduled mode (no randomness) (you said yes: yes.)
- [ ] FY-38: Lo3: Loop: add a simple computer rival chain you compare against (you said yes: yes.)
- [ ] FY-39: Lo4: Loop: add rewind (like Drift's) now and autopilot later (you said yes: rewind yes, autopilot later.)
- [ ] FY-40: Dr1: Drift: merge the two overlapping ideas (a personality system and a civic-milestone system) into one (you said yes: yes.)
- [ ] FY-41: Dr2: Drift: may I draw the skins, building pop-ups and route glyphs myself as simple code-drawn graphics (you said yes: yes.)
- [ ] FY-42: Te1: Trade Empire: may I add a Blackout mode badge to the shared opening screen (you said yes: yes, small.)
- [ ] FY-44: Co1: Continuum: write the advisor council, notable citizens and citizen of the season as original fictional characters, with real-world facts only sourced and named on screen (you said yes: yes.)
- [ ] FY-45: Co2: Continuum: build neighbouring settlements as computer-controlled neighbours first, before any multiplayer (you said yes: yes.)
- [ ] FY-46: Ca1: Le Champ de Mots: add coins earned from watering that unlock cosmetic skins (you said yes: yes, cosmetic only.) (Partly done 2026-10-09, see L-1.)
- [x] FY-47: Ca2: Le Champ de Mots: add a false-friends set, built from a reputable list read live and named on screen (you said yes: yes.)
- [ ] FY-49: So1: SOL: may I write the balance for prestige mutators myself (you said yes: yes.)
- [ ] FY-50: So2: SOL: build the anomaly system on a fixed schedule rather than random (you said yes: yes.)

- [ ] FY-51: Lifeline-style choose-your-own-adventure game (you said yes): sci-fi, dark tone, many branching paths, optional reading, a main character who makes mistakes; plan first (planning file, M convention), built after Chronicle.
- [ ] FY-52: A coding or logic-circuit puzzle game as the first of the coding, maths and chemistry games (you said yes); plan first.
- [ ] FY-53: One shared "three goals at all times" panel (you said yes) built in `shared/` and fed by each game's own goals, then wired into SOL, Trade Empire, Continuum and Loop.
- [ ] FY-54: One small optional fast timed reaction game with a slower mode like the Champ minigames (you said yes); plan first.
- [ ] FY-55: Optional friend ties (shared run codes, friend list, ghost runs, no messaging, never required, no worst-score shaming) after the shared run code FY-7 exists (you said yes).
- [ ] FY-56: Dream game (the dark foggy forest city builder): you want a large set of design questions answered before any planning doc. The 25 questions are FOR-YOU items Fg1 to Fg25; write `planning/<name>-plan.md` only after they are answered, and consider building the per-building puzzles as their own small games first.
- [x] FY-57: Design principle recorded (you said B and D): steady progress that can never be lost, and routines you know by heart, are what feels relaxed; calm modes lean on those. Written in `planning/PLAYER-PROFILE.md`.
- [x] FY-58: Standing rule recorded (you said yes): no all-good hero characters who never make a mistake. Written in `planning/PLAYER-PROFILE.md`.

## Closing tasks

- [ ] C-1: Archive this list when every item is checked off or moved (same rule as before) and start a fresh one.
