# Lighthouse: LA-8 notes (s3b, drafted 2026-10-19)

`local-ai/incoming/lighthouse.txt` holds no steps (header comment only, lint: 0 problems). 3 open items labelled `[local AI: after split]`; all three are C. Lighthouse's CLAUDE.md map is accurate for what exists. `index.html` is about 8,000 tokens against the 14,000-token limit in `tests/test_file_sizes.py`, so no cap needs raising.

## A list
None.

## B list
None.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| R4-LHPC-1 clickable lighthouse picture (lamp, clockwork, trouble spot) | `[Claude: design]` | The scene is a static SVG in `index.html` (`#scene`, `#lantern-glass`, `#rock-group`), so hotspots are possible, but what each click does is undefined: the engine has `wind` (clockwork), `tend` (see to the incident) and `patch {part}` (which of five parts?), and "the lamp" has no matching action. It also needs per-phase enabling rules (these actions exist only at night) and a hover label that is not colour-only. |
| R4-LHPC-7 camera key C with three views and a slow drift | `[Claude: design]` | Three fixed camera views (sea, gallery, lantern room) need new artwork for views the picture does not have today (it is one 900 by 420 scene), plus a drift effect with an off switch; scene art and layout rather than an exact edit. |
| R4-LHMO-7 tall portrait scene with phase panels in a bottom sheet | `[Claude: design]` | A different phone layout with a bottom sheet holding all five phase panels (`#evening-panel` ... `#yearend-panel`); bottom sheets failed in earlier audits and `mobile-*.js` already hold several phone-only controls that it would have to coexist with. |

| Item | Decision | Steps |
|------|----------|-------|
| R4-LHPC-1 | C | 0 |
| R4-LHPC-7 | C | 0 |
| R4-LHMO-7 | C | 0 |

Totals: A 0, B 0, C 3.
