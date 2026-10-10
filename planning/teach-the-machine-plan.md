# Teach the Machine (slug `teach-the-machine`, TODO QI-7) - Groundwork Plan

Source: the Quick ideas round (A7), owner-approved: "train a tiny classifier by choosing which features it looks at, then see exactly why it gets some cases wrong." Checked against `PLAYER-PROFILE.md`: AI, coding and computers named as interests, helper role (you teach), robots, working things out themselves, a notebook that fills, clever over fast, "more game than teaching", real-world issues with several points of view, no timers, nothing lost. Personal project, no BCM tag, working title.

Pitch: switch features on and off for a small, patient learning machine, press Train, and open up every wrong answer to see exactly which feature fooled it.

## 1. Concept
- You are the tutor of Pip, a small sorting machine (a robot that barely speaks and shows moods on a lamp) in a worn station workshop. Each lesson gives a task (sort sample cases into two or three bins: ripe or not, safe door or not, friendly signal or not) and a table of cases with several features (size, stripe, glow, weight, age of reading...). You choose which features Pip may look at, press Train, then Test on cases it has not seen.
- 2-minute session: one lesson. 20-minute session: a shelf of eight lessons.
- Look: dark workshop, a faceted low-poly robot, cases as labelled crates with their feature chips (shape and word, not colour only). Quiet tone, dry notes from Pip's lamp.

## 2. Core rules (a pure, tiny learner)
- Learner: a small decision tree of depth at most 3 trained by information gain over the chosen features, with fixed tie-breaks (feature order in the table). No randomness, no clock; Train gives the same tree every time.
- Test: Pip answers each unseen case; right answers settle, wrong answers open a Why panel: the exact path through the tree ("stripe = yes, so left; weight < 5, so Safe"), the feature that decided it, and the neighbours in training that looked alike. Why-categories: missing feature, distracting feature, too few examples, a shortcut (a feature that only happened to match in training), mislabelled example.
- A lesson is cleared when Pip scores at least the lesson's target (for example 90%) on the unseen cases. Wrong answers never end anything; you edit the feature set (or in later shelves remove a mislabelled example) and Train again.

## 3. Content size
40 lessons in 5 shelves of 8: Sorting Basics (one decisive feature), Two Features, Distractions (useless and misleading features), Shortcuts (spurious correlations), Fair Treatment (the data under-represents a group; Pip is right on average, wrong for one group). Shelf n+1 opens at 5 of n; any order inside. All data invented.

## 4. How fairness is PROVED
- Dev tool `tools/subsets.py` tries every feature subset (at most 8 features, so at most 256) for every lesson and records the score of each. Tests assert: at least one subset reaches the target, the best subset is stored as the answer, and for the "distraction" lessons the all-features subset does NOT reach the target (so choosing matters).
- Tests assert that the Why panel's path replays to the same prediction as the learner (explanation matches behaviour), and that every wrong test case belongs to exactly one why-category by explicit rule.
- Training is deterministic (golden-tree snapshot per lesson); datasets are fixed data, split fixed.

## 5. Collection and 100%
- The Failure Notebook: five why-categories, each with an entry that fills when you have found an example of it, plus a gallery of 40 "Pip's lessons" cards (what it learned in words). A lesson shelf on the wall lights per cleared lesson. 100% = 40 cleared; "Best features" (the stored best subset) is a bonus. States only go up.

## 6. Goals and hint ladder
- Three always-visible goals, any order, with counts and bars. Stats strip: Lessons cleared, Failures explained, Notebook entries, Hints.
- Hint ladder (first rung asks "Would you like a suggestion?"): Nudge (one sentence about what Pip might be fooled by), Hint (marks one feature to switch off or on), Answer (sets the best subset, with a button). Free, on request, never touches a clear.

## 7. Achievements (14)
First Lesson; Ten Cleared; Twenty-Five Cleared; All Forty; Shelf Done (one shelf); Three Shelves; Why Opened (open 1 Why panel); Why Collected (all five categories); The Right Few (clear with the best subset 10 times); Less Is More (clear a lesson by switching a feature off); Shortcut Spotted; Fair Treatment (finish shelf 5); Tutor's Patience (50 Train presses); Full Notebook (every notebook entry).

## 8. Real-world facts
Data is invented. The Fair Treatment shelf's About card shows short, sourced, dated summaries of real cases from two sides each (for example a public incident database and a developer's reply), read live from the AI Incident Database (incidentdatabase.ai) with the read date, bundled snapshot as fallback. More game than teaching.

## 9. Reuse
Pure-Python engine with `handle(json)`; subset-search tool in the pattern of Logic Gates' solver; Evidence Hunt's notebook; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `info_page.py`, `announcer.js`, `pc-shell.js`.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Learner and prover | Tree trainer, case tables, Why classifier, subset search, shelf 1 (8 lessons) with proofs |
| 2 | Workshop UI | Feature switches, Train, Test, Why panel with tree path, save contract. Playable slice |
| 3 | Shelves 2-3 | 16 more lessons, distractions, Failure Notebook |
| 4 | Shelves 4-5, hints, goals | 16 more lessons (40), shortcuts and fair treatment, hint ladder, three-goals strip. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Is a small decision tree the right "tiny classifier", or do you want a nearest-neighbour model Pip can show as "looks most like these"? Default: decision tree.
2. Should the Fair Treatment shelf stay inside the game or become an optional extra shelf? Default: inside, switchable off in settings.
