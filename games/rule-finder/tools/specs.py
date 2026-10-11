"""Rule Finder -- the authoring specs: one entry per case, in drawer order. `build_cases.py` turns them into the frozen
`cases_*.py` files (examples and par tests included). Change a spec, re-run the builder, run the tests.

A spec: id, name, domain (num / shape / grid), rule (encoded, see lang.py), size (clauses), ny / nn (how many accepted and rejected
starting examples to draw), line (the relay operator's log line: dry, never a hint), and optionally tries, exclude (items the
examples must not be), yes / no (fixed examples instead of drawn ones).
"""

DRAWERS = (
    {
        "key": "numbers", "name": "Number Gates",
        "blurb": "Each gate looks at one thing about a number. Find the thing and say it.",
        "max_clauses": 1,
        "cases": (
            {"id": "latch", "name": "Latch", "domain": "num", "rule": "even", "size": 1, "ny": 2, "nn": 2,
             "line": "Shift one. The gate was left running. Warm brass, cold tea, no note."},
            {"id": "hinge", "name": "Hinge", "domain": "num", "rule": "ge:50", "size": 1, "ny": 2, "nn": 2,
             "line": "The hinge squeaks on the way through and not on the way back. I have stopped oiling it."},
            {"id": "pane", "name": "Pane", "domain": "num", "rule": "mult:5", "size": 1, "ny": 2, "nn": 2,
             "line": "Cleaned the glass today. It was not dirty. It was only being looked at."},
            {"id": "lever", "name": "Lever", "domain": "num", "rule": "has:7", "size": 1, "ny": 1, "nn": 3, "par_floor": 2,
             "line": "Somebody has scratched tally marks into the lever. I count them and lose my place at the same mark each time."},
            {"id": "spring", "name": "Spring", "domain": "num", "rule": "mult:3", "size": 1, "ny": 2, "nn": 2,
             "line": "The spring has been replaced twice, by two people with different handwriting."},
            {"id": "rivet", "name": "Rivet", "domain": "num", "rule": "square", "size": 1, "ny": 2, "nn": 2,
             "line": "One rivet is newer than the rest. I have grown fond of it."},
            {"id": "cog", "name": "Cog", "domain": "num", "rule": "prime", "size": 1, "ny": 2, "nn": 2,
             "line": "The cog turns when it wants to. So far it has always wanted to."},
            {"id": "washer", "name": "Washer", "domain": "num", "rule": "tens_gt", "size": 1, "ny": 2, "nn": 2,
             "line": "Small things hold big things together. That is most of my training."},
        ),
    },
)
