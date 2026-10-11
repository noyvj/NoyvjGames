"""Rule Finder -- Number Gates: 8 cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""

KEY = "numbers"
NAME = "Number Gates"
BLURB = "Each gate looks at one thing about a number. Find the thing and say it."
MAX_CLAUSES = 1

CASES = (
    {
        "id": "latch", "name": "Latch", "domain": "num", "rule": "even", "size": 1,
        "yes": ["64", "74"], "no": ["3", "23"],
        "par": ["2", "36"],
        "line": "Shift one. The gate was left running. Warm brass, cold tea, no note.",
    },
    {
        "id": "hinge", "name": "Hinge", "domain": "num", "rule": "ge:50", "size": 1,
        "yes": ["92", "97"], "no": ["6", "12"],
        "par": ["40", "54"],
        "line": "The hinge squeaks on the way through and not on the way back. I have stopped oiling it.",
    },
    {
        "id": "pane", "name": "Pane", "domain": "num", "rule": "mult:5", "size": 1,
        "yes": ["75", "95"], "no": ["4", "8"],
        "par": ["0", "51"],
        "line": "Cleaned the glass today. It was not dirty. It was only being looked at.",
    },
    {
        "id": "lever", "name": "Lever", "domain": "num", "rule": "has:7", "size": 1,
        "yes": ["97"], "no": ["36", "38", "46"],
        "par": ["27", "78"],
        "line": "Somebody has scratched tally marks into the lever. I count them and lose my place at the same mark each time.",
    },
    {
        "id": "spring", "name": "Spring", "domain": "num", "rule": "mult:3", "size": 1,
        "yes": ["9", "27"], "no": ["73", "79"],
        "par": ["1", "3"],
        "line": "The spring has been replaced twice, by two people with different handwriting.",
    },
    {
        "id": "rivet", "name": "Rivet", "domain": "num", "rule": "square", "size": 1,
        "yes": ["16", "36"], "no": ["55", "87"],
        "par": ["6", "8"],
        "line": "One rivet is newer than the rest. I have grown fond of it.",
    },
    {
        "id": "cog", "name": "Cog", "domain": "num", "rule": "prime", "size": 1,
        "yes": ["7", "17"], "no": ["32", "80"],
        "par": ["1", "27"],
        "line": "The cog turns when it wants to. So far it has always wanted to.",
    },
    {
        "id": "washer", "name": "Washer", "domain": "num", "rule": "tens_gt", "size": 1,
        "yes": ["90", "96"], "no": ["19", "23"],
        "par": ["31", "66"],
        "line": "Small things hold big things together. That is most of my training.",
    },
)
