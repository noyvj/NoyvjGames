# Iteration Pass 3 — Fun/Teaching Balance for All 8 Games

**Purpose:** this pass applies research on educational game design specifically to the risk of each game either (a) becoming "chocolate-covered broccoli" — fun bolted onto a lesson rather than fused with it — or (b) tipping out of flow, either into boredom or into anxiety/dread. Same merge rule as the other iteration files: fold the relevant section into each game's own `CLAUDE.md`, under a new `## Iteration Notes — Pass 3 (Fun/Teaching Balance)` heading.

## The three principles this pass applies

1. **Fun and learning shouldn't be separable.** (Filament Games; the chocolate-covered-broccoli critique) If a player could win the game while ignoring or ignorant of the climate mechanic underneath, the mechanic is decorative, not integral. Test: does the *winning strategy* require understanding the lesson, or can you win a different way and the lesson is just flavor text?

2. **Stay in the flow channel.** (Csikszentmihalyi; Chen) Engagement lives between boredom (challenge is too easy relative to growing player skill) and anxiety (challenge outpaces skill, especially if consequences feel arbitrary or uncontrollable). Every game's difficulty curve should scale *with the same mechanic that teaches the lesson* — not as a separate, bolted-on difficulty slider.

3. **Build trust, not just fear.** (the Klim:S21 evaluation study) A climate game that only conveys threat, without a legible, working sense of efficacy ("my actions actually worked"), risks increasing anxiety without increasing trust that intervention matters. This is the research-backed version of the hope-angle requirement already built into every game — worth treating as a testable design goal, not just a vibe.

---

## Grid — add to `climate-quartet/grid/CLAUDE.md`

**Risk:** the tiered plant system could drift toward a pure optimization spreadsheet where a player wins by number-crunching without ever registering *why* the renewable path pays off — chocolate-covered-broccoli risk if the emissions meter is just a side-score rather than the actual mechanism gating success.

**Fix:**
- Make sure the escalating disruption events (the game's difficulty curve) scale directly off the *same* emissions meter that represents the climate lesson — not a separate difficulty setting. The player's growing skill (managing the coupled cost-curve/emissions system) should be the only thing standing between them and increasingly severe brownouts. This is flow principle #2 applied directly: challenge and lesson are the same axis.
- Keep early mistakes recoverable (a soft, escalating disruption curve rather than a sudden spike) so early-game missteps don't tip a first-time player into the anxiety zone before they've learned the system.

---

## Canopy — add to `climate-quartet/canopy/CLAUDE.md`

**Risk:** the idle/passive accumulation side of the mechanic risks tipping toward boredom — if preserving a plot mostly means waiting, without active skill or decision-making, flow drops even though the "lesson" (restraint compounds) is technically still present.

**Fix:**
- Keep the *active* decisions (which plot to clear/preserve/replant, and when) meaningfully skill-based — timing and plot-selection should matter, not just "wait long enough." Pace new unlocks (biodiversity sub-meter, stakeholder-tension moments from Pass 2) to arrive before long idle stretches would otherwise set in, so the challenge curve keeps pace with the player's growing understanding of the system.

---

## Tide — add to `climate-quartet/tide/CLAUDE.md`

**Risk:** this is the game most exposed to the "fuelling fear rather than building trust" failure mode from the Klim:S21 study — delayed consequence (the fish-stock crash) can read as arbitrary or unfair if the player can't trace it back to their own choices, which risks anxiety without efficacy.

**Fix:**
- The running log/ticker from Iteration Pass 1 is exactly the right tool here — use it not just for narrating decline, but equally for narrating *recovery*, so the player gets clear, legible feedback both ways (flow principle #2: immediate feedback, in both directions).
- Explicitly design the adaptation-tech-tree payoff (Pass 2) to produce a visible, trackable improvement the moment infrastructure tiers unlock — this is the concrete "trust" test from the cited study: does the player come away believing intervention worked, not just that the ocean is scary.

---

## Aftermath — add to `climate-quartet/aftermath/CLAUDE.md`

**Risk:** repeated runs risk sliding into boredom if the skill tree makes the player meaningfully stronger while event difficulty stays flat — skill outpacing challenge is the textbook flow-boredom failure mode.

**Fix:**
- The diversified event types from Iteration Pass 2 should scale in variety and severity roughly in step with skill-tree growth, so each run still asks something new of the player rather than becoming a rote execution of an already-solved strategy. Treat this explicitly as flow-curve tuning, not just content variety for its own sake.

---

## Herd — add to `climate-quartet-2/herd/CLAUDE.md`

**Risk:** if the emissions/decoupling system is tracked as a separate "sustainability score" bolted onto an otherwise-normal farm sim, this is close to a textbook chocolate-covered-broccoli setup — the player could optimize pure profitability while ignoring the score entirely.

**Fix:**
- Confirm the coupling-ratio mechanic feeds directly into the *same* profitability number the player is trying to maximize, not a parallel or optional metric. The winning strategy and the decoupling lesson need to be the same strategy, full stop — this is the single most important check for this game specifically.

---

## Thaw — add to `climate-quartet-2/thaw/CLAUDE.md`

**Risk:** already flagged as the most doom-prone game in the hub (Iteration Pass 1); this pass adds the research-backed version of that concern — a feedback-loop mechanic without a legible efficacy payoff is close to the exact setup the Klim:S21 study found risked "fuelling fear" rather than "strengthening trust."

**Fix:**
- The intervention lever (regional emissions reduction / permafrost-preserving measures) needs *immediate, visible* positive feedback the moment it's used — not just a flatter long-term slope revealed at session end. Flow principle #2 demands immediate feedback; skipping that here is exactly where a feedback-loop game risks becoming pure dread rather than an engaging, masterable system.
- Consider treating "does the player feel like their intervention worked" as an explicit thing to check via the in-game feedback prompt for this game specifically, given it's the highest-risk game in the hub on this axis.

---

## Loop — add to `climate-quartet-2/loop/CLAUDE.md`

**Risk:** the supply-chain-as-graph structure risks a different flavor of boredom — not idle waiting like Canopy, but dry abstraction, where "closing the loop" is legible as a number improving but not *felt* as a meaningful change.

**Fix:**
- The single-item vignette addition from Iteration Pass 2 is the direct fix here — treat it explicitly as satisfying flow's "immediate, felt feedback" requirement, not just as a nice-to-have visual. The abstract flow-chain graph is where the strategy lives; the vignette is where the player *feels* what that strategy means.

---

## Drift — add to `climate-quartet-2/drift/CLAUDE.md`

**Risk:** shares Loop's "dry abstraction" risk (a composite dashboard can feel like a spreadsheet) and Thaw's "fear without efficacy" risk (real displacement framed institutionally can read as fatalistic if the net-positive integration payoff isn't clearly felt).

**Fix:**
- The net-positive integration mechanic (well-integrated populations eventually contributing back to regional capacity) needs a clear, legible moment where the player notices the shift from strain to contribution — not just a background formula. This is the same "immediate feedback" and "trust, not just fear" fix as Thaw, applied to an institutional-capacity frame instead of a feedback-loop frame.
- Given the added sensitivity of this topic, the in-game feedback prompt for this game specifically could ask whether the player came away feeling migration pressure is a manageable systems problem (the intended message) rather than an unmanageable crisis — a direct, testable version of the trust-vs-fear distinction from the cited research.
