# Improvement Ideas — Replayability (Z7 audit follow-up)

Seeded from `planning/TODO.md`'s Z7 audit — a read-only pass over all 12 games checking which ones genuinely lack a reason to play twice, and whether that's fine (a teaching tool where one thorough playthrough *is* the point) or a real gap (a sandbox-shaped game that wants an ongoing reason to come back). Per that audit's own conclusion, ten of the twelve games are fine as-is — several already have more replay infrastructure than expected (scenario pickers, cross-run career systems, checkpoint replay, legacy carryover) built independently per game, consistent with the round-2 Z3/Z5 decision against a shared meta-progression module. Only two games came out with a real, specific, worth-flagging gap: **Trade Empire** (a sandbox game with a full endgame and zero meta-progression) and **Continuum** (real scenario/hard-mode/consulting-mode variety already built, but no in-game way to actually start a new settlement and go use it). Those two get real proposals below. Everything else gets one line — the audit's verdict, no ideas needed.

**How to answer:** same convention as the round-2/round-3 docs — respond by label ("J1: yes", "K3: later", "J2: no, because...") in a `## <SECTION>` block at the end of this file. "Yes" routes to `planning/TODO.md`, "later" to `planning/LATER.md`, "no" is dropped, and any open question that's genuinely yours to answer goes to `planning/FOR-YOU.md`.

Sections use this hub's standing per-game letters (A=SOL, B=Canopy, C=Grid, D=Tide, E=Aftermath, F=Herd, G=Thaw, H=Loop, I=Drift, J=Trade Empire, K=Continuum, L=Le Champ de Mots) so labels stay unambiguous against the other ideas-round docs.

---

## A. SOL — fine as-is

Has real, robust replay value already: the A1/A3 Prestige/New Game+ tree (flat yield bonus per level, tier unlocks, an opt-in "New Game+ Challenge" harder-replay toggle) gives a genuine, escalating reason to reset the world and go again. No ideas needed.

## B. Canopy — fine as-is

Teaching tool by design (a comparison game, not a run-based one) — but already has a small genuine replay hook, B15's cross-session "legacy forest" growth-bonus carryover between sessions. No ideas needed.

## C. Grid — fine as-is

Has real replay value already: C13's four starting scenarios (Standard / Coal-heavy legacy / Greenfield / Emergency) plus C1's Operator Career (points-buy cross-run perks, persisted in localStorage, earned achievements banked across runs). No ideas needed.

## D. Tide — fine as-is

Teaching tool, but already ships real optional replay variety: D19's three sea-level scenarios (conservative/moderate/severe) and D27's checkpoint-replay/foresight mechanic (rewind a run and compare the abandoned path's outcome against what actually happened). No ideas needed.

## E. Aftermath — fine as-is

The reference case for "meta-progression done right" in this hub — built from Milestone 1 as repeated short runs with a persistent cross-run skill tree, which doubles as its explicit hope-angle mechanic ("every run, even a rough one, contributes permanent capability for the next"). No ideas needed.

## F. Herd — fine as-is

Teaching tool, one continuous farm session by design. Its sustainable-certification/poultry-unlock (F11/F23) and record-ratio marker (F8) are within-session milestones or a cross-session personal-best, not cross-run meta-progression — but the decoupling lesson doesn't need a second playthrough to land. No ideas needed.

## G. Thaw — fine as-is

Teaching tool, single continuous region session — explicitly flagged in its own design notes as the most doom-prone game in the hub. Only cross-session hook is a personal-best (G19), same shape as Herd/Canopy. Replay isn't the right lever for its doom-risk concern anyway; the hope-angle mechanic already carries that weight. No ideas needed.

## H. Loop — fine as-is

Teaching tool, but already has genuine replay hooks: a goods-category picker locked in at game start (H2/H20 — clothing, furniture, etc.), an in-game "Start New Chain" reset control (H7), and a sticky cross-session best-ever streak (H19). A real, if modest, reason to reset and try a different category. No ideas needed.

## I. Drift — fine as-is

Teaching tool, single long-timeline session. Has a difficulty toggle (Accelerated Severity) and a flavor-only coda choice (I5), but no cross-run meta-progression or scenario variety. Judged fine anyway: its built-in active-region-vs-passive-control-region comparison (I2, a dotted third trend line) already delivers the "see the alternate path" payoff inside one session — the same job replaying a scenario would otherwise do elsewhere in the hub. No ideas needed.

## J. Trade Empire — real gap, ideas below

A large sandbox economic game (same "start small, end up watching a self-operating machine run" shape as SOL) that reached a full 14-milestone endgame with **zero prestige/legacy/meta-progression system**. Once the automated trade network is running well, there's no mechanical reason to found a new corporation and do it again — unlike SOL, which has exactly this hook. This matches an already-open backlog item (`planning/TODO.md`'s `J21`: "a fresh game starts with a small permanent bonus once the endgame state is reached (built independently per Z3's resolution)") — this audit's job here isn't to invent a new ask, it's to confirm J21 is a real gap and flesh out what it could concretely look like, since J21 itself is deliberately vague.

