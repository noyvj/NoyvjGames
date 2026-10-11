"""Rule Finder -- Patterns: 8 cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""

KEY = "patterns"
NAME = "Patterns"
BLURB = "Three by three patterns of filled and empty squares. The gate looks at how a pattern is laid out."
MAX_CLAUSES = 3

CASES = (
    {
        "id": "grille", "name": "Grille", "domain": "grid", "rule": "sym_lr", "size": 1,
        "yes": ["######..."], "no": ["...#..#.#", "...##.#.."],
        "par": [".......#.", "..####..."],
        "line": "A grille lets the air through and keeps the rest of the building out. Sensible.",
    },
    {
        "id": "lattice", "name": "Lattice", "domain": "grid", "rule": "count_ge:5", "size": 1,
        "yes": ["#.##.####"], "no": [".#...#...", "#..##...."],
        "par": ["....#.###", ".###.#.#."],
        "line": "Lattice work. Every gap is a decision somebody made on purpose.",
    },
    {
        "id": "trellis", "name": "Trellis", "domain": "grid", "rule": "row|col", "size": 2,
        "yes": ["####..##.", "#####.##."], "no": ["....###..", ".#...#..#", ".##....#."],
        "par": ["...###.##", ".#..##.##", "#.#.#.##."],
        "line": "The trellis is bare. Nothing has grown on it since before my time.",
    },
    {
        "id": "mesh", "name": "Mesh", "domain": "grid", "rule": "centre&corners_ge:2", "size": 2,
        "yes": ["#.#.#.#..", "#####..##"], "no": [".#.#..#..", ".#.#.##..", "#..#....#"],
        "par": ["....#.#.#", ".#####.#.", "#...#.##."],
        "line": "Mesh is mostly holes. That is the point, and also, I think, the joke.",
    },
    {
        "id": "grating", "name": "Grating", "domain": "grid", "rule": "sym_tb&centre", "size": 2,
        "yes": [".#####.##", "##.#####."], "no": ["#....####", "##...##.#", "####...#."],
        "par": [".#.######", "#.#.#.#.#", "###..####"],
        "line": "Mind the grating. I have, and it has not once thanked me.",
    },
    {
        "id": "sieve", "name": "Sieve", "domain": "grid", "rule": "empty:top&empty:left", "size": 2,
        "yes": [".....#..#", "....#..#."], "no": ["#.#####..", "##..##.##", "####..#.."],
        "par": [".....##..", "....#....", "..#....#."],
        "line": "A sieve keeps what is too big. I keep a few things like that.",
    },
    {
        "id": "louvre", "name": "Louvre", "domain": "grid", "rule": "diag&~sym_lr", "size": 2,
        "yes": ["..#######", "###.###.#"], "no": [".....###.", "..#....#.", ".###.#..."],
        "par": ["..#.#.##.", ".#.##.###", "#.#######"],
        "line": "The louvres tilt one way in the morning and the other after lunch, or would, if there were a lunch.",
    },
    {
        "id": "slat", "name": "Slat", "domain": "grid", "rule": "touch&~count_ge:5&~centre", "size": 3,
        "yes": ["..##.#..#", "##.#..#.."], "no": ["..###.###", "#...#####", "##...####"],
        "par": [".......##", ".....##..", "....##.##", ".##..#.##"],
        "line": "Slats, in a row, saying nothing. Restful.",
    },
)
