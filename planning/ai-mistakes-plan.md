# AI Mistakes (slug `ai-mistakes`, TODO QI-40) - Groundwork Plan

Source: the Quick ideas round (G7), owner-approved: "spot where a simple AI would go wrong in a series of small cases and say why." Checked against `PLAYER-PROFILE.md`: AI and coding named as new interests, finds broken-build cleverness satisfying, investigation and deduction feel, real-world issues shown with several points of view, "more game than teaching", hint ladder, no timers, nothing lost, dry dark humour, no harm on screen. Personal project, no BCM tag, working title. One-line pitch: a very small, very honest machine called Pip makes guesses; you check each one, decide whether it is a mistake, and say why, then change what it learned and watch it fix itself.

## 1. Concept
**Pip** is a toy classifier in a desk lamp at the **Tallow Street Lab**. It has learned from a tiny pile of examples you can see (6 to 14 per case) and gives a guess for a new input (a photo described by a few features, a sentence, a short list of facts). Each **Case** shows the training pile, the new input and Pip's answer with its confidence. You choose: **Fine** or **Mistake**. If Mistake, you pick **why** from a short list of failure kinds. Then an optional **Fix** step lets you add, remove or relabel one training example and run Pip again to see the answer change.
- 2-minute session: a case about a "sandwich" classifier that only ever saw round bread; one question, one reason, one fix.
- 20-minute session: a chapter of six cases that add a new failure kind each, ending with a case where Pip is right for the wrong reason.
- Look: dark, clean low-poly lab bench and a friendly lamp-shaped Pip with a three-light face (words too); training examples as a tidy grid of cards (not a card game: they are labelled data tiles); confidence as a bar plus a number. Quiet; dry humour.
- The "AI" is **real but tiny**: a hand-built model the game actually runs (a keyword scorer, nearest-neighbour on features, a one-rule decision stump, a count-based naive classifier). Its working is shown in words on request.

## 2. Rules (a pure function of the case)
- A case has: a model type, a training pile, an input, Pip's computed output and confidence, the truth (what a careful person would say), and the **intended failure kind** if Pip is wrong. Some cases are Fine (to keep the player honest).
- Failure kinds (12): Too few examples, Unbalanced examples, Wrong label, Spurious pattern (it learned the background), Never seen this (out of its range), Words not meaning, Overconfident, Ambiguous question, Old data, Leaked answer, Biased sample, Right for the wrong reason.
- Scoring is only a mark per case (Clean: right verdict and right kind, Steady: right verdict, Rough: needed the Fix to see it). Every grade clears.
- **Fix** is a counterfactual: removing or adding one example recomputes Pip's output with the same model; the result shows the old and new answers. Fix is always allowed, free, and resettable. No clock, no randomness.

## 3. Content size
- 36 cases in six chapters of six: Too Few (data size), Same Old (imbalance and bias), Looks Right (spurious patterns), Never Seen (range), Words and Meaning (language), Sure of Itself (overconfidence and right-for-wrong-reason).
- 12 failure kinds with 3 field-guide pages each (36 entries), each with a plain explanation, a tiny picture, and a "real-world" note.

## 4. How fairness is PROVED (tests)
- Every case runs its real model: the stored Pip output equals the model's computed output (no faked answers).
- **Counterfactual tests:** for each Mistake case, removing the stored "culprit" example(s) flips the output to the truth; removing any single unrelated example does **not** (so the stated cause is the actual cause). For Fine cases, no single removal changes the output (stable).
- Each case has exactly one defensible failure kind among the list (a checker with a rubric: the intended kind explains the counterfactual and no other kind does); ambiguous cases are rejected.
- Banned-content lint: toy domains only (animals, foods, weather, tools); sensitive real-world domains appear only in the field-guide notes, in neutral wording with sources. Determinism and source scan: no clock, no randomness.

## 5. Bigger picture, goals, hints
- The **Field Guide** is the collection: 12 failure kinds x 3 pages, each page unlocked when you spot that kind in a case. A lab wall shows 36 pinned cases that turn from blank to filled. A completion percentage bar sits above.
- Three goals always visible (any order): the next three unearned achievements with counts and bars. Stats strip: Cases checked, Mistakes spotted, Kinds known, Fixes.
- Hint ladder (opt-in; first rung asks "Would you like a suggestion?"): Nudge (look at the training pile's balance), Hint (which examples matter, shown highlighted), Answer (the verdict, the kind, and the example to remove, with a Show me button).
- Every chapter and case open from the start.

## 6. Achievements (14; computed from facts)
1 First Check; 2 Ten Cases; 3 Chapter Checked; 4 Whole Lab (all 36); 5 Sharp Eye (first-time right verdict, 10 times); 6 Right Reason (right kind, 10 times); 7 Thirty Clean (all but a few Clean); 8 Fixer (use Fix 10 times); 9 Fixed It (Fix flips a Mistake to right, 10 cases); 10 Kinds Half (6); 11 Kinds Full (12); 12 Honest Pip (find a Fine case, 5 times); 13 Right for the Wrong Reason; 14 Second Opinion (all three hint rungs on one case).

## 7. Real-world facts
The Field Guide's "Real world" notes cite named, dated sources read live: documented public incidents and studies of machine-learning failures (the AI Incident Database, published research on image classifiers trained on background cues, and government standards bodies' reports on bias testing), each shown with the read date and presented with more than one point of view (researchers, companies, affected users). Described in neutral wording with no distressing detail. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step. Modules: `models.py` (tiny classifiers), `cases_*.py`, `rubric.py`, `fix.py` (counterfactual recompute), `fieldguide.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Station Medic's case-and-seal pattern, Evidence Hunt's solver-as-proof pattern, `shared/hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `level-select.js`, the info-page kit.
- Save: best mark per case, field-guide pages, hint rungs, flags, tally.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Tiny models, case format, counterfactual and rubric proofs, chapter 1 (6 cases) with tests |
| 2 | Bench UI | Pip, training grid, verdict and kind pickers, Fix step, result card, save contract. Playable slice |
| 3 | Chapters 2-4, field guide, hints | 18 more cases, Field Guide, hint ladder, three-goals strip |
| 4 | Chapters 5-6 | 12 more cases (36 in all), all 12 failure kinds. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Should cases stay in toy domains (animals, foods, weather) with real-world incidents only in the Field Guide notes, or should some cases use a realistic setting (for example a job-application screener)? Default: toy domains only.
2. Should the Fix step (change one example and re-run Pip) be on from the start or appear only after the first chapter? Default: from the start.
