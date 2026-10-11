"""Rule Finder -- Shape Strings: 8 cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""

KEY = "shapes"
NAME = "Shape Strings"
BLURB = "Strings of circles, squares, triangles and diamonds. The gate looks at one thing about the string."
MAX_CLAUSES = 1

CASES = (
    {
        "id": "valve", "name": "Valve", "domain": "shape", "rule": "has:t", "size": 1,
        "yes": ["tdt"], "no": ["dss", "dssc"],
        "par": ["cdc", "dsstc"],
        "line": "Valve seats are cold to the touch. I rest a hand on one when I count.",
    },
    {
        "id": "gasket", "name": "Gasket", "domain": "shape", "rule": "pair", "size": 1,
        "yes": ["csss"], "no": ["tcs", "dst"],
        "par": ["tcc", "cscs"],
        "line": "A gasket does not make anything work. It makes sure nothing leaks. I admire that.",
    },
    {
        "id": "bracket", "name": "Bracket", "domain": "shape", "rule": "first:s", "size": 1,
        "yes": ["ssds"], "no": ["cdtt", "tccd"],
        "par": ["dss", "scdt"],
        "line": "Whoever bent this bracket measured twice and then, I suspect, did something else entirely.",
    },
    {
        "id": "flange", "name": "Flange", "domain": "shape", "rule": "len_ge:5", "size": 1,
        "yes": ["tsdsds"], "no": ["csc", "scs"],
        "par": ["tsdd", "ccscc"],
        "line": "Flanges: all very round. I have nothing against them.",
    },
    {
        "id": "coupling", "name": "Coupling", "domain": "shape", "rule": "mirror", "size": 1,
        "yes": ["sss"], "no": ["cddt", "tcdd"],
        "par": ["sccss", "cdttdc"],
        "line": "Coupling check. Two things held together by a third thing that nobody thanks.",
    },
    {
        "id": "sprocket", "name": "Sprocket", "domain": "shape", "rule": "up", "size": 1,
        "yes": ["cstd"], "no": ["tddc", "dddc"],
        "par": ["ccstd", "cstsd"],
        "line": "The sprocket's teeth are worn evenly. Someone cared, or nobody did, for a very long time.",
    },
    {
        "id": "bearing", "name": "Bearing", "domain": "shape", "rule": "kinds_ge:3", "size": 1,
        "yes": ["cdsc"], "no": ["ttd", "ttdt"],
        "par": ["csc", "tcttd"],
        "line": "Bearings make a small sound when they are happy. This one is not happy. It is, however, working.",
    },
    {
        "id": "collar", "name": "Collar", "domain": "shape", "rule": "twice:c", "size": 1,
        "yes": ["cdsc"], "no": ["dtd", "dddt"],
        "par": ["csd", "sdc"],
        "line": "Collar and cuffs. The relay had a dress code once. It has been quietly lowered.",
    },
)
