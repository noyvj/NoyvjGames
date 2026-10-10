# Rule Finder (slug `rule-finder`, TODO QI-5) - Groundwork Plan

Source: the Quick ideas round (A5), owner-approved: "a sequence of numbers or shapes follows a hidden rule; you test guesses and name the rule." Checked against `PLAYER-PROFILE.md`: logic puzzles, working it out themselves, clever over fast, hint ladder on request, a codex that fills in, three goals, no timers, no losing progress, coding and maths named as interests. Personal project, no BCM tag, working title.

Pitch: a signal-room sorting game where a machine accepts or rejects whatever you feed it, and you work out and name the rule behind it.

## 1. Concept
- The Sorter is an old relay that lets some items through a gate and stops others. Each case shows a few accepted and rejected examples (numbers, strings of shapes, or small patterns). You build your own test items, press Send, and the Sorter says Through or Stopped. When you think you know the rule you build it in the Rule Builder and press Name it.
- 2-minute session: one case. 20-minute session: a drawer of eight cases.
- Look: dark control room, a brass-and-glass gate drawn in low-poly SVG, items as large tiles with a shape, a number or both (always a letter or glyph as well as colour). Quiet tone; one dry line from the relay's old operator (a log voice, optional).

## 2. Core rules (pure functions)
- An item is drawn from a fixed domain per case: integers 0 to 99, short shape strings (3 to 6 tiles from 4 shapes), or small 3x3 patterns.
- A rule is a program in a tiny rule language (a composition of up to three clauses such as "sum is even", "each tile larger than the one before", "contains two of the same shape in a row", "digits add to a multiple of 3", joined by and/or/not). Examples shown at the start are chosen from the rule's accepted and rejected items.
- Testing is free and unlimited (no guess budget, no penalty). A Tests counter only records how many you used; it earns a medal against par.
- Naming: the Rule Builder offers the clause menu; the answer is correct if the built rule agrees with the hidden rule on EVERY item in the domain (extensional equality, checked by exhaustive evaluation), not only if the words match. A near miss shows one counter-example item the player's rule gets wrong, never the hidden rule.

## 3. Content size
48 cases in 6 drawers of 8: Number Gates (single clause), Shape Strings, Two Clauses (and/or), Not (negation and exceptions), Patterns (3x3), The Odd Gate (rules with a surprising single exception). Drawer n+1 opens at 5 of 8 cleared; any order inside; every drawer is browsable.

## 4. How fairness is PROVED
- Dev tool `tools/finder.py` enumerates the whole rule language up to the case's size and checks (a) the hidden rule is the SHORTEST rule consistent with the starting examples OR the starting examples plus the par test set, so a clever player can reach it; (b) a par test set exists: a minimal list of items whose answers separate the hidden rule from every other rule of equal or shorter length (found by greedy-then-exact set cover); par tests are stored per case and re-verified in tests.
- Every case: tests assert the starting examples do NOT already uniquely identify the rule (otherwise no game), but the par set does.
- Extensional equality and domain evaluation are deterministic; no clock, no random; examples and orders are fixed data.

## 5. Collection and 100%
- The Rule Codex: one page per case, filled when cleared, showing the rule in words, the family it belongs to and the smallest set of tests that would have proved it (the par set, shown as a "shortest path"). A wall map of six drawers, 48 slots, fills as you go. 100% is all 48 named; medals (tests under par) are a bonus, not required. States only go up.

## 6. Goals and hint ladder
- Three goals always visible, any order: next three unearned achievements with counts and bars. Stats strip: Cases named, Tests sent, Codex pages, Clean names (named at par). The tally counts tests, near misses and hints.
- Ladder (first rung asks "Would you like a suggestion?"): Nudge (which kind of property to look at: sums, order, repeats), Hint (a test item worth sending next, shown as a ghost tile), Answer (the rule written out, with a button to name it). Free, on request only, never touches the medal.

## 7. Achievements (14)
First Gate; Eight Named; Twenty-Four Named; All Forty-Eight; Drawer Closed (clear one drawer); Four Drawers; Quick Eye (name with 3 or fewer tests); At Par (10 cases at par); Counter-Example (name after a near miss); Both Ways (use "not" correctly in 5 cases); Patient Hands (send 200 tests); Shape Reader (all of Shape Strings); Odd Gate Open (clear The Odd Gate); Full Codex (48 codex pages).

## 8. Real-world facts
None, fiction. The About page lists the logic puzzles and psychology work that inspired it (Wason's 2-4-6 task, Eleusis) on a Sources page, read as text only, dated.

## 9. Reuse
Pure-Python engine with `handle(json)`; `tools/` solver pattern from Hull Repair; shared `level-select.js`, `hint-ladder.js`, `goals-panel.js`, `opening-screen.js`, `confirm-dialog.js`, `info_page.py`, `announcer.js`, `pc-shell.js`; Evidence Hunt's notebook/codex page style.

## 10. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Rule language and prover | Evaluator, rule enumerator, par-test finder, drawer 1 (8 cases) with proofs and tests |
| 2 | Sorter UI | Item builder, Send, gate animation, Rule Builder, near-miss counter-example, save contract. Playable slice |
| 3 | Drawers 2-4 | 24 more cases, Shape and Not clauses, drawer gating, Rule Codex |
| 4 | Drawers 5-6, hints, goals | 16 more cases (48 total), patterns, odd gate, hint ladder, three-goals strip, medals. First complete game |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 11. Open questions for the owner
1. Should a wrong name ever show the hidden rule's words after several near misses? Default: no, only the Answer rung does.
2. Add a free "write your own rule and test a friend" mode? Default: no.
