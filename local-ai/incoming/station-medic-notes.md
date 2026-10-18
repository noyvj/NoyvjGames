# Station Medic: LA-8 notes (s3b, drafted 2026-10-19)

Steps are in `local-ai/incoming/station-medic.txt` (lint: 0 problems). 4 open items labelled `[local AI: after split]`.

## A list
None.

## B list (chains)
- R4-SMPC-6 (3 steps): a history list where a click on an earlier step rewinds to it, with the later steps staying listed and re-runnable. Built on the existing `undo` (R4-SMPC-5) and `shift.replay`: step 1 adds `Game.later` (the actions taken back; cleared by any new action, restore and entering a shift; never saved) and `Game.jump(n)`; step 2 adds the `history` view key (`{at, steps:[{n, msg}]}`, from replaying tokens plus later) and the `jump {n}` action; step 3 adds the list under the shift log (`#history-list`, a button per step, current position marked by words and `aria-current`). Not allowed on a finished shift (as with undo) and the saved run is only the steps up to the position, so old saves load unchanged. Tests were checked by hand against shift 1-2 (treat p=0 x=0, then p=1 x=1 finishes it).
- No `index.html` size cap test exists in this game. `#log-panel` is not a toggle window here (always on the page), so no `pc-config.json` change.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-SMPC-1 drag a treatment onto a bed, a scan onto a patient | `[Claude: design]` | Drag and drop onto re-rendered patient cards is a gesture task type that failed in earlier audits (the page rebuilds the patients on every action); the drop rules (which scans and treatments are allowed) are already in the buttons, so it should be built once by Claude. |
| R4-SMMO-1 one patient per screen with swipe between beds, bottom drawer | `[Claude: design]` | A different phone layout with swipe and a bottom sheet; both task types failed before. |
| R4-SMMO-4 pull down to open the Condition Sheet as a bottom sheet | `[Claude: design]` | Pull-down gesture plus a bottom sheet; same failure type. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-SMPC-1 | C | 0 |
| R4-SMPC-6 | B | 3 |
| R4-SMMO-1 | C | 0 |
| R4-SMMO-4 | C | 0 |

Totals: A 0, B 1 item (3 steps), C 3.
