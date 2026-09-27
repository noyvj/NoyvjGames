# Site-Wide TODO (round 3)

**Progress: 38/109 items checked off (34.9%).** Recompute with `grep -c "^\s*- \[[ x]\]" planning/TODO.md` (total) and the same with `\[x\]` (done) as items land.

Built from your answers in `planning/IMPROVEMENT-IDEAS-ROUND-3.md` (Part 4). Only the sections you have answered so far are here: **GB** (Canopy gamified), **M** (new games), **N** (seasonal events), **O** (Trade Empire and Continuum replayability), **P/Q/S/T** (Signal, Undersleep, Overclock, Last Line open questions), **X** (Warframe tracker) and **R** (returning later). GC-GI, A-L, U, Z and Y are unanswered and wait for you. The previous list is archived at `planning/todo-archive/260914_260927.md`; anything from it that was moved here is marked "moved" there.

Rules carried over: "yes" items are here, "later" items are parked in `planning/LATER.md`, "no" items are dropped, questions only you can answer are in `planning/FOR-YOU.md`. Every real-world fact in a feature is read from a live source and named on screen. Nothing is pushed by the AI sessions.

---

## Standing decisions from your Round 3 answers (apply everywhere)

- **Audio:** not being considered; ask again around round 6 (R1-R8 all dropped for now).
- **Roguelikes and card games:** you do not like them, so anything in that genre (Canopy Expedition mode, Overclock) is built on my judgment without expecting your input, kept honest and fun rather than polished to your taste.
- **Level select:** for games that are getting complex, add a level select where every 5 levels is either a game mode or a new mechanic; mechanics that do not belong in the base game (Canopy's poachers and storm fronts) live there.
- **Fast-forward and pause:** wanted in most games that are not turn-based.
- **Skill-tree progression:** where a game has meta-progression (Canopy's Seed Vault, idle crews), build it as a skill tree.
- **Leaderboards:** build them generally, always opt-in (the leaderboard backend from tonight is the base).
- **Events (N):** real big-date events (Christmas, Halloween, New Year, Easter, Hanukkah, Thanksgiving, 4th of July, Valentine's Day and other big ones, internationally inclusive), doable within about 15 minutes of starting a game, with a temporary date-tied stand-in event for games with no natural fit.

---

## W. Cross-game groundwork these answers need (build once, reuse)

- [ ] W-1: **Level select framework** (shared component plus per-game level list): a level-select screen where every fifth level is a game mode or a new mechanic; used first by Canopy (GB-13, GB-15, GB-16) and then offered to other games that are getting complex.
- [ ] W-2: **Fast-forward (1x/2x/4x) and pause** for the real-time (ticking) games: audit which games tick (SOL, Canopy, Tide? Continuum has speed controls already) and add the same control to those that lack it, without touching tick math.
- [ ] W-3: **Skill-tree component** (shared UI and data shape) for meta-progression, first user Canopy's Seed Vault and ranger crews (GB-10, GB-26), later Trade Empire's charter tree (O-1).
- [ ] W-4: **Seasonal events groundwork** (`shared/seasonal-events.js` per Round 3 section N item 11): date-window check, flavour overrides, banner, badge grant through the achievements path, no new backend.
- [ ] W-5: **General opt-in leaderboards**: extend `app/leaderboards.py` boards beyond the three built tonight, and a shared widget entry per game (the shared `leaderboard.js` already exists); used by Canopy's community plot (GB-19), Last Line and Signal.
- [x] W-6: **Multiplayer scoping document** (R-39): write `planning/MULTIPLAYER-SCOPING.md` covering what the parked community items need (shared coastline, mutual aid, peer-city ghost, 1v1 modes such as Canopy's rival company), so you can decide the pass.

---

## GB. Canopy, gamified (all 30 answered)

- [ ] GB-1: Wildfire season (opt-in via the difficulty select).
- [ ] GB-2: Golden seedling pop-up.
- [ ] GB-3: Expedition mode (roguelike run of 12 seasons with boons and a shareable seed), built as a separate game mode on my judgment.
- [ ] GB-4: Tend action with cooldown (hotkey T).
- [ ] GB-5: Neighbour synergy layout puzzle.
- [ ] GB-6: Species on replant (pioneer pine, hardwood oak, orchard).
- [ ] GB-7: Blight in monocultures (needs GB-6).
- [ ] GB-8: Hidden Heart Tree secret.
- [ ] GB-9: Ranger contracts board.
- [ ] GB-10: Seed Vault meta-progression (skill-tree style, per W-3).
- [ ] GB-11: Fast-forward toggle (1x/2x/4x) plus pause (per W-2).
- [ ] GB-12: Rival logging company, as a possible 1v1 game mode (design it as a mode; park the 1v1 pairing on W-6).
- [ ] GB-13: Poacher whack-a-mole, as a level/mode via the level select (not in the base game).
- [ ] GB-14: Forest name and adopted-tree nickname with log narration.
- [ ] GB-15: Storm front events, as a level/mode via the level select.
- [ ] GB-16: Forest spirit narrator, as a story level.
- [ ] GB-17: Challenge run set (Pacifist, Scorched Start, Sprint, No-Highland) with badges.
- [ ] GB-18: Undo window after Clear.
- [ ] GB-19: Daily community forest: everyone's play waters one big community plot, with a shared "best day" and an opt-in investment leaderboard (uses the community pools backend from tonight and W-5).
- [ ] GB-20: Rare conditional wildlife in the wildlife log.
- [ ] GB-21: Timber gambler clear-cut option.
- [ ] GB-22: Standing-value milestone celebrations (1k, 2.5k, 5k, 10k), also as achievements if they are not already.
- [ ] GB-23: Weather reads on the grid (rain shimmer, drought tint).
- [ ] GB-24: Wetland/mangrove tidal puzzle (extends the Wetland Forest built as B1; share the tide logic with Tide).
- [ ] GB-25: Stakeholder faces (named recurring characters with moods and friendship perks).
- [ ] GB-26: Idle/automation ranger crews, built into a skill tree (per W-3).
- [ ] GB-27: Chain bloom effect.
- [ ] GB-28: Forest Almanac collection page.
- [ ] GB-29: Carbon-credit market minigame.
- [ ] GB-30: Perfect Season streak.

---

## M. New games (groundwork plans first; a plan is `planning/<game>-plan.md`)

- [x] M-1: Heist Committee: write the groundwork plan (turn-based crew planning on a timeline), then build it (M-1b).
- [x] M-2: Lighthouse: write the groundwork plan (cozy keeper idle game; a constant unease, as if it might turn into a horror game at any moment, but it never does), then build it (M-2b).
- (M-3 Cryptid Hunt dropped: you do not like roguelikes or card-game styles.)
- [x] M-4: Pocket Bazaar: write the groundwork plan (fast merge-and-fulfil; explicitly no energy limits and no microtransactions), then build it (M-4b).
- [x] M-5: Dead Reckoning: write the groundwork plan (navigation puzzle), then build it (M-5b).
- [ ] M-1b: Build Heist Committee from its plan.
- [ ] M-2b: Build Lighthouse from its plan.
- [ ] M-4b: Build Pocket Bazaar from its plan.
- [ ] M-5b: Build Dead Reckoning from its plan.

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
- [ ] O-5: "Found a New Settlement" control (confirm-gated, archives the current one).
- [ ] O-6: A "Found a new settlement" button beside each archived entry.
- [ ] O-7: Founder's legacy carryover.
- [ ] O-8: A fourth starting scenario unlocked after reaching Space Age once.

---

## P. Signal (daily deduction puzzle; plan in `planning/signal-plan.md`)

Decisions from your answers: theme retro radio-room; UTC daily reset with an archive so past puzzles can be played; a non-daily endless practice mode; launch date not tied to a special day; Option A "Triangulate" with some bigger-board modes. Python vs JS: you want Python as far as possible but would not make the call, so it is my call: Pyodide with an instant HTML shell and a lazy engine load so the first paint is immediate.

- [ ] P-1: Build Signal to the plan's milestones with these decisions (one checkbox per milestone below).
- [ ] P-1a: Engine, daily seed, archive of past puzzles.
- [ ] P-1b: UI, retro radio-room theme, share text.
- [ ] P-1c: Endless practice and bigger-board modes.
- [ ] P-1d: Achievements, settings, tests, hub card, changelog.

## Q. Undersleep (plan in `planning/undersleep-plan.md`)

Decisions: cozy tone, "Unpacking"-esque; multiple characters, with a story mode where several characters' stories interconnect (a low-energy shut-in while an impulsive high-energy character keeps making plans); the player picks a preset that represents "them" and still plays other characters around it; framed as a game you add personal touches to so the character feels like you, not as a journal; no extra journal tags beyond my defaults. Your Q3 ("don't know what you mean") and Q2 (how visible is stored data) are answered in `planning/FOR-YOU.md`.

- [x] Q-1: Rework the plan for the cozy, multi-character, story-mode direction (update `planning/undersleep-plan.md`).
- [ ] Q-2: Build Layer A (the game) with characters, the "you" preset and the story arcs, then the personal-touches layer (no medical framing).

## S. Overclock (space roguelike deck-builder; plan in `planning/overclock-plan.md`)

You chose space and delegated the rest (you dislike the genre): I pick the gimmick, run length, meta-progression and story defaults.
- [x] S-1: Choose and document the gimmick, run length and meta-progression in the plan.
- [ ] S-2: Build it to the plan's baseline milestones.

## T. Last Line (turn-based tower defense; plan in `planning/last-line-plan.md`)

Decisions: the tower sits in a living hedge-maze that overgrows and dies to make a new route each wave; seeded maps; turn-based waves (time to reassess and set defences); endless mode with a best-wave leaderboard and a campaign; leaderboards generally, opt-in.
- [x] T-1: Update the plan for these decisions.
- [ ] T-2: Build it to the baseline milestones, with opt-in leaderboards (W-5).

## U. Deep Descent (plan in `planning/deep-descent-plan.md`, approved as "same as 6")
- [ ] U-1: Read the plan against the answers to S and T, decide its gimmick, and build it after Overclock and Last Line.

---

## X. Warframe Build Tracker (your answers; "no" items dropped: 12 plat value, 16 lucky drop counter, 30 export/restore)

- [ ] X-1: Meta build planner (one plan, one completion bar).
- [x] X-2: "This week" pin of up to three builds.
- [ ] X-3: Weapon/warframe/companion crafting tracker with the import marking owned items.
- [x] X-4: Foundry timer notes with "ready at" and optional notification.
- [ ] X-5: Void relic planner, including which relics carry the missing parts, which are unvaulted, and how to get them.
- [x] X-6: Credits and endo budget line per plan.
- [ ] X-7: Drop-source optimizer for a whole wishlist (farming session suggestions).
- [x] X-8: Mastery-rank checklist.
- [x] X-10: "Recently completed" strip.
- [ ] X-11: Forma planner, with about three suggested-build links to Overframe per item.
- [x] X-13: Trader schedule tab (Baro countdown from an entered date).
- [x] X-14: Copy wishlist as text.
- [x] X-15: Progress history chart from import snapshots.
- [x] X-17: Shared goals code for a friend.
- [x] X-18: Per-resource "I have enough" toggle.
- [ ] X-19: Companion breeding/imprint planner (or manual log).
- [ ] X-20: Per-resource farming tips written from research, not by hand.
- [x] X-21: Build-loadout notes.
- [x] X-22: Colour tag per build with filter (and fold in the related tagging ideas).
- [ ] X-23: "What changed since my last import" diff view.
- [x] X-24: Long-term goals list.
- [x] X-25: Daily/weekly checklist tab with reset times.
- [x] X-26: Keyboard shortcuts with a "?" cheat sheet.
- [ ] X-27: "Am I wasting anything?" audit.
- [x] X-28: Own-edits changelog, plus an "edited vs imported" visual difference so people can tick things off without a full import.
- [ ] X-29: Endgame readiness score.
- (X-9 arcane/mod inventory tracker: "later", parked in `planning/LATER.md`.)

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

## Closing tasks

- [ ] C-1: Archive this list when every item is checked off or moved (same rule as before) and start a fresh one.
