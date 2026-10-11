"""Rule Finder -- Not: 8 cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""

KEY = "not"
NAME = "Not"
BLURB = "A gate can look for what a thing is not. Tick Not in the Rule Builder to turn a property around."
MAX_CLAUSES = 3

CASES = (
    {
        "id": "shunt", "name": "Shunt", "domain": "num", "rule": "~mult:3", "size": 1,
        "yes": ["37", "73"], "no": ["24", "48"],
        "par": ["3", "4"],
        "line": "A shunt is a way around. I have been taking one for years.",
    },
    {
        "id": "choke", "name": "Choke", "domain": "num", "rule": "even&~mult:4", "size": 2,
        "yes": ["10", "22", "58"], "no": ["81", "87", "97"],
        "par": ["11", "20"],
        "line": "The choke smooths things out. I tried it on a mood once. Inconclusive.",
    },
    {
        "id": "baffle", "name": "Baffle", "domain": "num", "rule": "ge:20&~even&~mult:5", "size": 3,
        "yes": ["69", "79", "93"], "no": ["8", "9", "18"],
        "par": ["17", "26", "27", "53", "75"],
        "line": "Baffles hold things back so the rest can pass in order. A queue, in brass.",
    },
    {
        "id": "damper", "name": "Damper", "domain": "num", "rule": "ge:20&~has:5", "size": 2,
        "yes": ["49", "69", "94"], "no": ["10", "15", "17"],
        "par": ["0", "20", "95"],
        "line": "A damper takes the edge off. I keep one in my coat pocket, so to speak.",
    },
    {
        "id": "filter", "name": "Filter", "domain": "shape", "rule": "~pair", "size": 1,
        "yes": ["sdt"], "no": ["cccd", "dddd"],
        "par": ["scc", "cdcd"],
        "line": "Filters keep out what you do not want. I keep a list.",
    },
    {
        "id": "screen", "name": "Screen", "domain": "shape", "rule": "has:c&~has:d", "size": 2,
        "yes": ["tcs", "tcss"], "no": ["ssts", "stdd", "sdds"],
        "par": ["cdc", "ttt", "cccc", "tcsd"],
        "line": "The screen shows what is behind it only when it feels like it.",
    },
    {
        "id": "shutter", "name": "Shutter", "domain": "shape", "rule": "~mirror&last:s", "size": 2,
        "yes": ["dsts", "ddss"], "no": ["tcc", "cttc", "scdt"],
        "par": ["ccs", "scss", "sdds"],
        "line": "Shutter down for the night. Not that anyone has asked.",
    },
    {
        "id": "blind", "name": "Blind", "domain": "shape", "rule": "~first:c&~last:c", "size": 2,
        "yes": ["dtd", "sssd"], "no": ["cdc", "ctcd", "cdcd"],
        "par": ["scs", "tcdcd", "tdddc"],
        "line": "Blinds drawn. Nothing was looking in, and I felt better anyway.",
    },
)
