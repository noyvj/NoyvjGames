# Slingshot: LA-8 notes (s3b, drafted 2026-10-19)

`local-ai/incoming/slingshot.txt` holds no steps (header comment only, lint: 0 problems). 4 open items labelled `[local AI: after split]`; all four are C. Slingshot's CLAUDE.md map is accurate for what exists, but what the four items add is not exact-step work.

## A list
None.

## B list
None.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| QI-6-4 chapters 4-5, hints, goals | `[Claude: design]` | 14 new missions (giants and far shore) each need a goal definition and a reference plan found by `tools/solve.py` with the real engine, a 10 percent spare-fuel proof and a second distinct plan; that is physics design plus a long search, not an exact edit. The "live data" part reads NASA/JPL pages (`[Claude: live web data]`). The hint ladder (Nudge, Hint ghost, Answer) and three-goals strip could be carved off by Claude as their own items later and then split (they need the achievements, so they follow QI-6-6). |
| QI-6-5 standard kit | `[Claude: shared]` | Opening screen, tutorial, keyboard help, confirm dialogs, About with Sources and What's New are all wired from the shared components in the shared folder, which the local AI may not touch or name in a step; the Teach the Machine milestone 5 shows the work spans `index.html`, `app.js`, `info.py` and `sources.json` around those shared scripts. |
| QI-6-6 achievements | `[on hold]` | The plan's list of 14 (`planning/slingshot-plan.md` section 7) includes Four Giants, The Ringed One, Far Shore and All Thirty-Six, which need the chapter 4-5 missions of QI-6-4, and the milestone ends in a reachability test over all of them. Build after QI-6-4. |
| QI-6-7 Desktop boot and wrap-up | `[Claude: shared]` | `pc-config.json`, `pc.js` and the generated `pc.html` use the shared Desktop shell and the page generator in the scripts folder; design of the window layout is also open. |

| Item | Decision | Steps |
|------|----------|-------|
| QI-6-4 | C | 0 |
| QI-6-5 | C | 0 |
| QI-6-6 | C | 0 |
| QI-6-7 | C | 0 |

Totals: A 0, B 0, C 4.