1. **[BIG]** Charter renewal (concretizes J21 itself). On reaching the endgame state, offer a "Renew the Charter" reset — same shape as SOL's Prestige button (confirm-dialog gated, reuses `shared/confirm-dialog.js`). Pick **one** of a small set of inherited advantages before the new game starts (e.g. a starting trade route already established between two colonies, a flat discount on the first automation system built, or starting reputation/relations with one colony type) — chosen once per charter, not stacked freely, so repeated charters don't trivialize the early game the way an unbounded flat bonus would.
2. **[SMALL]** Founding-conditions variety on renewal. Each charter renewal randomizes which two colonies start connected and what they specialize in (within the existing specialization set — agriculture/mining/manufacturing/research/energy), so the very first logistics bottleneck a returning player has to solve differs charter to charter, even before anything numeric changes.
3. **[BIG]** Lifetime ledger. A small permanent stats page (mirrors SOL's lifetime stats surviving Prestige) tracking cumulative goods moved, routes established, and charters completed across every past playthrough on this browser — gives long-term players something that visibly keeps growing across resets even without stacking raw numeric power, and it's a natural home for a "N charters completed" achievement.
4. **[SMALL]** Opt-in "harder charter" toggle, unlocked only after the first endgame is reached — same shape as SOL's New Game+ Challenge node. E.g. market saturation crashes prices faster, or colony needs evolve on a shorter cadence — for players who want a tougher second run rather than a bonus-boosted easier one.

## K. Continuum — real gap, ideas below

Real scenario/mode variety already exists — K12's three starting scenarios (Standard/Harsh Frontier/Fertile Valley, locked after season 1), K18's hard mode, and K22's two consulting-mode cases (a pre-built struggling city to turn around) — plus a settlement archive built specifically to keep keepsake records across separate playthroughs. But a grep of `index.html` and the CLAUDE.md turned up **no in-game "start a new settlement" control anywhere** — only consulting mode's own scenario-scoped "Abandon" (which reloads a fresh `Campaign` but only to exit that one sub-mode). Given the game's own design is "one continuous save spanning the whole arc," all of that built replay variety currently has no front door back to it short of clearing browser storage by hand — which most players will never think to do, and which the shared save-widget itself doesn't expose (checked `shared/save-widget.js`: it has no "new game"/"delete save" affordance, that's left to each game individually).

1. **[BIG]** An actual "Found a New Settlement" control. A clearly labeled, confirm-dialog-gated action (same `shared/confirm-dialog.js` pattern as SOL's Reset This World/Prestige) that archives the current settlement if it isn't already archived, then starts a brand-new `Campaign` — the missing front door back to K12's scenario picker, K18's hard mode, and K22's consulting mode, which currently exist with nothing pointing at them once a settlement is already well underway.
2. **[SMALL]** Surface the archive as a jumping-off point, not just a record. On the Civilization Summary panel's archive list, add a "Found a new settlement" button next to each archived entry (not only a passive read of past runs) — so browsing your own settlement history naturally invites starting the next one, rather than the archive reading as purely a trophy case.
3. **[BIG]** A light "founder's legacy" carryover, in the spirit of Canopy's B15 legacy-forest pattern. A new settlement's opening season starts with one small, named bonus derived from the previous settlement's peak achievement (e.g. "Founded by veterans of a Thriving Space Age city: +1 starting Administrator") — capped small and singular (like SOL's one-node-at-a-time Prestige tree) so it doesn't flatten the early-game tension the sustainability mechanic depends on.
4. **[SMALL]** A fourth starting scenario, unlocked only after reaching Space Age once — sitting alongside K12's existing three, for a returning player who's already seen every era and wants a deliberately different opening rather than the same Standard/Harsh Frontier/Fertile Valley set every time.

## L. Le Champ de Mots — fine as-is

Not a "replay" shape by design — it's an ongoing personal SRS study tool, and resetting a mastered plot would actively defeat its whole point (mirroring a real forgetting curve, not a game state meant to be re-ground for fun). It already has genuine repeat-play content exactly where that fits: four anti-farming-capped arcade minigames (Greetings & Basics Blitz, Verb Racer, Boutique Dash, Café Rush) for players who want to play again purely for fun, separate from the farm's own one-directional progress. No ideas needed.

---

## Notes

- **Trade Empire (J) and Continuum (K) are the only two sections with real proposals** — everything else already has enough of its own replay hook (or, for the eight teaching games, correctly doesn't need one). If none of J/K get a "yes," this doc can be closed out with nothing landing in `TODO.md` beyond the Z7 audit entry itself.
- **J and K's ideas don't overlap or need shared scaffolding** — Trade Empire's proposals extend its own already-open `J21` item; Continuum's are a UI gap (a missing control), not a new system, so nothing here calls for a new `shared/` module.
- If Trade Empire's charter-renewal idea (J1) is accepted, it directly resolves the open `J21` backlog line in `TODO.md` — check that item off/replace it with whichever specific shape gets picked, rather than tracking both separately.

---

<!-- Add your answers below as ## J / ## K blocks (numbered lines matching the item numbers above). -->
