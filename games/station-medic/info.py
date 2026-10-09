"""Station Medic -- the About page: what the game is, what it will never do, and the fiction notice."""

NOTICE = ("This is a fiction game, not medical advice. Every condition, scan and treatment in it is invented for Lowlight "
          "Station. Nothing here describes real medicine, and nothing here should be used to decide how to care for a real person.")

PLEDGE = (
    "There is no timer, no energy and no waiting: the ward never changes while you think.",
    "Nobody dies on screen. A bad call costs a seal, never a person: the patient is settled later and you can restore the shift and try again.",
    "Progress is only ever added. Seals only go up, and nothing expires or can be missed.",
    "No randomness anywhere: the same actions in the same shift always do the same thing.",
    "Hints are free and never touch a seal. The answer is one tap away whenever you want it.",
    "No audio, no purchases, no leaderboards.",
)

FRAMING = ("Station Medic is a small invented place: Lowlight Station, a worn ring far from anywhere, its quiet infirmary, ten crew "
           "and a second medic robot called Tally. It is a puzzle about reading signs, choosing scans and sharing a thin cabinet.")

HOW = (
    "Read the sheet. Each condition lists its signs, the scans that read positive for it and what cures it. A patient shows all the "
    "signs of what they have.",
    "A scan uses a supply and answers yes or no. If the signs fit more than one condition, a scan can tell them apart.",
    "A treatment uses a supply too. A chart note can forbid some treatments, and two heavy ones never go together.",
    "Every shift can be finished with no cost whatever the scans say. A cost (a wasted supply, a reaction, a borrowed spare) only lowers the shift's seal: Clean, Steady or Rough.",
)


def view():
    return {"framing": FRAMING, "notice": NOTICE, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW)}
