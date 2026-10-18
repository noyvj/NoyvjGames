# Teach the Machine: LA-8 notes (s3b, drafted 2026-10-19)

`local-ai/incoming/teach-the-machine.txt` holds no steps (header comment only, lint: 0 problems). 3 open items labelled `[local AI: after split]`; all three are C. QI-7-5 (standard kit) is already ticked.

## A list
None.

## B list
None.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| QI-7-4 shelves 4-5, hints, goals | `[Claude: design]` | 16 new lessons are authored content (story, features, hidden rule, shortcuts and mislabelled cases) in `tools/lesson_specs.py`, built by `tools/build_lessons.py` and accepted only if the subset proof passes; the Why categories `shortcut` and `mislabelled` first appear here and need their lesson data. Not an exact edit. The hint ladder and three-goals strip could be carved off by Claude as separate items afterwards. |
| QI-7-6 achievements | `[on hold]` | The 14 achievements and their reachability test cover all 40 lessons and the Notebook's five categories, two of which only exist after QI-7-4. Build after QI-7-4. |
| QI-7-7 Desktop boot and wrap-up | `[Claude: shared]` | `pc-config.json`, `pc.js` and the generated `pc.html` use the shared Desktop shell and the generator in the scripts folder, and the layout of the windows is a design choice (CLAUDE.md already names the tutorial hook `window.TEACH_THE_MACHINE_PC_TUTORIAL_STEPS` that `pc.js` must fill). |

| Item | Decision | Steps |
|------|----------|-------|
| QI-7-4 | C | 0 |
| QI-7-6 | C | 0 |
| QI-7-7 | C | 0 |

Totals: A 0, B 0, C 3.
