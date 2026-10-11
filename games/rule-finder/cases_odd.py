"""Rule Finder -- The Odd Gate: 8 cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""

KEY = "odd"
NAME = "The Odd Gate"
BLURB = "These gates have a surprising exception: one rare item breaks the pattern. Test the edges."
MAX_CLAUSES = 3

CASES = (
    {
        "id": "knot", "name": "Knot", "domain": "num", "rule": "even&~prime", "size": 2,
        "yes": ["68", "76", "96"], "no": ["31", "37", "49"],
        "par": ["0", "2", "14", "22"],
        "line": "Every system has one knot nobody mentions. This is ours.",
    },
    {
        "id": "burr", "name": "Burr", "domain": "num", "rule": "ge:10|has:7", "size": 2,
        "yes": ["73", "77", "95"], "no": ["2", "6", "8"],
        "par": ["0", "5", "7", "12"],
        "line": "A burr is a small rough edge left on the way through. I leave a few myself.",
    },
    {
        "id": "kink", "name": "Kink", "domain": "num", "rule": "ge:70&~square", "size": 2,
        "yes": ["76", "94", "98"], "no": ["3", "13", "24"],
        "par": ["65", "71", "72", "80", "81"],
        "line": "The kink in the line has been there so long it counts as the line.",
    },
    {
        "id": "snag", "name": "Snag", "domain": "num", "rule": "mult:9&~dsum_ge:10", "size": 2,
        "yes": ["18", "36", "54"], "no": ["28", "62", "79"],
        "par": ["0", "27", "30", "90", "99"],
        "line": "Caught on a snag. Backed off. Went round. Nothing to report, except that it caught.",
    },
    {
        "id": "hitch", "name": "Hitch", "domain": "shape", "rule": "len_ge:4&~up", "size": 2,
        "yes": ["csts", "tsds"], "no": ["ccd", "sdd", "dds"],
        "par": ["cccd", "cstd", "ccstd"],
        "line": "A hitch is just a wait that has been given a name.",
    },
    {
        "id": "wobble", "name": "Wobble", "domain": "shape", "rule": "has:c|up", "size": 2,
        "yes": ["tcst", "dsct"], "no": ["ttss", "dsds", "ddss"],
        "par": ["ssd", "std", "sdt", "cccccc"],
        "line": "It wobbles, but only on the one string, and only just.",
    },
    {
        "id": "wrinkle", "name": "Wrinkle", "domain": "grid", "rule": "touch|count_ge:5", "size": 2,
        "yes": [".####.###", "#.####.##"], "no": ["......#.#", "....#.#..", ".#...##.."],
        "par": ["......##.", "..#.#.#..", "#.#...#.#", "#.#.#.#.#"],
        "line": "A wrinkle in the pattern. I smoothed it. It came back. We are on terms.",
    },
    {
        "id": "twist", "name": "Twist", "domain": "grid", "rule": "count_ge:6&~empty:top", "size": 2,
        "yes": ["##.#.###.", "##.##.##."], "no": ["...##....", "#.#..#...", "#.#.#...."],
        "par": ["...######", "..#..#.##", "..#..####", "######..."],
        "line": "A twist at the end. I did not see it coming, which is the entire point of a twist.",
    },
)
