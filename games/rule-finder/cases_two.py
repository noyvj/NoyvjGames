"""Rule Finder -- Two Clauses: 8 cases (frozen by tools/build_cases.py from tools/specs.py; do not edit by hand)."""

KEY = "two"
NAME = "Two Clauses"
BLURB = "Now the gate looks at two things at once, joined by and or by or."
MAX_CLAUSES = 2

CASES = (
    {
        "id": "fuse", "name": "Fuse", "domain": "num", "rule": "even&ge:50", "size": 2,
        "yes": ["72", "76", "92"], "no": ["33", "43", "89"],
        "par": ["12", "40", "58", "63"],
        "line": "Fuses only do their job once. I find that more honest than most equipment.",
    },
    {
        "id": "contact", "name": "Contact", "domain": "num", "rule": "mult:5|has:7", "size": 2,
        "yes": ["78", "79", "87"], "no": ["4", "24", "42"],
        "par": ["0", "5", "89"],
        "line": "Contacts: the tiny places where one thing finally touches another. Mostly they are dusty.",
    },
    {
        "id": "switch", "name": "Switch", "domain": "num", "rule": "ge:50&has:3", "size": 2,
        "yes": ["53", "73", "83"], "no": ["25", "27", "28"],
        "par": ["30", "43", "67", "71"],
        "line": "I flipped the switch and the room did not change. This is sometimes the whole of the work.",
    },
    {
        "id": "bobbin", "name": "Bobbin", "domain": "shape", "rule": "first:c&pair", "size": 2,
        "yes": ["ccc", "cct"], "no": ["stsc", "tcts", "tdcd"],
        "par": ["ctc", "tcc", "cdttss", "stccdc"],
        "line": "Wound this bobbin by hand. It is the only thing on shift I can say I made.",
    },
    {
        "id": "terminal", "name": "Terminal", "domain": "num", "rule": "mult:3|ge:90", "size": 2,
        "yes": ["18", "30", "36"], "no": ["55", "56", "67"],
        "par": ["10", "57", "89", "95"],
        "line": "Terminal. The word has an unfortunate ring, so we say the end of the line instead.",
    },
    {
        "id": "coil", "name": "Coil", "domain": "shape", "rule": "has:t|has:d", "size": 2,
        "yes": ["sstd", "tssd"], "no": ["cscc", "scsc", "sssc"],
        "par": ["ccc", "sts", "sds", "cctc", "scdc"],
        "line": "A coil remembers which way the current went. I should like to be so reliable.",
    },
    {
        "id": "rotor", "name": "Rotor", "domain": "shape", "rule": "len_ge:5&mirror", "size": 2,
        "yes": ["stssts", "sdssds"], "no": ["tcsdsc", "tttttc", "dtcsdc"],
        "par": ["stts", "ctdtc", "sssts"],
        "line": "The rotor spins quietly, which I take as a compliment.",
    },
    {
        "id": "stator", "name": "Stator", "domain": "shape", "rule": "up|pair", "size": 2,
        "yes": ["ttts", "ddss"], "no": ["sdtd", "tdcd", "dtct"],
        "par": ["csc", "ctd", "dts"],
        "line": "The stator holds still while the rotor does all the talking. We have an understanding.",
    },
)
